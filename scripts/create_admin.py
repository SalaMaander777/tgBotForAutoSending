#!/usr/bin/env python3
"""
Generate a bcrypt hash for the admin password.

Usage:
    python scripts/create_admin.py
    python scripts/create_admin.py --password mysecretpassword
"""

import argparse
import getpass
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate bcrypt hash for admin password")
    parser.add_argument(
        "--password",
        help="Password to hash (if not provided, will prompt securely)",
    )
    args = parser.parse_args()

    try:
        import bcrypt
    except ImportError:
        print("ERROR: bcrypt is not installed. Run: pip install bcrypt", file=sys.stderr)
        sys.exit(1)

    if args.password:
        password = args.password
    else:
        password = getpass.getpass("Enter admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("ERROR: Passwords do not match", file=sys.stderr)
            sys.exit(1)

    if len(password) < 8:
        print("WARNING: Password is shorter than 8 characters", file=sys.stderr)

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    print("\n=== Add this to your .env file ===")
    print(f"ADMIN_PASSWORD_HASH={hashed}")
    print("\n=== Or export it ===")
    print(f"export ADMIN_PASSWORD_HASH='{hashed}'")


if __name__ == "__main__":
    main()
