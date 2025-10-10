#!/usr/bin/env python3
"""
bwForCluster NEMO 2 Easybuild Module Collector
Collects information about available software modules from different HPC architectures
and creates machine-readable JSON outputs for Git repository.
"""

import subprocess
import json
import re
import os
import argparse
from datetime import datetime
from typing import Dict, List, Tuple


class ModuleCollector:
    def __init__(self):
        self.architectures = ['genoa', 'h200', 'l40s', 'mi300a', 'milan']
        self.categories = {
            'bio': 'Biology Software',
            'chem': 'Chemistry Software', 
            'compiler': 'Compilers',
            'math': 'Mathematics Software',
            'phys': 'Physics Software',
            'tools': 'Development Tools',
            'lib': 'Libraries',
            'data': 'Data Analysis',
            'ai': 'Artificial Intelligence',
            'vis': 'Visualization'
        }
    
    def run_module_command(self, architecture: str) -> str:
        """
        Executes the module avail command for a specific architecture
        """
        try:
            # Load the corresponding architecture
            load_cmd = f"module load arch/{architecture}"
            avail_cmd = "module avail"
            
            # Combine both commands
            full_cmd = f"{load_cmd} && {avail_cmd}"
            
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # module avail outputs via stderr
            return result.stderr + result.stdout
            
        except subprocess.TimeoutExpired:
            print(f"Timeout when executing command for {architecture}")
            return ""
        except Exception as e:
            print(f"Error executing command for {architecture}: {e}")
            return ""
    
    def get_module_spider_data(self, architecture: str) -> Dict[str, str]:
        """
        Executes module spider once and extracts all descriptions
        """
        try:
            load_cmd = f"module load arch/{architecture}"
            spider_cmd = "module spider"
            
            full_cmd = f"{load_cmd} && {spider_cmd}"
            
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60  # Spider can take longer
            )
            
            output = result.stdout + result.stderr
            return self.parse_spider_output(output)
            
        except subprocess.TimeoutExpired:
            print(f"Timeout when executing module spider for {architecture}")
            return {}
        except Exception as e:
            print(f"Error executing module spider for {architecture}: {e}")
            return {}
    
    def parse_spider_output(self, output: str) -> Dict[str, str]:
        """
        Parses the module spider output and extracts software descriptions
        """
        descriptions = {}
        lines = output.split('\n')
        current_software = None
        current_description = []
        
        for line in lines:
            # Detect software headers (e.g. "  lang/bison:")
            if line.strip() and ':' in line and not line.startswith('    '):
                # Save previous description if available
                if current_software and current_description:
                    descriptions[current_software] = ' '.join(current_description).strip()
                
                # Extract software names (without versions)
                software_match = re.match(r'\s*(\S+):\s*', line)
                if software_match:
                    current_software = software_match.group(1)
                    current_description = []
                else:
                    current_software = None
                    current_description = []
            
            # Collect description lines (start with 4+ spaces)
            elif line.startswith('    ') and current_software:
                # Skip version lines (usually contain commas and module names)
                if not ('/' in line and ',' in line):
                    desc_line = line.strip()
                    if desc_line:
                        current_description.append(desc_line)
        
        # Save last description
        if current_software and current_description:
            descriptions[current_software] = ' '.join(current_description).strip()
        
        return descriptions
    
    def parse_module_output(self, output: str, architecture: str, spider_descriptions: Dict[str, str]) -> List[Dict]:
        """
        Parses the module avail output and extracts module information
        """
        modules = []
        current_category = "Unknown"
        
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Detect category headers (e.g. "Chemistry Software")
            if line.startswith('---') and line.endswith('---'):
                # Extract category names between dashes
                category_match = re.search(r'---+\s*(.+?)\s*---+', line)
                if category_match:
                    current_category = category_match.group(1).strip()
                continue
            
            # Detect modules (contain version numbers and optional flags)
            if '/' in line and not line.startswith('-'):
                # Split line into individual modules
                module_entries = re.findall(r'(\S+/\S+(?:\s*\([^)]+\))?)', line)
                
                for entry in module_entries:
                    # Filter out arch/* modules
                    clean_entry = re.sub(r'\s*\([^)]+\)$', '', entry.strip())
                    if clean_entry.startswith('arch/'):
                        continue
                    
                    module_info = self.parse_single_module(entry, current_category, architecture, spider_descriptions)
                    if module_info:
                        modules.append(module_info)
        
        return modules
    
    def parse_single_module(self, module_entry: str, category: str, architecture: str, spider_descriptions: Dict[str, str]) -> Dict:
        """
        Parses a single module entry
        """
        # Remove flags like (D), (L), (S) at the end
        clean_entry = re.sub(r'\s*\([^)]+\)$', '', module_entry.strip())
        
        # Split into components: category/software/version
        parts = clean_entry.split('/')
        if len(parts) < 2:
            return None
        
        # Determine software and version based on number of parts
        if len(parts) == 2:
            # Format: software/version
            software = parts[0]
            version = parts[1]
            detected_category = self.detect_category(software, category)
            software_key = software
        else:
            # Format: category/software/version (3+ parts)
            category_prefix = parts[0]
            software = parts[1]
            version = '/'.join(parts[2:])  # Rest is version (can contain more slashes)
            
            # Use category prefix for better categorization
            detected_category = self.detect_category_from_prefix(category_prefix, category)
            software_key = f"{category_prefix}/{software}"
        
        # Get description from spider data
        description = spider_descriptions.get(software_key, "")
        
        # Fallback description if spider has no data
        if not description:
            description = f"{software} version {version} for {architecture} architecture"
        
        return {
            'software': software,
            'version': version,
            'category': detected_category,
            'architecture': architecture,
            'description': description,
            'full_name': clean_entry,
            'collected_at': datetime.now().isoformat()
        }
    
    def detect_category(self, software: str, header_category: str) -> str:
        """
        Determines category based on software name and header
        """
        # Check if software starts with known prefix
        for prefix, cat_name in self.categories.items():
            if software.startswith(prefix + '/') or software == prefix:
                return cat_name
        
        # Use header category if available
        if header_category and header_category != "Unknown":
            return header_category
        
        # Fallback categories based on software name
        software_lower = software.lower()
        if any(term in software_lower for term in ['gcc', 'intel', 'llvm', 'go']):
            return 'Compilers'
        elif any(term in software_lower for term in ['python', 'r-', 'julia']):
            return 'Programming Languages'
        elif any(term in software_lower for term in ['mpi', 'openmpi', 'cuda']):
            return 'Parallel Computing'
        else:
            return 'Other'
    
    def detect_category_from_prefix(self, category_prefix: str, header_category: str) -> str:
        """
        Determines category based on module prefix (e.g. devel, bio, chem)
        """
        # Direct mapping of known prefixes
        prefix_mapping = {
            'devel': 'Development Tools',
            'bio': 'Biology Software',
            'chem': 'Chemistry Software',
            'compiler': 'Compilers',
            'math': 'Mathematics Software',
            'phys': 'Physics Software',
            'tools': 'Development Tools',
            'lib': 'Libraries',
            'data': 'Data Analysis',
            'ai': 'Artificial Intelligence',
            'vis': 'Visualization',
            'lang': 'Programming Languages',
            'mpi': 'Parallel Computing',
            'gpu': 'GPU Computing',
            'system': 'System Tools',
            'numlib': 'Numerical Libraries',
            'toolchain': 'Toolchains'
        }
        
        # Check direct mapping
        if category_prefix.lower() in prefix_mapping:
            return prefix_mapping[category_prefix.lower()]
        
        # Check if prefix is in defined categories
        if category_prefix in self.categories:
            return self.categories[category_prefix]
        
        # Use header category if available
        if header_category and header_category != "Unknown":
            return header_category
        
        return 'Other'
    
    def collect_all_modules(self) -> Dict[str, List[Dict]]:
        """
        Collects modules for all architectures
        """
        all_modules = {}
        
        for arch in self.architectures:
            print(f"Collecting modules for architecture: {arch}")
            
            # Get spider data once for this architecture
            print(f"  -> Running module spider...")
            spider_descriptions = self.get_module_spider_data(arch)
            print(f"  -> {len(spider_descriptions)} software descriptions found")
            
            # Get module avail output
            output = self.run_module_command(arch)
            
            if output:
                modules = self.parse_module_output(output, arch, spider_descriptions)
                all_modules[arch] = modules
                print(f"  -> {len(modules)} modules found")
            else:
                print(f"  -> No modules found or error occurred")
                all_modules[arch] = []
        
        return all_modules
    
    def save_data(self, modules_data: Dict[str, List[Dict]], output_dir: str):
        """
        Saves the collected data to JSON files
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Save data per architecture
        for arch, modules in modules_data.items():
            arch_file = os.path.join(output_dir, f"modules_{arch}.json")
            with open(arch_file, 'w', encoding='utf-8') as f:
                json.dump(modules, f, indent=2, ensure_ascii=False)
            print(f"Data for {arch} saved: {arch_file}")
        
        # Create combined file
        all_modules = []
        for modules in modules_data.values():
            all_modules.extend(modules)
        
        combined_file = os.path.join(output_dir, "modules_all.json")
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump(all_modules, f, indent=2, ensure_ascii=False)
        print(f"Combined data saved: {combined_file}")
        
        # Create metadata
        metadata = {
            'collection_date': datetime.now().isoformat(),
            'architectures': list(modules_data.keys()),
            'total_modules': len(all_modules),
            'modules_per_arch': {arch: len(modules) for arch, modules in modules_data.items()}
        }
        
        metadata_file = os.path.join(output_dir, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"Metadata saved: {metadata_file}")


def main():
    parser = argparse.ArgumentParser(description='bwForCluster NEMO 2 Easybuild Module Collector')
    parser.add_argument('--output-dir', '-o', default='./data',
                       help='Output directory for JSON files')
    parser.add_argument('--architecture', '-a', 
                       help='Collect only for specific architecture')
    
    args = parser.parse_args()
    
    collector = ModuleCollector()
    
    if args.architecture:
        if args.architecture not in collector.architectures:
            print(f"Unknown architecture: {args.architecture}")
            print(f"Available architectures: {', '.join(collector.architectures)}")
            return 1
        
        collector.architectures = [args.architecture]
    
    print("Starting module collection...")
    modules_data = collector.collect_all_modules()
    
    print("\nSaving data...")
    collector.save_data(modules_data, args.output_dir)
    
    print("\nCollection completed!")
    return 0


if __name__ == "__main__":
    exit(main())