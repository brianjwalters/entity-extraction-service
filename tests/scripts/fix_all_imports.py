#!/usr/bin/env python3
"""
Fix imports in all moved scripts to use absolute imports instead of sys.path manipulation.

This script:
1. Removes sys.path manipulation lines
2. Ensures absolute imports from project root
3. Adds usage documentation headers
"""

import os
import re
from pathlib import Path


def fix_imports_in_file(filepath: Path) -> tuple[bool, list[str]]:
    """
    Fix imports in a single file.

    Returns:
        (changed, issues) - Whether file was changed and list of issues found
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    issues = []

    # Pattern 1: Remove sys.path.insert/append lines
    sys_path_patterns = [
        r'sys\.path\.insert\([^)]+\)\s*\n',
        r'sys\.path\.append\([^)]+\)\s*\n',
    ]

    for pattern in sys_path_patterns:
        matches = re.findall(pattern, content)
        if matches:
            issues.append(f"Removed {len(matches)} sys.path manipulation(s)")
            content = re.sub(pattern, '', content)

    # Pattern 2: Remove import sys if it's only used for sys.path
    # Check if 'import sys' exists but sys is not used elsewhere
    if 'import sys' in content and not re.search(r'\bsys\.[^p]', content):
        # sys is only used for sys.path, safe to remove
        content = re.sub(r'^import sys\s*\n', '', content, flags=re.MULTILINE)
        issues.append("Removed unused 'import sys'")

    # Pattern 3: Fix relative imports to absolute
    # from src.xxx → from src.xxx (already correct)
    # from ...src.xxx → from src.xxx
    relative_import_pattern = r'from \.+src\.'
    if re.search(relative_import_pattern, content):
        content = re.sub(r'from \.+src\.', 'from src.', content)
        issues.append("Fixed relative imports to absolute")

    # Pattern 4: Add usage documentation if missing
    if '#!/usr/bin/env python3' not in content[:100]:
        script_name = filepath.name
        header = f'''#!/usr/bin/env python3
"""
{script_name} - Entity Extraction Utility Script

Usage:
    cd /srv/luris/be/entity-extraction-service
    source venv/bin/activate
    python tests/scripts/{filepath.parent.name}/{script_name}
"""

'''
        content = header + content
        issues.append("Added usage header")

    # Write back if changed
    changed = content != original_content
    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    return changed, issues


def main():
    """Fix imports in all scripts."""
    scripts_dir = Path(__file__).parent

    categories = ['debug', 'analysis', 'archived', 'utilities']

    total_files = 0
    total_changed = 0

    for category in categories:
        category_dir = scripts_dir / category
        if not category_dir.exists():
            continue

        print(f"\n=== Processing {category}/ ===")

        py_files = list(category_dir.glob('*.py'))
        for filepath in sorted(py_files):
            total_files += 1
            changed, issues = fix_imports_in_file(filepath)

            if changed:
                total_changed += 1
                print(f"✅ {filepath.name}")
                for issue in issues:
                    print(f"   - {issue}")
            else:
                print(f"⏭️  {filepath.name} (no changes needed)")

    print(f"\n" + "="*60)
    print(f"Summary: Fixed {total_changed}/{total_files} files")
    print("="*60)


if __name__ == '__main__':
    main()
