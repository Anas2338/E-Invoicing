#!/usr/bin/env python3
"""
Validate the OpenAI Agent SDK skill structure and content
"""

import os
import yaml
from pathlib import Path
import sys

def validate_yaml_frontmatter(file_path: str) -> dict:
    """Validate YAML frontmatter in SKILL.md"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if content.startswith('---'):
        # Find the end of YAML frontmatter
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                return frontmatter
            except yaml.YAMLError as e:
                print(f"❌ Invalid YAML in {file_path}: {e}")
                return None

    print(f"❌ No YAML frontmatter found in {file_path}")
    return None

def validate_skill_structure(skill_dir: str) -> list:
    """Validate the skill directory structure"""
    errors = []
    skill_path = Path(skill_dir)

    # Check required files
    required_files = ["SKILL.md"]
    for req_file in required_files:
        if not (skill_path / req_file).exists():
            errors.append(f"Missing required file: {req_file}")

    # Check required directories
    required_dirs = ["scripts", "references", "assets"]
    for req_dir in required_dirs:
        if not (skill_path / req_dir).exists():
            errors.append(f"Missing required directory: {req_dir}")

    # Validate SKILL.md frontmatter
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        frontmatter = validate_yaml_frontmatter(skill_md)
        if frontmatter:
            if "name" not in frontmatter:
                errors.append("SKILL.md missing 'name' in frontmatter")
            if "description" not in frontmatter:
                errors.append("SKILL.md missing 'description' in frontmatter")
            elif len(frontmatter["description"]) < 20:
                errors.append("SKILL.md description should be more descriptive (at least 20 characters)")
        else:
            errors.append("SKILL.md has invalid YAML frontmatter")

    # Check reference files exist
    reference_files = [
        "references/multi-agent.md",
        "references/security.md",
        "references/cost-control.md",
        "references/error-handling.md"
    ]

    for ref_file in reference_files:
        if not (skill_path / ref_file).exists():
            errors.append(f"Missing reference file: {ref_file}")

    # Check script files exist
    script_files = [
        "scripts/setup_agent.py"
    ]

    for script_file in script_files:
        if not (skill_path / script_file).exists():
            errors.append(f"Missing script file: {script_file}")

    # Check asset files exist
    asset_files = [
        "assets/basic-agent-template.md"
    ]

    for asset_file in asset_files:
        if not (skill_path / asset_file).exists():
            errors.append(f"Missing asset file: {asset_file}")

    return errors

def validate_content_quality(skill_dir: str) -> list:
    """Validate content quality in skill files"""
    errors = []
    skill_path = Path(skill_dir)

    # Check SKILL.md has sufficient content
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for essential sections
        essential_sections = [
            "When to Use This Skill",
            "Core Components",
            "Best Practices",
            "Common Patterns"
        ]

        missing_sections = []
        for section in essential_sections:
            if f"# {section}" not in content and f"## {section}" not in content:
                missing_sections.append(section)

        if missing_sections:
            errors.append(f"SKILL.md missing essential sections: {', '.join(missing_sections)}")

    # Validate reference files have content
    reference_files = [
        "references/multi-agent.md",
        "references/security.md",
        "references/cost-control.md",
        "references/error-handling.md"
    ]

    for ref_file in reference_files:
        ref_path = skill_path / ref_file
        if ref_path.exists():
            with open(ref_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content.strip()) < 50:  # At least 50 characters of content
                    errors.append(f"Reference file {ref_file} appears to have insufficient content")

    return errors

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate OpenAI Agent SDK skill")
    parser.add_argument("--dir", default=".", help="Skill directory path (default: current directory)")

    args = parser.parse_args()

    print("(Validating OpenAI Agent SDK skill...")
    print(f"[Checking directory: {args.dir}]")

    # Validate structure
    structure_errors = validate_skill_structure(args.dir)

    # Validate content quality
    content_errors = validate_content_quality(args.dir)

    all_errors = structure_errors + content_errors

    if all_errors:
        print("\n[ERROR] Validation failed with the following errors:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")

        print(f"\n[ERROR] Total errors: {len(all_errors)}")
        return 1
    else:
        print("\n[SUCCESS] All validations passed!")
        print("[READY] The OpenAI Agent SDK skill is properly structured and ready to use.")
        return 0

if __name__ == "__main__":
    exit(main())