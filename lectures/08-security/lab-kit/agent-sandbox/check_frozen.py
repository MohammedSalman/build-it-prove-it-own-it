"""Week 8 addition: check that Week 3's files in this folder are still byte-for-byte frozen.

    python check_frozen.py

Reads the SHA-256 table in FROZEN-COPY.md and compares it with the files on disk.
Windows line endings (CRLF) are read as LF first, so a checkout on Windows still matches.
"""

import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
table = re.findall(r"^([0-9a-f]{64})  (\S+)$", (HERE / "FROZEN-COPY.md").read_text(encoding="utf-8"), re.M)
changed = 0
for digest, name in table:
    path = HERE / name
    same = path.is_file() and hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == digest
    changed += not same
    print(("ok       " if same else "CHANGED  ") + name)
print(f"\n{len(table) - changed} of {len(table)} frozen files unchanged")
sys.exit(1 if changed else 0)
