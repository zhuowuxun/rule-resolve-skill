#!/usr/bin/env python3
from pathlib import Path
import runpy
import sys

SKILL_DIR = Path(__file__).resolve().parents[1]
BUNDLED_SCRIPT = SKILL_DIR / "scripts" / "standardize_validation_main_excel.py"

if __name__ == '__main__':
    if not BUNDLED_SCRIPT.exists():
        raise SystemExit(f'Missing bundled validation standardization script: {BUNDLED_SCRIPT}')
    sys.argv[0] = str(BUNDLED_SCRIPT)
    runpy.run_path(str(BUNDLED_SCRIPT), run_name='__main__')
