# VPN Telegram Bot

Telegram-бот для автоматической продажи VPN-доступа через 3x-ui.

## Быстрый старт

### 1. Установка зависимостей на VPS

```bash
apt update && apt upgrade -y
apt install curl ufw git sqlite3 -y
```

### 2. Установка Docker

```bash
curl -fsSL https://get.docker.com | sh
```

### 3. Установка 3x-ui

```bash
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
```

После установки зайдите в веб-интерфейс `https://IP:2053` и создайте inbound:
- Protocol: **vless**
- Port: **443** (или 8443)
- Network: **tcp**
- Security: **none**

### 4. Настройка бота

```bash
git clone <repo> ~/vpn_telegram
cd ~/vpn_telegram
cp .env.example .env
nano .env  # заполните реальными данными
```

### 5. Запуск

```bash
docker compose build --no-cache
docker compose up -d
docker compose logs -f
```

## Переменные окружения

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `ADMIN_IDS` | Telegram ID администраторов через запятую |
| `VPN_PANEL_URL` | URL панели 3x-ui (https://IP:PORT) |
| `VPN_PANEL_USERNAME` | Логин панели |
| `VPN_PANEL_PASSWORD` | Пароль панели |
| `YOOKASSA_SHOP_ID` | ID магазина ЮKassa (опционально) |
| `YOOKASSA_SECRET_KEY` | Секретный ключ ЮKassa (опционально) |

## Структура проекта

```
vpn_telegram/
├── bot/
│   ├── main.py           # точка входа
│   ├── config.py         # настройки
│   ├── models.py         # модели БД
│   ├── handlers/         # обработчики команд
│   ├── keyboards/        # клавиатуры
│   ├── services/         # бизнес-логика
│   │   └── vpn_service.py  # прямая работа с БД 3x-ui
│   ├── middlewares/      # middleware
│   └── utils/            # утилиты
├── data/                 # SQLite база бота
├── Dockerfile
├── docker-compose.yml
└── .env
```

## Команды бота

- `/start` — главное меню
- `/admin` — панель администратора (только для ADMIN_IDS)

## Тарифы по умолчанию

| Тариф | Дней | Stars | Рублей |
|---|---|---|---|
| 1 день | 1 | 15 | 50 |
| 1 неделя | 7 | 75 | 250 |
| 1 месяц | 30 | 250 | 350 |
| 6 месяцев | 180 | 999 | 1500 |
| 1 год | 365 | 1800 | 2500 |

Тарифы можно изменить через админ-панель `/admin` → Тарифы.
