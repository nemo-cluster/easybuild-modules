#!/usr/bin/env python3
"""
Generate MediaWiki pages from collected module JSON data.

Compatible with MediaWiki 1.39.  Produces:
  - A single combined page  (--mode combined, default)
  - One page per category    (--mode per-category)
  - One page per architecture group (--mode per-arch)

Uses collapsible wikitables, sortable tables, and <code> markup.
"""

import html as _html
import json
import argparse
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

# Must match definitions in collect_modules.py
ARCH_GROUPS = {
    'genoa': ['genoa', 'h200', 'rtx', 'mi300a'],
    'l40s':  ['l40s'],
    'milan': ['milan'],
}

ARCH_GROUP_LABELS = {
    'genoa': 'Genoa / H200 / RTX / MI300A',
    'l40s':  'L40S',
    'milan': 'Milan',
}


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_data(data_dir: str):
    with open(os.path.join(data_dir, 'modules_all.json'), 'r',
              encoding='utf-8') as f:
        modules = json.load(f)
    meta_path = os.path.join(data_dir, 'metadata.json')
    metadata = {}
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    return modules, metadata


def unique_modules_for_group(modules: List[Dict],
                             group_members: List[str]) -> List[Dict]:
    """Return deduplicated modules belonging to any member of a group."""
    seen = set()
    result = []
    for m in modules:
        if m['architecture'] not in group_members:
            continue
        key = (m['software'], m['version'], m['category'])
        if key not in seen:
            seen.add(key)
            result.append(m)
    return result


def group_by_category(modules: List[Dict]) -> Dict[str, Dict[str, List[Dict]]]:
    """Group modules by category → software → list of version dicts."""
    tree: Dict[str, Dict[str, List[Dict]]] = defaultdict(
        lambda: defaultdict(list))
    for m in modules:
        tree[m['category']][m['software']].append(m)
    return tree


def shorten_desc(desc: str, max_len: int = 200) -> str:
    """Truncate long descriptions for table display."""
    if len(desc) <= max_len:
        return desc
    return desc[:max_len].rsplit(' ', 1)[0] + ' …'


def wiki_escape(text: str) -> str:
    """Escape characters that interfere with MediaWiki table syntax."""
    return text.replace('|', '{{!}}').replace('[', '&#91;').replace(']', '&#93;')


# ---------------------------------------------------------------------------
# Spiderlein helpers
# ---------------------------------------------------------------------------

