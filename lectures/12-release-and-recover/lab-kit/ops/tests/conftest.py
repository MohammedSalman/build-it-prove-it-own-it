import sys
from pathlib import Path

# The ops tools import each other by name (they run as "python ops/deploy.py").
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
