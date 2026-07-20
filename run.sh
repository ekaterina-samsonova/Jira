#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Устанавливаю зависимости (первый запуск может занять минуту)..."
python3 -m pip install -r requirements.txt -q

echo ""
echo "=========================================="
echo "  Сервер запущен!"
echo "  Откройте в браузере:"
echo ""
echo "  http://localhost:8000"
echo ""
echo "  Чтобы остановить сервер: Ctrl + C"
echo "=========================================="
echo ""

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
