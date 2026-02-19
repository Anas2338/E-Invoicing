#!/usr/bin/env python3
"""
SQLModel Generator Script

This script helps generate SQLModel classes from database schemas,
data models, or feature descriptions.
"""

import argparse
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class FieldDefinition:
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    index: bool = False
    unique: bool = False
    foreign_key: Optional[str] = None
    default: Optional[Any] = None


@dataclass
class ModelDefinition:
    name: str
    fields: List[FieldDefinition]
    table: bool = True


class SQLModelGenerator:
    def __init__(self):
        self.type_mapping = {
            'int': 'int',
            'integer': 'int',
            'bigint': 'int',
            'smallint': 'int',
            'string': 'str',
            'varchar': 'str',
            'text': 'str',
            'bool': 'bool',
            'boolean': 'bool',
            'float': 'float',
            'double': 'float',
            'decimal': 'float',
            'date': 'datetime.date',
            'time': 'datetime.time',
            'datetime': 'datetime.datetime',
            'timestamp': 'datetime.datetime',
        }

    def parse_schema_description(self, description: str) -> List[ModelDefinition]:
        """
        Parse a text description of a schema into model definitions.
        Supports natural language descriptions like:
        "User table with id (primary key, integer), name (string, not null), email (string, unique, not null)"
        """
        models = []

        # Split by table definitions (look for patterns like "table_name with fields..." or "create table_name...")
        table_parts = re.split(r'\.\s*(?=[A-Z][a-z]+\s+(?:table|with|create))|;\s*', description)

        for part in table_parts:
            part = part.strip()
            if not part:
                continue

            # Look for table name
            table_match = re.search(r'(?:create\s+)?(\w+)\s+(?:table|with)', part, re.IGNORECASE)
            if not table_match:
                continue

            table_name = table_match.group(1).capitalize()
            model_def = ModelDefinition(name=table_name, fields=[])

            # Extract field definitions
            # Look for patterns like: "field_name (type, constraints)" or "field_name type constraints"
            field_pattern = r'(\w+)\s*(?:\(|\s+)([a-zA-Z]+)[^,)]*(?:,\s*([^)]*))?(?:\)|\s|$)'
            field_matches = re.findall(field_pattern, part, re.IGNORECASE)

            for field_match in field_matches:
                field_name, field_type, constraints_str = field_match
                field_type = field_type.lower()

                # Parse constraints
                constraints = constraints_str.lower() if constraints_str else ""
                is_nullable = 'not null' not in constraints
                is_primary = 'primary key' in constraints
                is_index = 'index' in constraints or 'indexed' in constraints
                is_unique = 'unique' in constraints
                is_foreign = 'foreign key' in constraints

                # Try to extract foreign key reference
                fk_match = re.search(r'foreign key.*?references\s+(\w+)', constraints, re.IGNORECASE)
                foreign_key = fk_match.group(1) if fk_match else None

                # Map SQL type to Python type
                python_type = self.type_mapping.get(field_type, 'str')

                field_def = FieldDefinition(
                    name=field_name.lower(),
                    type=python_type,
                    nullable=is_nullable,
                    primary_key=is_primary,
                    index=is_index,
                    unique=is_unique,
                    foreign_key=foreign_key
                )

                model_def.fields.append(field_def)

            # If no fields were parsed, try a simpler approach
            if not model_def.fields:
                # Look for simple field definitions like "id integer", "name string", etc.
                simple_field_pattern = r'(\w+)\s+([a-zA-Z]+)'
                simple_matches = re.findall(simple_field_pattern, part)

                for field_name, field_type in simple_matches:
                    python_type = self.type_mapping.get(field_type.lower(), 'str')
                    field_def = FieldDefinition(
                        name=field_name.lower(),
                        type=python_type
                    )
                    model_def.fields.append(field_def)

            if model_def.fields:  # Only add if we have fields
                models.append(model_def)

        return models

    def generate_model_code(self, model_def: ModelDefinition) -> str:
        """Generate SQLModel code for a single model"""
        lines = []

        # Import statements
        lines.append("from sqlmodel import SQLModel, Field")
        lines.append("from typing import Optional")
        lines.append("from datetime import datetime, date")
        lines.append("")

        # Model class definition
        if model_def.table:
            lines.append(f"class {model_def.name}(SQLModel, table=True):")
        else:
            lines.append(f"class {model_def.name}(SQLModel):")

        # Add fields
        for field in model_def.fields:
            field_line = self._generate_field_line(field)
            lines.append(f"    {field_line}")

        return "\n".join(lines)

    def _generate_field_line(self, field: FieldDefinition) -> str:
        """Generate a field definition line"""
        field_args = []

        # Handle primary key
        if field.primary_key:
            field_args.append("primary_key=True")

        # Handle nullable
        if not field.primary_key and field.nullable:
            field_type = f"Optional[{field.type}]"
            default_val = "None"
        else:
            field_type = field.type
            if field.default is not None:
                default_val = repr(field.default)
            else:
                default_val = "None" if field.nullable else ""

        # Handle index
        if field.index:
            field_args.append("index=True")

        # Handle unique
        if field.unique:
            field_args.append("unique=True")

        # Handle foreign key
        if field.foreign_key:
            field_args.append(f'foreign_key="{field.foreign_key}"')

        # Handle default value
        if not field.primary_key and field.default is not None:
            field_args.append(f"default={repr(field.default)}")
        elif field.primary_key:
            field_args.append("default=None")
        elif field.nullable and not field_args:
            field_args.append("default=None")

        # Build the field definition
        args_str = f", {', '.join(field_args)}" if field_args else ""

        if field.primary_key or not field.nullable or field.default is not None:
            return f"{field.name}: {field_type} = Field({args_str})"
        else:
            return f"{field.name}: Optional[{field.type}] = Field(default=None{args_str})"

    def generate_complete_code(self, model_defs: List[ModelDefinition]) -> str:
        """Generate complete code with all models"""
        if not model_defs:
            return "# No models generated"

        # Import section
        imports = [
            "from sqlmodel import SQLModel, Field, create_engine, Session",
            "from typing import Optional, List",
            "from datetime import datetime, date",
            "from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index, func",
            ""
        ]

        # Generate each model
        models_code = []
        for model_def in model_defs:
            models_code.append(self.generate_model_code(model_def))
            models_code.append("")  # Empty line between models

        # Add example usage
        example = [
            "",
            "# Example usage:",
            "# engine = create_engine(\"sqlite:///example.db\")",
            "# SQLModel.metadata.create_all(engine)",
            ""
        ]

        return "\n".join(imports + models_code + example)


