"""Adjusted from narwhals.

https://github.com/narwhals-dev/narwhals/blob/25701453aaa0556adc491e428f6d5724a1eac177/utils/bump_version.py

License: MIT
Copyright (c) 2024 Marco Gorelli
"""

# python bump-version.py <patch|minor|major>

# ruff: noqa: PLW1510, S603, S607, T201
# mypy: ignore
from __future__ import annotations

import subprocess
import sys

out = subprocess.run(["git", "fetch", "upstream", "--tags"])
if out.returncode != 0:
    print(out)
    sys.exit(1)
subprocess.run(["git", "reset", "--hard", "upstream/main"])

if subprocess.run(["git", "branch", "--show-current"], text=True, capture_output=True).stdout.strip() != "bump-version":
    msg = "`bump-version.py` should be run from `bump-version` branch"
    raise RuntimeError(msg)

# Delete local tags, if present
try:
    # Get the list of all tags
    result = subprocess.run(["git", "tag", "-l"], capture_output=True, text=True, check=True)
    tags = result.stdout.splitlines()  # Split the tags into a list by lines

    # Delete each tag using git tag -d
    subprocess.run(["git", "tag", "-d", *tags], check=True)
    print("All local tags have been deleted.")
except subprocess.CalledProcessError as e:
    print(f"An error occurred: {e}")

subprocess.run(["git", "fetch", "upstream", "--tags"])
subprocess.run(["git", "fetch", "upstream", "--prune", "--tags"])

how = sys.argv[1]
version = subprocess.run(["uv", "version", "--bump", how, "--short"], text=True, capture_output=True).stdout.strip()

subprocess.run(["git", "commit", "-a", "-m", f"release: Bump version to {version}"])
subprocess.run(["git", "tag", "-a", f"v{version}", "-m", f"v{version}"])
subprocess.run(["git", "push", "upstream", "HEAD", "--follow-tags"])
subprocess.run(["git", "push", "upstream", "HEAD:stable", "-f", "--follow-tags"])
