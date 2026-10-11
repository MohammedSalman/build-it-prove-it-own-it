"""Feature flags, read from a JSON file that operators edit.

The file's path comes from AFTERHOURS_FLAGS (ops/deploy.py sets it to flags/<env>.json).
It is re-read whenever it changes, so turning a flag on or off takes effect on the next
request, without a deploy or a restart. A missing file, a missing flag or a broken file
all mean "off": new behaviour must be switched on deliberately.
"""

import json
import os
from pathlib import Path

_cache: dict = {"key": None, "flags": {}}


def enabled(name: str) -> bool:
    path = os.environ.get("AFTERHOURS_FLAGS")
    if not path:
        return False
    try:
        stat = Path(path).stat()
        key = (path, stat.st_mtime_ns, stat.st_size)
        if _cache["key"] != key:
            _cache["flags"] = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            _cache["key"] = key
    except (OSError, ValueError):
        return False
    return _cache["flags"].get(name) is True
