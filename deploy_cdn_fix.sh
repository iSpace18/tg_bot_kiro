#!/bin/bash
# Автоматический деплой CDN обхода

set -e

echo "=========================================="
echo "🚀 Деплой CDN обхода VPN"
echo "=========================================="

# 1. Скопировать обновленный файл в контейнер
echo "📦 Копирование обновленного vpn_service.py..."
docker cp bot/services/vpn_service.py vpn_telegram_bot:/opt/vpn_bot/bot/services/vpn_service.py

# 2. Перезапустить бот
echo "🔄 Перезапуск бота..."
docker restart vpn_telegram_bot

# Подождать пока бот запустится
echo "⏳ Ожидание запуска бота (10 секунд)..."
sleep 10

# 3. Сбросить пробный период
echo "🧹 Сброс пробного периода..."
docker exec vpn_telegram_bot python /opt/vpn_bot/cleanup_and_reset_trial.py

echo ""
echo "=========================================="
echo "✅ ДЕПЛОЙ ЗАВЕРШЕН!"
echo "=========================================="
echo ""
echo "📱 Теперь запросите пробный период через бота"
echo "   Новый ключ будет с CDN обходом через djanvpn.ru"
echo ""
