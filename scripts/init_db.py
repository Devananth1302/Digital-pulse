"""Script to initialize the database schema in Supabase.

Usage:
    python scripts/init_db.py

Reads the SQL from database/schemas/001_initial.sql and prints it.
You must run this SQL in the Supabase SQL Editor manually,
as Supabase does not support direct DDL execution via the client SDK.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def main():
    schema_path = project_root / "database" / "schemas" / "001_initial.sql"
    migration_path = project_root / "database" / "migrations" / "000_enable_vector.sql"

    print("=" * 60)
    print("Digital Pulse - Database Initialization")
    print("=" * 60)
    print()
    print("Run the following SQL in your Supabase SQL Editor:")
    print()
    print("-" * 60)

    if migration_path.exists():
        print(migration_path.read_text())
        print()

    if schema_path.exists():
        print(schema_path.read_text())
    else:
        print(f"ERROR: Schema file not found at {schema_path}")
        sys.exit(1)

    print("-" * 60)
    print()
    print("Copy the SQL above and run it in your Supabase Dashboard:")
    print("  https://supabase.com/dashboard → SQL Editor")
    print()


if __name__ == "__main__":
    main()
