"""Локальный запуск приложения 'uroki' для тренировок.

Запускать ПОСЛЕ setup_local_lab.sh:
    python3 uroki_local_run.py            # LAB=/tmp/uroki_test по умолчанию
    LAB=/tmp/mylab python3 uroki_local_run.py

Приложение поднимется на http://127.0.0.1:5099
"""
import os
import sys

LAB = os.environ.get("LAB", "/tmp/uroki_test")
sys.path.insert(0, LAB)

from app.web import app  # noqa: E402

if __name__ == "__main__":
    print(f"[*] serving lab from {LAB} on http://127.0.0.1:5099")
    app.run(host="127.0.0.1", port=5099, threaded=True)
