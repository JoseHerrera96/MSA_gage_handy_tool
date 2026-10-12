from __future__ import annotations

import sys
from pathlib import Path

source_directory = Path(__file__).resolve().parent / "src"
if str(source_directory) not in sys.path:
    sys.path.insert(0, str(source_directory))

from app import main

if __name__ == "__main__":
    main()
