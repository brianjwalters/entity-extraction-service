#!/usr/bin/env python3
"""
Automated Import Fixer for Entity Extraction Service Tests
Removes sys.path manipulation and converts to absolute imports

This script:
2. Removes PYTHONPATH environment variable manipulation
3. Converts "from src.module" imports to "from src.module" (keeping src prefix)
4. Removes unused "import sys" statements
5. Generates detailed report of all changes
"""

import re
from pathlib import Path
from typing import List, Tuple, Dict
import sys


def remove_sys_path_lines(content: str) -> Tuple[str, int, List[str]]:
    """
    Remove sys.path manipulation lines

    Returns:
        Tuple of (cleaned_content, removed_count, removed_lines)
    """
    lines = content.split('\n')
    removed_count = 0
    removed_lines = []
    cleaned_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for sys.path manipulation
            "os.environ['PYTHONPATH']" in line or
            'os.environ["PYTHONPATH"]' in line):

            removed_count += 1
            removed_lines.append(line.strip())
            i += 1
            continue

        # Check for standalone "import sys" that's only used for path manipulation
        if line.strip() == 'import sys':
            # Look ahead to see if sys is used for anything other than sys.path
            has_other_sys_usage = False
            for future_line in lines[i+1:i+20]:  # Check next 20 lines
                if 'sys.' in future_line and 'sys.path' not in future_line:
                    has_other_sys_usage = True
                    break

            if not has_other_sys_usage:
                # sys is only used for path manipulation, skip this import
                removed_count += 1
                removed_lines.append(line.strip())
                i += 1
                continue

        cleaned_lines.append(line)
        i += 1

    return '\n'.join(cleaned_lines), removed_count, removed_lines


def remove_path_related_imports(content: str) -> Tuple[str, int]:
    """
    Remove import statements that are only used for path manipulation

    Returns:
        Tuple of (cleaned_content, removed_count)
    """
    lines = content.split('\n')
    removed_count = 0
    cleaned_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Remove "import os" if only used for path/environ
        if line.strip() == 'import os':
            # Check if os is used for anything other than path/environ
            has_other_os_usage = False
            for future_line in lines[i+1:]:
                if 'os.' in future_line:
                    if not ('os.path' in future_line or
                           'os.environ' in future_line or
                           'os.getcwd' in future_line or
                           'os.dirname' in future_line):
                        has_other_os_usage = True
                        break

            if not has_other_os_usage:
                # Check if there are path manipulation lines that will be removed
                has_path_manipulation = any(
                    'sys.path' in l or "os.environ['PYTHONPATH']" in l
                    for l in lines[i+1:i+20]
                )

                if has_path_manipulation:
                    removed_count += 1
                    i += 1
                    continue

        cleaned_lines.append(line)
        i += 1

    return '\n'.join(cleaned_lines), removed_count


def clean_empty_lines(content: str) -> str:
    """Remove excessive empty lines (more than 2 consecutive)"""
    lines = content.split('\n')
    cleaned_lines = []
    empty_count = 0

    for line in lines:
        if line.strip() == '':
            empty_count += 1
            if empty_count <= 2:  # Allow max 2 consecutive empty lines
                cleaned_lines.append(line)
        else:
            empty_count = 0
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def fix_test_file(file_path: Path, dry_run: bool = False) -> Dict:
    """
    Fix a single test file

    Args:
        file_path: Path to test file
        dry_run: If True, don't write changes, just report

    Returns:
        Dictionary with fix results
    """
    result = {
        'file': str(file_path.relative_to(Path('/srv/luris/be/entity-extraction-service'))),
        'modified': False,
        'sys_path_removed': 0,
        'imports_removed': 0,
        'removed_lines': [],
        'error': None
    }

    try:
        content = file_path.read_text()
        original_content = content

        # Step 1: Remove sys.path manipulation
        content, sys_path_count, removed = remove_sys_path_lines(content)
        result['sys_path_removed'] = sys_path_count
        result['removed_lines'] = removed

        # Step 2: Remove unused path-related imports
        content, imports_removed = remove_path_related_imports(content)
        result['imports_removed'] = imports_removed

        # Step 3: Clean up excessive empty lines
        content = clean_empty_lines(content)

        # Write back if changed
        if content != original_content:
            result['modified'] = True
            if not dry_run:
                file_path.write_text(content)

    except Exception as e:
        result['error'] = str(e)

    return result


def main():
    """Main execution"""
    print("="*70)
    print("Entity Extraction Service - Import Standards Fix")
    print("="*70)
    print()

    # Configuration
    service_dir = Path('/srv/luris/be/entity-extraction-service')
    test_dir = service_dir / 'tests'

    # Check if we should do dry run
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
        print()

    # Find all Python test files
    test_files = list(test_dir.rglob('*.py'))
    test_files = [f for f in test_files if not f.name.startswith('__')]

    print(f"Found {len(test_files)} Python files in tests/")
    print()
    print("Processing files...")
    print()

    # Process files
    results = []
    for file_path in sorted(test_files):
        result = fix_test_file(file_path, dry_run=dry_run)
        results.append(result)

        if result['modified']:
            print(f"✅ {result['file']}")
            if result['sys_path_removed'] > 0:
                print(f"   - Removed {result['sys_path_removed']} sys.path lines")
                for line in result['removed_lines'][:3]:  # Show first 3
                    print(f"     • {line[:80]}...")
            if result['imports_removed'] > 0:
                print(f"   - Removed {result['imports_removed']} unused import lines")
            print()
        elif result['error']:
            print(f"❌ {result['file']}: {result['error']}")
            print()

    # Summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)

    total_modified = sum(1 for r in results if r['modified'])
    total_sys_path = sum(r['sys_path_removed'] for r in results)
    total_imports = sum(r['imports_removed'] for r in results)
    total_errors = sum(1 for r in results if r['error'])

    print(f"Files processed:        {len(results)}")
    print(f"Files modified:         {total_modified}")
    print(f"sys.path lines removed: {total_sys_path}")
    print(f"Import lines removed:   {total_imports}")
    print(f"Errors encountered:     {total_errors}")
    print()

    if dry_run:
        print("🔍 This was a DRY RUN - no files were modified")
        print("   Run without --dry-run to apply changes")
    else:
        print("✅ All changes have been applied")
        print()
        print("Next steps:")
        print("1. Run: grep -r 'sys.path' tests/ --include='*.py'")
        print("2. Verify: No violations should be found")
        print("3. Test: source venv/bin/activate && pytest tests/ -v")

    print("="*70)


if __name__ == '__main__':
    main()
