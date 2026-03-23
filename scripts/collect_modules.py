#!/usr/bin/env python3
"""
bwForCluster NEMO 2 Easybuild Module Collector

Collects available software modules from different HPC architectures
via lmod (module avail / module spider) and writes JSON output.

Architectures genoa, h200, rtx and mi300a share the same module tree
(symbolic links to genoa).  Only one lmod query is performed for the
whole group; the result is duplicated for the other members.
l40s (Intel + NVIDIA L40S) is a separate physical architecture with
its own module tree and is queried independently.
"""

import subprocess
import json
import re
import os
import argparse
from datetime import datetime
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Architecture definitions
# ---------------------------------------------------------------------------

# Groups of architectures that share the same physical module tree.
# The first entry is the *canonical* architecture that is actually queried.
ARCH_GROUPS = {
    'genoa': ['genoa', 'h200', 'rtx', 'mi300a'],
    'l40s':  ['l40s'],    # Intel-based nodes, separate physical module tree
    'milan': ['milan'],
}

ALL_ARCHITECTURES = ['genoa', 'h200', 'rtx', 'mi300a', 'l40s', 'milan']

# Reverse lookup: architecture → canonical representative
CANONICAL_ARCH = {
    alias: canonical
    for canonical, members in ARCH_GROUPS.items()
    for alias in members
}

# ---------------------------------------------------------------------------
# Category prefix → human-readable label (with module path prefix)
# ---------------------------------------------------------------------------
CATEGORIES = {
    'ai':        'Artificial Intelligence (ai/)',
    'bio':       'Life Sciences & Bioinformatics (bio/)',
    'cae':       'Computer-Aided Engineering (cae/)',
    'chem':      'Computational Chemistry (chem/)',
    'compiler':  'Compilers (compiler/)',
    'data':      'Data Management & Processing (data/)',
    'devel':     'Development Tools (devel/)',
    'geo':       'Earth & Environmental Sciences (geo/)',
    'gpu':       'GPU Computing (gpu/)',
    'lang':      'Programming Languages & Utilities (lang/)',
    'lib':       'General Libraries (lib/)',
    'math':      'Mathematics (math/)',
    'mpi':       'MPI Libraries (mpi/)',
    'numlib':    'Numerical Libraries (numlib/)',
    'phys':      'Physics & Materials Science (phys/)',
    'system':    'System Software (system/)',
    'toolchain': 'Compiler Toolchains (toolchain/)',
    'tools':     'General Utilities (tools/)',
    'vis':       'Visualization & Graphics (vis/)',
}


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

