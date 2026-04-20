# VPN Telegram Bot

Telegram бот для автоматической продажи VPN доступа с интеграцией 3x-ui панели.

## Возможности

- 🎁 Пробный период для новых пользователей
- 💳 Оплата через Telegram Stars и ЮKassa
- 🔑 Автоматическое создание VPN ключей через прямой доступ к БД 3x-ui
- 👥 Реферальная система с бонусами
- 📊 Профиль пользователя с историей покупок
- 🛠 Админ панель для управления
- ❓ FAQ раздел

## Требования

- Ubuntu/Debian сервер
- Python 3.8+
- Установленная 3x-ui панель
- Telegram Bot Token от @BotFather

## Быстрая установка на сервере

### 1. Клонируйте репозиторий

```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/vpn-telegram-bot.git vpn_bot
cd vpn_bot
```

### 2. Создайте .env файл

```bash
nano .env
```

Заполните необходимые данные:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=your_telegram_id
DATABASE_URL=sqlite+aiosqlite:///data/bot.db

VPN_PANEL_URL=https://your-server-ip:2053
VPN_PANEL_USERNAME=admin
VPN_PANEL_PASSWORD=admin

# Для продакшена ОБЯЗАТЕЛЬНО False
VPN_MOCK_MODE=False

TRIAL_DAYS=3
REFERRAL_BONUS_PERCENT=15

YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
```

### 3. Запустите установку

```bash
chmod +x install_on_server.sh
./install_on_server.sh
```

Скрипт автоматически:
- Установит все зависимости
- Создаст виртуальное окружение
- Установит Python пакеты
- Создаст systemd сервис для автозапуска
- Запустит бота

### 4. Проверьте статус

```bash
systemctl status vpn-bot.service
journalctl -u vpn-bot.service -f
```

## Управление ботом

```bash
# Перезапуск
systemctl restart vpn-bot.service

# Остановка
systemctl stop vpn-bot.service

# Запуск
systemctl start vpn-bot.service

# Просмотр логов в реальном времени
journalctl -u vpn-bot.service -f

# Обновление с GitHub
cd /opt/vpn_bot
git pull
systemctl restart vpn-bot.service
```

## Тарифы по умолчанию

| Тариф | Дней | Stars | Рублей |
|---|---|---|---|
| 1 день | 1 | 15 | 50 |
| 1 неделя | 7 | 75 | 250 |
| 1 месяц | 30 | 250 | 350 |
| 6 месяцев | 180 | 999 | 1500 |
| 1 год | 365 | 1800 | 2500 |

Тарифы можно изменить через админ-панель `/admin` → Тарифы.

## Структура проекта

```
vpn_bot/
├── bot/
│   ├── handlers/       # Обработчики команд
│   ├── keyboards/      # Клавиатуры
│   ├── middlewares/    # Middleware
│   ├── services/       # Бизнес-логика (VPN, платежи, рефералы)
│   ├── utils/          # Утилиты (БД, логирование)
│   ├── config.py       # Конфигурация
│   ├── models.py       # Модели БД
│   └── main.py         # Точка входа
├── data/               # База данных SQLite
├── requirements.txt    # Python зависимости
├── install_on_server.sh # Скрипт установки
└── .env               # Конфигурация (не в git)
```

## Разработка и тестирование

### Локальное тестирование (Windows/Mac)

Для тестирования без реального VPN сервера установите в `.env`:

```env
VPN_MOCK_MODE=True
```

Это создаст тестовые VPN ключи без подключения к 3x-ui.

### Установка зависимостей

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### Запуск локально

```bash
export PYTHONPATH=.  # Linux/Mac
# или
$env:PYTHONPATH="."  # Windows PowerShell

python bot/main.py
```

## Настройка 3x-ui

Убедитесь, что в 3x-ui создан inbound с протоколом VLESS:

1. Зайдите в панель 3x-ui: `https://your-server-ip:2053`
2. Создайте inbound:
   - Protocol: **vless**
   - Port: **443** (или другой)
   - Network: **tcp**
   - Security: **none** или **reality**

Бот автоматически найдет первый VLESS inbound и будет добавлять туда клиентов.

## Команды бота

- `/start` — главное меню
- `/admin` — панель администратора (только для ADMIN_IDS)

## Устранение неполадок

### Бот не создает VPN ключи

Проверьте доступ к базе данных 3x-ui:

```bash
ls -la /etc/x-ui/x-ui.db
chmod 644 /etc/x-ui/x-ui.db
```

### Просмотр подробных логов

```bash
journalctl -u vpn-bot.service -n 100 --no-pager
```

### Проверка inbound в 3x-ui

```bash
sqlite3 /etc/x-ui/x-ui.db "SELECT id, protocol, port FROM inbounds;"
```

## Лицензия

MIT

## Поддержка

Если возникли вопросы, создайте Issue в репозитории.
