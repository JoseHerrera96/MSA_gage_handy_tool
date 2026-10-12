from __future__ import annotations

import subprocess
import sys
import importlib.util
from pathlib import Path


def main() -> None:
    app_spec = importlib.util.find_spec("app.main")
    if app_spec is None or app_spec.origin is None:
        raise ModuleNotFoundError("The packaged Streamlit app module could not be located.")

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", app_spec.origin],
        check=True,
    )


if __name__ == "__main__":
    main()