class ModuleCollector:
    def __init__(self, architectures: Optional[List[str]] = None):
        self.architectures = architectures or list(ALL_ARCHITECTURES)

    # -- shell helpers ------------------------------------------------------

    @staticmethod
    def _run(cmd: str, timeout: int = 30) -> str:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                               text=True, timeout=timeout)
            return r.stderr + r.stdout
        except subprocess.TimeoutExpired:
            print(f"  Timeout: {cmd}")
        except Exception as e:
            print(f"  Error: {e}")
        return ""

    # -- lmod queries -------------------------------------------------------

    def _module_avail(self, arch: str) -> str:
        return self._run(f"module load arch/{arch} && module avail")

    def _module_spider(self, arch: str) -> Dict[str, str]:
        out = self._run(f"module load arch/{arch} && module spider", timeout=60)
        return self._parse_spider(out)

    @staticmethod
    def _parse_spider(output: str) -> Dict[str, str]:
        descriptions: Dict[str, str] = {}
        key: Optional[str] = None
        lines: List[str] = []
        for line in output.split('\n'):
            if line.strip() and ':' in line and not line.startswith('    '):
                if key and lines:
                    descriptions[key] = ' '.join(lines).strip()
                m = re.match(r'\s*(\S+):\s*', line)
                key = m.group(1) if m else None
                lines = []
            elif line.startswith('    ') and key:
                if not ('/' in line and ',' in line):
                    s = line.strip()
                    if s:
                        lines.append(s)
        if key and lines:
            descriptions[key] = ' '.join(lines).strip()
        return descriptions

    # -- parsing ------------------------------------------------------------

    def parse_avail(self, output: str, arch: str,
                    spider: Dict[str, str]) -> List[Dict]:
        modules: List[Dict] = []
        header = "Unknown"
        now = datetime.now().isoformat()

        for line in output.split('\n'):
            line = line.strip()
            hm = re.search(r'---+\s*(.+?)\s*---+', line)
            if hm:
                header = hm.group(1).strip()
                continue
            if '/' not in line or line.startswith('-'):
                continue
            for entry in re.findall(r'(\S+/\S+(?:\s*\([^)]+\))?)', line):
                clean = re.sub(r'\s*\([^)]+\)$', '', entry.strip())
                if clean.startswith('arch/'):
                    continue
                info = self._parse_entry(clean, header, arch, spider, now)
                if info:
                    modules.append(info)
        return modules

    def _parse_entry(self, full_name: str, header: str, arch: str,
                     spider: Dict[str, str], ts: str) -> Optional[Dict]:
        parts = full_name.split('/')
        if len(parts) < 2:
            return None

        if len(parts) == 2:
            software, version = parts
            category = self._fallback_category(software, header)
            spider_key = software
        else:
            prefix, software = parts[0], parts[1]
            version = '/'.join(parts[2:])
            category = CATEGORIES.get(prefix.lower(),
                                      header if header != "Unknown" else "Other")
            spider_key = f"{prefix}/{software}"

        description = spider.get(spider_key, "") or f"{software} {version}"

        return {
            'software': software,
            'version': version,
            'category': category,
            'architecture': arch,
            'description': description,
            'full_name': full_name,
            'collected_at': ts,
        }

    @staticmethod
    def _fallback_category(software: str, header: str) -> str:
        s = software.lower()
        if any(t in s for t in ('gcc', 'intel', 'llvm', 'go')):
            return 'Compilers (compiler/)'
        if any(t in s for t in ('python', 'r-', 'julia')):
            return 'Programming Languages (lang/)'
        if any(t in s for t in ('mpi', 'openmpi', 'cuda')):
            return 'Parallel Computing (mpi/)'
        return header if header != "Unknown" else "Other"

    # -- collection ---------------------------------------------------------

    def collect(self) -> Dict[str, List[Dict]]:
        """Collect modules for all requested architectures.

        Identical architectures (same ARCH_GROUP) are queried only once;
        the result is copied with the correct architecture name.
        """
        results: Dict[str, List[Dict]] = {}
        cache: Dict[str, List[Dict]] = {}          # canonical → modules

        for arch in self.architectures:
            canonical = CANONICAL_ARCH.get(arch, arch)

            if canonical not in cache:
                print(f"Collecting modules for {canonical}"
                      f" (canonical for {', '.join(ARCH_GROUPS.get(canonical, [canonical]))})...")
                spider = self._module_spider(canonical)
                print(f"  {len(spider)} descriptions from spider")
                avail = self._module_avail(canonical)
                mods = self.parse_avail(avail, canonical, spider) if avail else []
                cache[canonical] = mods
                print(f"  {len(mods)} modules found")
            else:
                print(f"Reusing {canonical} data for {arch} (identical module tree)")

            if arch == canonical:
                results[arch] = cache[canonical]
            else:
                results[arch] = [{**m, 'architecture': arch}
                                 for m in cache[canonical]]
        return results

    # -- persistence --------------------------------------------------------

    @staticmethod
    def save(data: Dict[str, List[Dict]], output_dir: str):
        os.makedirs(output_dir, exist_ok=True)

        all_modules: List[Dict] = []
        for arch, modules in data.items():
            p = os.path.join(output_dir, f"modules_{arch}.json")
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(modules, f, indent=2, ensure_ascii=False)
            print(f"  {p}  ({len(modules)} modules)")
            all_modules.extend(modules)

        combined = os.path.join(output_dir, "modules_all.json")
        with open(combined, 'w', encoding='utf-8') as f:
            json.dump(all_modules, f, indent=2, ensure_ascii=False)
        print(f"  {combined}  ({len(all_modules)} modules total)")

        # architecture group info for metadata
        group_info = {}
        for canonical, members in ARCH_GROUPS.items():
            present = [a for a in members if a in data]
            if present:
                group_info[canonical] = present

        metadata = {
            'collection_date': datetime.now().isoformat(),
            'architectures': list(data.keys()),
            'architecture_groups': group_info,
            'identical_note': (
                'Architectures within the same group share an identical '
                'module tree (symbolic links).  Only one lmod query is '
                'performed per group.'
            ),
            'total_modules': len(all_modules),
            'modules_per_arch': {a: len(m) for a, m in data.items()},
        }
        mp = os.path.join(output_dir, "metadata.json")
        with open(mp, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"  {mp}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='bwForCluster NEMO 2 Easybuild Module Collector')
    parser.add_argument('--output-dir', '-o', default='./data',
                        help='Output directory for JSON files (default: ./data)')
    parser.add_argument('--architecture', '-a',
                        help='Collect only for a specific architecture')
    args = parser.parse_args()

    if args.architecture:
        if args.architecture not in ALL_ARCHITECTURES:
            print(f"Unknown architecture: {args.architecture}")
            print(f"Available: {', '.join(ALL_ARCHITECTURES)}")
            return 1
        archs = [args.architecture]
    else:
        archs = None

    collector = ModuleCollector(archs)
    print("Starting module collection...\n")
    data = collector.collect()
    print("\nSaving data...")
    collector.save(data, args.output_dir)
    print("\nDone!")
    return 0


if __name__ == "__main__":
    exit(main())