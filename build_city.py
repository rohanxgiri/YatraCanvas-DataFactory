#!/usr/bin/env python3
"""Convenience entrypoint script for building a city dataset."""

import sys
from datafactory.cli import app


def parse_and_run():
    args = sys.argv[1:]
    if not args:
        print("Usage: python build_city.py \"City, State, Country\" [options]")
        print("Example: python build_city.py \"Jaipur, Rajasthan, India\"")
        sys.exit(1)

    # If first argument contains commas, parse it as "City, State, Country"
    first_arg = args[0]
    if "," in first_arg and not first_arg.startswith("-"):
        parts = [p.strip() for p in first_arg.split(",")]
        city = parts[0]
        state = parts[1] if len(parts) > 1 else ""
        country = parts[2] if len(parts) > 2 else "India"

        cli_args = ["build", "--city", city, "--state", state, "--country", country]
        # Append any remaining flags
        cli_args.extend(args[1:])
        sys.argv = [sys.argv[0]] + cli_args
    elif args[0] not in ("build", "validate", "export-sqlite"):
        sys.argv = [sys.argv[0], "build"] + args

    app()


if __name__ == "__main__":
    parse_and_run()