def main():
    parser = argparse.ArgumentParser(description="SQLModel Generator")
    parser.add_argument("--description", "-d", required=True,
                       help="Description of the database schema or data model")
    parser.add_argument("--output", "-o", help="Output file for generated code")

    args = parser.parse_args()

    generator = SQLModelGenerator()

    try:
        # Parse the description
        models = generator.parse_schema_description(args.description)

        if not models:
            print("❌ No models could be generated from the provided description.")
            print("Please provide a description in the format:")
            print("  'TableName with field1 (type, constraints), field2 (type, constraints)'")
            print("Example:")
            print("  'User table with id (integer, primary key), name (string, not null), email (string, unique)'")
            return 1

        # Generate code
        code = generator.generate_complete_code(models)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(code)
            print(f"✅ Code generated and saved to {args.output}")
        else:
            print("Generated SQLModel code:")
            print("="*50)
            print(code)

        # Print model summary
        print("\n📊 Generated Models Summary:")
        for model in models:
            print(f"  • {model.name}: {len(model.fields)} fields")
            for field in model.fields:
                constraints = []
                if field.primary_key: constraints.append("PK")
                if field.unique: constraints.append("UNIQUE")
                if field.index: constraints.append("INDEX")
                if field.foreign_key: constraints.append(f"FK->{field.foreign_key}")

                constraint_str = f" ({', '.join(constraints)})" if constraints else ""
                print(f"    - {field.name}: {field.type}{constraint_str}")

    except Exception as e:
        print(f"❌ Error generating models: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())