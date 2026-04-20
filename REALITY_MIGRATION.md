# VLESS-Reality Migration

## Дата миграции
20 апреля 2026, 21:48 UTC

## Что изменилось

### До миграции
- **Протокол**: VLESS
- **Транспорт**: TCP (plain)
- **Шифрование**: none
- **Порт**: 443
- **Статус**: Устаревшая конфигурация, уязвимая для DPI

### После миграции
- **Протокол**: VLESS
- **Транспорт**: TCP
- **Шифрование**: Reality
- **Flow**: xtls-rprx-vision
- **SNI маскировка**: www.google.com, google.com
- **Порт**: 443
- **Статус**: Современная конфигурация, рекомендованная для России

## Reality ключи

```
Private Key: MPnNzbMLF812adXAeJXYv3nY3M6gDWZJsc2kIlLAZnE
Public Key:  c4d33NKVpulPMhdJOcq-e12fjJjRZMU5V_wTTIm5K2c
```

## Преимущества Reality

1. **Маскировка трафика**: VPN-трафик маскируется под обычные HTTPS-запросы к Google
2. **Защита от DPI**: Роскомнадзор не может определить использование VPN
3. **Улучшенная стабильность**: Особенно на мобильных сетях в России
4. **Vision flow**: Дополнительная оптимизация для снижения задержек

## Формат ключей

Новые ключи генерируются в формате:

```
vless://UUID@SERVER:443?type=tcp&security=reality&pbk=PUBLIC_KEY&fp=chrome&sni=www.google.com&sid=0123456789abcdef&spx=%2F&flow=xtls-rprx-vision#DISPLAY_NAME
```

Параметры:
- `security=reality` - включено Reality шифрование
- `pbk=...` - публичный ключ Reality
- `fp=chrome` - отпечаток браузера Chrome
- `sni=www.google.com` - маскировка под Google
- `flow=xtls-rprx-vision` - оптимизированный поток данных

## Резервная копия

Создана полная резервная копия перед миграцией:
```
/root/backup_before_reality_20260420_214857/
├── config.json (старая конфигурация x-ui)
└── vpn_bot/ (старая версия бота)
```

## Восстановление

Если что-то пошло не так, выполните:

```bash
ssh root@89.44.76.190
/root/restore_from_reality.sh
```

Скрипт автоматически:
1. Остановит сервисы
2. Восстановит старую конфигурацию x-ui
3. Восстановит старую версию бота
4. Запустит сервисы

## Проверка работоспособности

### Проверка сервисов
```bash
systemctl status x-ui
systemctl status vpn-bot
```

### Проверка конфигурации
```bash
cat /usr/local/x-ui/bin/config.json | grep -A 5 "realitySettings"
```

### Проверка клиентов
```bash
sqlite3 /etc/x-ui/x-ui.db "SELECT email, flow FROM (SELECT json_extract(value, '$.email') as email, json_extract(value, '$.flow') as flow FROM inbounds, json_each(json_extract(settings, '$.clients')) WHERE protocol='vless');"
```

Все клиенты должны иметь `flow=xtls-rprx-vision`

## Тестирование

1. Откройте бота в Telegram: @djan_vpn_bot
2. Нажмите "Пробный период"
3. Получите новый ключ
4. Импортируйте ключ в клиент (v2rayNG, Karing, Streisand)
5. Проверьте подключение

## Рекомендуемые клиенты

Согласно vpn-configs-for-russia:

### Лучшие (с защитой от localhost SOCKS5):
- **Karing** ✅ (Android, iOS, Windows, macOS)
- **Throne** ✅ (Windows, Linux, macOS)

### Не рекомендуется:
- v2rayN ❌ (нет защиты от localhost exploit)
- Happ ❌ (нестабильная работа)

## Источники

Миграция основана на рекомендациях из:
- https://github.com/igareck/vpn-configs-for-russia
- Статья на Habr о критической уязвимости мобильных клиентов
- Официальная документация Xray-core

## Дополнительные улучшения

Применены оптимизации из предыдущих миграций:
- BBR congestion control
- TCP Fast Open
- Оптимизированные keepalive (100s/10s)
- MSS clamping через iptables
- Увеличенные TCP буферы
- tcp_mtu_probing=1

## Контакты

Если возникли проблемы:
1. Проверьте логи: `journalctl -u x-ui -n 50` и `journalctl -u vpn-bot -n 50`
2. Попробуйте восстановить из бэкапа
3. Проверьте, что клиент поддерживает Reality (Karing, Throne)
