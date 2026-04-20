# 🚀 Инструкция по развертыванию VPN бота на сервере

## Предварительные требования

- Сервер с Ubuntu/Debian
- Установленный 3x-ui панель
- Root доступ к серверу
- SSH доступ

## Шаг 1: Подключение к серверу

```bash
ssh root@89.44.76.190
```

## Шаг 2: Загрузка файлов на сервер

### Вариант A: Через Git (рекомендуется)

```bash
cd /opt
git clone <your-repo-url> vpn_bot
cd vpn_bot
```

### Вариант B: Через SCP с Windows

На вашем Windows компьютере выполните:

```powershell
# Из директории проекта
scp -r * root@89.44.76.190:/opt/vpn_bot/
```

## Шаг 3: Настройка .env файла

На сервере отредактируйте `.env`:

```bash
cd /opt/vpn_bot
nano .env
```

Убедитесь, что `VPN_MOCK_MODE=False`:

```env
BOT_TOKEN=8151059110:AAFsJ2tCzjA2mE_v3Y3NbK1ZSAHTCntCGXI
ADMIN_IDS=1658346274
DATABASE_URL=sqlite+aiosqlite:///data/bot.db

VPN_PANEL_URL=https://89.44.76.190:2053
VPN_PANEL_USERNAME=admin
VPN_PANEL_PASSWORD=admin

VPN_MOCK_MODE=False

TRIAL_DAYS=3
REFERRAL_BONUS_PERCENT=15

YOOKASSA_SHOP_ID=1331911
YOOKASSA_SECRET_KEY=live_xpdcw18Zx_TrPpIw0NIhSru4BznbFxZX3FKmN2CD3RU
```

## Шаг 4: Запуск скрипта развертывания

```bash
cd /opt/vpn_bot
chmod +x deploy.sh
./deploy.sh
```

Скрипт автоматически:
- Установит Python и зависимости
- Создаст виртуальное окружение
- Установит все пакеты
- Создаст systemd сервис
- Запустит бота

## Шаг 5: Проверка работы

```bash
# Проверить статус
systemctl status vpn-bot.service

# Посмотреть логи
journalctl -u vpn-bot.service -f
```

## Управление ботом

### Перезапуск
```bash
systemctl restart vpn-bot.service
```

### Остановка
```bash
systemctl stop vpn-bot.service
```

### Запуск
```bash
systemctl start vpn-bot.service
```

### Просмотр логов
```bash
# Последние логи
journalctl -u vpn-bot.service -n 100

# Следить за логами в реальном времени
journalctl -u vpn-bot.service -f
```

### Обновление бота

```bash
cd /opt/vpn_bot
git pull  # если используете git
systemctl restart vpn-bot.service
```

## Проверка доступа к базе данных 3x-ui

```bash
# Проверить существование файла
ls -la /etc/x-ui/x-ui.db

# Проверить права доступа
chmod 644 /etc/x-ui/x-ui.db
```

## Устранение неполадок

### Бот не запускается

```bash
# Проверить логи
journalctl -u vpn-bot.service -n 50

# Проверить права на файлы
ls -la /opt/vpn_bot

# Проверить виртуальное окружение
/opt/vpn_bot/venv/bin/python --version
```

### Ошибка доступа к базе данных

```bash
# Проверить права на x-ui базу
ls -la /etc/x-ui/x-ui.db

# Дать права на чтение
chmod 644 /etc/x-ui/x-ui.db
```

### VPN ключи не работают

1. Проверьте, что 3x-ui панель работает
2. Проверьте настройки inbound в 3x-ui
3. Убедитесь, что порт открыт в firewall

## Автозапуск при перезагрузке

Сервис уже настроен на автозапуск. После перезагрузки сервера бот запустится автоматически.

```bash
# Проверить статус автозапуска
systemctl is-enabled vpn-bot.service
```

## Безопасность

⚠️ **Важно:**
- Не публикуйте `.env` файл в публичных репозиториях
- Регулярно обновляйте зависимости
- Используйте firewall для защиты сервера
- Регулярно делайте бэкапы базы данных
