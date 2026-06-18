#!/usr/bin/env python3
from pathlib import Path
import runpy
import sys

SKILL_DIR = Path(__file__).resolve().parents[1]
BUNDLED_SCRIPT = SKILL_DIR / "scripts" / "standardize_validation_main_excel.py"
LOCAL_PROJECT_SCRIPT = Path('/Users/carmenz/Documents/tag管理系统/规则名称标准化/scripts/standardize_validation_main_excel.py')

if __name__ == '__main__':
    SCRIPT = BUNDLED_SCRIPT if BUNDLED_SCRIPT.exists() else LOCAL_PROJECT_SCRIPT
    if not SCRIPT.exists():
        raise SystemExit(f'Missing validation standardization script: {SCRIPT}')
    sys.argv[0] = str(SCRIPT)
    runpy.run_path(str(SCRIPT), run_name='__main__')
