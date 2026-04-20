# 🚀 Быстрое развертывание (ручной способ)

## Шаг 1: Подключитесь к серверу

```bash
ssh root@89.44.76.190
```

## Шаг 2: Установите необходимые пакеты

```bash
apt-get update
apt-get install -y python3 python3-pip python3-venv unzip
```

## Шаг 3: Распакуйте файлы

```bash
cd /opt/vpn_bot
unzip -o vpn_bot.zip
ls -la
```

## Шаг 4: Создайте виртуальное окружение и установите зависимости

```bash
cd /opt/vpn_bot
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Шаг 5: Проверьте настройки .env

```bash
cat .env
```

Убедитесь что `VPN_MOCK_MODE=False`

## Шаг 6: Создайте systemd сервис

```bash
cat > /etc/systemd/system/vpn-bot.service << 'EOF'
[Unit]
Description=VPN Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vpn_bot
Environment="PYTHONPATH=/opt/vpn_bot"
ExecStart=/opt/vpn_bot/venv/bin/python bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

## Шаг 7: Запустите сервис

```bash
systemctl daemon-reload
systemctl enable vpn-bot.service
systemctl start vpn-bot.service
```

## Шаг 8: Проверьте статус

```bash
systemctl status vpn-bot.service
```

## Шаг 9: Посмотрите логи

```bash
journalctl -u vpn-bot.service -f
```

Нажмите Ctrl+C чтобы выйти из просмотра логов.

---

## Альтернатива: Запуск без systemd (для тестирования)

```bash
cd /opt/vpn_bot
source venv/bin/activate
export PYTHONPATH=/opt/vpn_bot
python bot/main.py
```

Нажмите Ctrl+C чтобы остановить бота.

---

## Полезные команды

### Перезапуск бота
```bash
systemctl restart vpn-bot.service
```

### Остановка бота
```bash
systemctl stop vpn-bot.service
```

### Просмотр логов
```bash
journalctl -u vpn-bot.service -n 100 --no-pager
```

### Проверка доступа к базе x-ui
```bash
ls -la /etc/x-ui/x-ui.db
sqlite3 /etc/x-ui/x-ui.db "SELECT id, protocol FROM inbounds LIMIT 5;"
```