def load_spiderlein_config(allowlist_path: str,
                           cat_rename_path: str):
    """Load allowlist and rename mappings for spiderlein mode.

    Returns (allowlist, renames) where
    - allowlist is a set of 'category/software' strings (lowercase);
      empty set means "include everything".
    - renames is {'software': {...}, 'category': {...}} with lowercase keys.
    """
    allowlist: Set[str] = set()
    if allowlist_path and os.path.exists(allowlist_path):
        with open(allowlist_path, 'r', encoding='utf-8') as f:
            for line in f:
                entry = line.strip()
                if entry and not entry.startswith('#'):
                    allowlist.add(entry.lower())

    renames: Dict = {'software': {}, 'category': {}}
    if cat_rename_path and os.path.exists(cat_rename_path):
        with open(cat_rename_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        renames['software'] = {
            k.lower(): v for k, v in data.get('software', {}).items()
        }
        renames['category'] = {
            k.lower(): v for k, v in data.get('category', {}).items()
        }
    return allowlist, renames

# note: allowlist entries use DISPLAY names (after rename), not original EB names


def generate_spiderlein(modules: List[Dict], metadata: Dict,
                        allowlist: Set[str], renames: Dict) -> str:
    """Generate a spiderlein-compatible gsorted HTML fragment.

    Rows are deduplicated across all architectures, filtered by allowlist,
    renamed via renames, and sorted globally by software name.
    Output matches the nemo_spiderlein_gsorted.html format.
    """
    # --- Deduplicate across all architectures by (short_cat, sw, version) ---
    seen: Set[tuple] = set()
    rows = []
    for m in modules:
        parts = m.get('full_name', '').split('/')
        if len(parts) < 3:
            continue  # skip Global Aliases and bare-path entries
        cat_key = parts[0].lower()
        sw_key  = parts[1].lower()
        ver     = m.get('version', '')
        key = (cat_key, sw_key, ver)
        if key in seen:
            continue
        seen.add(key)

        # Apply output renames first, then filter by display names
        cat_out = renames['category'].get(cat_key, cat_key)
        sw_out  = renames['software'].get(sw_key,  sw_key)

        # Allowlist filter uses display names (after rename)
        if allowlist and f'{cat_out}/{sw_out}' not in allowlist:
            continue

        desc = (m.get('description') or '').strip()
        desc = shorten_desc(desc, max_len=300) if desc else '-'

        rows.append((cat_out, sw_out, ver, desc))

    # Sort globally by software name (gsorted), then category, then version
    rows.sort(key=lambda r: (r[1].lower(), r[0].lower(), r[2]))

    # --- Build header ---
    now        = datetime.now(timezone.utc)
    date_stamp = now.strftime('%Y-%m-%dT%H%M%S')
    unix_ts    = int(now.timestamp())
    coll_date  = metadata.get('collection_date', now.isoformat())

    lines = [
        '<!--Format:   1.0-->',
        f'<!--Date:     {date_stamp};{unix_ts}-->',
        '<!--Source:   bwForCluster NEMO 2-->',
        f'<!--Collected: {coll_date}-->',
        '<!--Comment1: Installed modulefiles (wo hidden/obsolete) of all shareholders-->',
        '<!--Comment2: generated by: generate_mediawiki.py --mode spiderlein -->',
        '<!--Title:    Available software modules on bwForCluster NEMO 2-->',
        '<!--Columns:-->',
        '<!--     1./name     = Software modulefile package name-->',
        '<!--     2./version  = Software modulefile package version-->',
        '<!--     3./category = Modulefile category of software-->',
        '<!--     4./eligible = Defines for which user group software is available-->',
        '<!--     5./cluster  = on which cluster software is installed-->',
        '<!--     6./whatis   = (Condensed) whatis text as extracted for module whatis-->',
        '<!--     7./variants = Variants as implemented in the hieraric modulefile system-->',
        '<!---->',
        '<!--Data:-->',
    ]

    for cat, sw, ver, desc in rows:
        lines.append(
            f'<tr><td>{_html.escape(sw)}</td>'
            f'<td>{_html.escape(ver)}</td>'
            f'<td>{_html.escape(cat)}</td>'
            f'<td>all</td>'
            f'<td>bwForCluster NEMO 2</td>'
            f'<td>{_html.escape(desc)}</td>'
            f'<td>-</td></tr>'
        )

    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# Page generators
# ---------------------------------------------------------------------------

def _arch_info_section(_metadata: Dict) -> str:
    """Architecture overview box."""
    lines = [
        '== Architecture Overview ==',
        '',
        '{| class="wikitable"',
        '|-',
        '! Architecture !! Group !! Notes',
    ]
    for canonical, members in ARCH_GROUPS.items():
        for arch in members:
            group_label = ARCH_GROUP_LABELS.get(canonical, canonical)
            note = ''
            if arch == canonical:
                note = 'canonical (queried by collector)'
            else:
                note = f'symbolic link → {canonical}'
            lines.append('|-')
            lines.append(
                f'| <code>{arch}</code> || {group_label} || {note}')
    lines.append('|}')
    lines.append('')
    lines.append(
        "'''Note:''' Architectures within the same group share an identical "
        "module tree.  The modules listed below are therefore the same for "
        "all members of each group."
    )
    lines.append('')
    return '\n'.join(lines)


def _category_table(software_dict: Dict[str, List[Dict]],
                     collapsible: bool = True,
                     collapsed: bool = True) -> str:
    """Generate a wikitable for one category's modules."""
    css = 'wikitable sortable'
    if collapsible:
        css += ' mw-collapsible'
        if collapsed:
            css += ' mw-collapsed'

    lines = [
        f'{{| class="{css}" style="width:100%"',
        '|-',
        '! Software !! Versions !! Module path !! Description',
    ]
    for sw_name in sorted(software_dict, key=str.lower):
        versions_list = software_dict[sw_name]
        versions = sorted({v['version'] for v in versions_list})
        ver_str = ', '.join(f'<code>{wiki_escape(v)}</code>' for v in versions)
        full_name = versions_list[0].get('full_name', '')
        # Show module load path without version
        parts = full_name.split('/')
        if len(parts) >= 3:
            mod_path = f'{parts[0]}/{parts[1]}'
        else:
            mod_path = parts[0] if parts else ''
        desc = shorten_desc(versions_list[0].get('description', ''))
        lines.append('|-')
        lines.append(
            f'| <code>{wiki_escape(sw_name)}</code> '
            f'|| {ver_str} '
            f'|| <code>{wiki_escape(mod_path)}</code> '
            f'|| {wiki_escape(desc)}'
        )
    lines.append('|}')
    return '\n'.join(lines)


def _stats_table(metadata: Dict, modules: List[Dict] = None) -> str:
    """Summary statistics table with unique module counts per arch group."""
    lines = [
        '{| class="wikitable"',
        '|-',
        '! Metric !! Value',
        '|-',
        f'| Collection date || {metadata.get("collection_date", "n/a")}',
    ]
    if modules is not None:
        seen_all: set = set()
        for canonical, members in ARCH_GROUPS.items():
            unique = unique_modules_for_group(modules, members)
            if not unique:
                continue
            group_label = ARCH_GROUP_LABELS.get(canonical, canonical)
            lines.append('|-')
            lines.append(f'| Unique modules ({group_label}) || {len(unique)}')
            for m in unique:
                seen_all.add((m['software'], m['version'], m['category']))
        lines.append('|-')
        lines.append(f'| Total unique modules (all groups) || {len(seen_all)}')
    else:
        for arch, count in metadata.get('modules_per_arch', {}).items():
            lines.append('|-')
            lines.append(f'| Modules ({arch}) || {count}')
        lines.append('|-')
        lines.append(
            f'| Total modules || {metadata.get("total_modules", "n/a")}')
    lines.append('|}')
    return '\n'.join(lines)


def generate_combined(modules: List[Dict], metadata: Dict) -> str:
    """One page with all architecture groups, categories as collapsible
    sections."""
    page = [
        '= bwForCluster NEMO 2 – Available EasyBuild Modules =',
        '',
        'This page is automatically generated from the module data '
        'collected on the HPC cluster.',
        '',
        _stats_table(metadata, modules),
        '',
        _arch_info_section(metadata),
    ]

    for canonical, members in ARCH_GROUPS.items():
        group_label = ARCH_GROUP_LABELS.get(canonical, canonical)
        unique = unique_modules_for_group(modules, members)
        if not unique:
            continue

        page.append(f'== {group_label} ==')
        page.append('')
        page.append(
            f"Available for: {', '.join(f'<code>{a}</code>' for a in members)}"
        )
        page.append('')

        by_cat = group_by_category(unique)
        for cat_name in sorted(by_cat):
            sw_dict = by_cat[cat_name]
            n = sum(len(v) for v in sw_dict.values())
            page.append(f'=== {cat_name} ({len(sw_dict)} software, {n} versions) ===')
            page.append('')
            page.append(_category_table(sw_dict, collapsible=True, collapsed=True))
            page.append('')

    return '\n'.join(page)


def generate_per_category(modules: List[Dict],
                          _metadata: Dict) -> Dict[str, str]:
    """One page per category (across all architectures)."""
    pages: Dict[str, str] = {}

    # De-duplicate across identical arch groups
    dedup: Dict[str, List[Dict]] = {}
    for canonical, members in ARCH_GROUPS.items():
        unique = unique_modules_for_group(modules, members)
        dedup[canonical] = unique

    all_cats = set()
    for mods in dedup.values():
        for m in mods:
            all_cats.add(m['category'])

    for cat_name in sorted(all_cats):
        safe_name = re.sub(r'[^A-Za-z0-9_]', '_', cat_name)
        lines = [
            f'= {cat_name} =',
            '',
            f'Modules in category **{cat_name}** on bwForCluster NEMO 2.',
            '',
        ]
        for canonical, members in ARCH_GROUPS.items():
            group_label = ARCH_GROUP_LABELS.get(canonical, canonical)
            cat_mods = [m for m in dedup[canonical] if m['category'] == cat_name]
            if not cat_mods:
                continue
            by_sw: Dict[str, List[Dict]] = defaultdict(list)
            for m in cat_mods:
                by_sw[m['software']].append(m)

            lines.append(f'== {group_label} ==')
            lines.append('')
            lines.append(_category_table(by_sw, collapsible=False))
            lines.append('')

        pages[safe_name] = '\n'.join(lines)

    return pages


def generate_per_arch(modules: List[Dict],
                      _metadata: Dict) -> Dict[str, str]:
    """One page per architecture group."""
    pages: Dict[str, str] = {}
    for canonical, members in ARCH_GROUPS.items():
        group_label = ARCH_GROUP_LABELS.get(canonical, canonical)
        unique = unique_modules_for_group(modules, members)
        if not unique:
            continue

        lines = [
            f'= EasyBuild Modules – {group_label} =',
            '',
            f"Architectures: {', '.join(f'<code>{a}</code>' for a in members)}",
            '',
            f"These architectures share an identical module tree "
            f"(symbolic links to <code>{canonical}</code>).",
            '',
        ]
        by_cat = group_by_category(unique)
        for cat_name in sorted(by_cat):
            sw_dict = by_cat[cat_name]
            n = sum(len(v) for v in sw_dict.values())
            lines.append(
                f'== {cat_name} ({len(sw_dict)} software, {n} versions) ==')
            lines.append('')
            lines.append(_category_table(sw_dict, collapsible=True, collapsed=True))
            lines.append('')

        pages[canonical] = '\n'.join(lines)

    return pages


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Generate MediaWiki pages from collected module data')
    parser.add_argument('--data-dir', '-d', default='./data',
                        help='Directory with modules_all.json (default: ./data)')
    parser.add_argument('--output-dir', '-o', default='./wiki',
                        help='Output directory for .mediawiki files (default: ./wiki)')
    parser.add_argument('--mode', '-m',
                        choices=['combined', 'per-category', 'per-arch', 'spiderlein'],
                        default='combined',
                        help='Page generation mode (default: combined)')
    parser.add_argument('--allowlist',
                        default='./scripts/spiderlein_allowlist.txt',
                        help='Allowlist file for spiderlein mode '
                             '(default: ./scripts/spiderlein_allowlist.txt)')
    parser.add_argument('--cat-rename',
                        default='./scripts/spiderlein_cat_rename.json',
                        help='Category/software rename config for spiderlein mode '
                             '(default: ./scripts/spiderlein_cat_rename.json)')
    args = parser.parse_args()

    modules, metadata = load_data(args.data_dir)
    if not modules:
        print("No module data found.  Run collect_modules.py first.")
        return 1

    os.makedirs(args.output_dir, exist_ok=True)

    if args.mode == 'combined':
        page = generate_combined(modules, metadata)
        path = os.path.join(args.output_dir, 'Easybuild_Module_List.mediawiki')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(page)
        print(f"Combined page: {path}")

    elif args.mode == 'per-category':
        pages = generate_per_category(modules, metadata)
        for name, content in pages.items():
            path = os.path.join(args.output_dir, f'Modules_{name}.mediawiki')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Category page: {path}")

    elif args.mode == 'per-arch':
        pages = generate_per_arch(modules, metadata)
        for name, content in pages.items():
            path = os.path.join(args.output_dir, f'Modules_{name}.mediawiki')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Architecture page: {path}")

    elif args.mode == 'spiderlein':
        allowlist, renames = load_spiderlein_config(args.allowlist, args.cat_rename)
        content = generate_spiderlein(modules, metadata, allowlist, renames)
        path = os.path.join(args.output_dir, 'nemo2_spiderlein_gsorted.html')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Spiderlein HTML: {path}")
        if allowlist:
            print(f"  Allowlist entries applied: {len(allowlist)}")
        else:
            print("  No allowlist — all modules included")
        sw_renames  = renames.get('software', {})
        cat_renames = renames.get('category', {})
        if sw_renames:
            print(f"  Software renames: {sw_renames}")
        if cat_renames:
            print(f"  Category renames: {cat_renames}")

    print(f"\nDone!  {args.mode} mode → {args.output_dir}/")
    return 0


if __name__ == "__main__":
    exit(main())
