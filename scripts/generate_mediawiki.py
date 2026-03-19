#!/usr/bin/env python3
"""
Generate MediaWiki pages from collected module JSON data.

Compatible with MediaWiki 1.39.  Produces:
  - A single combined page  (--mode combined, default)
  - One page per category    (--mode per-category)
  - One page per architecture group (--mode per-arch)

Uses collapsible wikitables, sortable tables, and <code> markup.
"""

import json
import argparse
import os
import re
from collections import defaultdict
from typing import Dict, List

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


def _stats_table(metadata: Dict) -> str:
    """Summary statistics table."""
    lines = [
        '{| class="wikitable"',
        '|-',
        '! Metric !! Value',
        '|-',
        f'| Collection date || {metadata.get("collection_date", "n/a")}',
    ]
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
        _stats_table(metadata),
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

    page.append('')
    page.append(
        '[[Category:NEMO2]][[Category:Software]]'
    )
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

        lines.append('[[Category:NEMO2]][[Category:Software]]')
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

        lines.append('[[Category:NEMO2]][[Category:Software]]')
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
                        choices=['combined', 'per-category', 'per-arch'],
                        default='combined',
                        help='Page generation mode (default: combined)')
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

    print(f"\nDone!  {args.mode} mode → {args.output_dir}/")
    return 0


if __name__ == "__main__":
    exit(main())
