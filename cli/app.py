from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_FILE = PROJECT_ROOT / "src" / "app.py"


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(APP_FILE)],
        check=True,
    )


if __name__ == "__main__":
    main()
