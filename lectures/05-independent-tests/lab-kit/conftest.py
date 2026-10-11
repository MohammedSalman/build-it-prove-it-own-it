import os
import tempfile

# app.main builds a module-level app on import; keep it away from the real database.
# (This file sits at the top of the kit so that tests/ and properties/ both get it.)
os.environ.setdefault("AFTERHOURS_DB", os.path.join(tempfile.mkdtemp(), "import.db"))
