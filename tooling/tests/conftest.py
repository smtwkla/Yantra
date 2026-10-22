"""The tooling scripts (tooling/*.py) are imported by name, as release.py runs them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
