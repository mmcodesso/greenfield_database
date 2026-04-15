from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from generator_dataset.main import main


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/settings.yaml"
    validation_scope = sys.argv[2] if len(sys.argv) > 2 else "full"
    main(config_path, validation_scope)
