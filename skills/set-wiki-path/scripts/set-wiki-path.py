#!/usr/bin/env python3
"""Write wiki_path to .wiki-path in the current directory."""

import sys
from pathlib import Path

if len(sys.argv) < 2 or not sys.argv[1].strip():
    print("Usage: set-wiki-path.py <path>")
    sys.exit(1)

new_path = str(Path(sys.argv[1].strip()).expanduser().resolve())
target = Path.cwd() / ".wiki-path"

target.write_text(new_path + "\n")

print(f"ok: wiki_path = {new_path}")
print(f"    written to {target}")
