"""Copy synthetic test apps beside, but not over, the installed distribution."""

import shutil
import sys
from pathlib import Path

source = Path(__file__).resolve().parent.parent
destination = Path(sys.argv[1])
shutil.copyfile(source / "pyproject.toml", destination / "pyproject.toml")
for name in ("tests", "testapp"):
    target = destination / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source / name, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "media"))
