#!/usr/bin/env python3
"""
Package the MCP SDK Assistant skill into a distributable format
"""

import os
import zipfile
import shutil
from pathlib import Path

def package_skill(skill_dir: str, output_dir: str = "."):
    """Package the skill into a .skill file"""

    skill_path = Path(skill_dir)
    skill_name = skill_path.name

    # Validate required files
    required_files = ["SKILL.md"]
    for req_file in required_files:
        if not (skill_path / req_file).exists():
            raise FileNotFoundError(f"Required file {req_file} not found in {skill_dir}")

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create the package file
    package_file = output_path / f"{skill_name}.skill"

    # Create the zip archive
    with zipfile.ZipFile(package_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(skill_dir):
            for file in files:
                file_path = Path(root) / file
                # Add file to zip with relative path
                zipf.write(file_path, file_path.relative_to(skill_path.parent))

    print(f"[SUCCESS] Skill packaged successfully: {package_file}")
    print(f"[DIR] Skill directory: {skill_dir}")
    print(f"[SIZE] Package size: {package_file.stat().st_size} bytes")

    return str(package_file)

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Package MCP SDK Assistant skill")
    parser.add_argument("--dir", default=".", help="Skill directory path (default: current directory)")
    parser.add_argument("--output", "-o", default=".", help="Output directory for package (default: current directory)")

    args = parser.parse_args()

    try:
        package_path = package_skill(args.dir, args.output)
        print(f"\n[COMPLETE] Skill package created at: {package_path}")
    except Exception as e:
        print(f"[ERROR] Error packaging skill: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())