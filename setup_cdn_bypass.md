# Настройка Cloudflare CDN для обхода блокировок

## Почему мобильные операторы блокируют VPN:
1. **DPI (Deep Packet Inspection)** - анализ трафика
2. **Блокировка по IP** - известные VPN серверы
3. **Блокировка протоколов** - Reality, VLESS детектируются

## Решение: Cloudflare CDN
Cloudflare маскирует VPN трафик под обычный HTTPS, операторы не могут заблокировать Cloudflare.

## Что нужно:
1. **Домен** (можно бесплатный на Freenom, Cloudflare Registrar, или купить)
2. **Cloudflare аккаунт** (бесплатный)

## Шаги настройки:

### 1. Получить домен
- Зарегистрируйте домен на https://www.cloudflare.com/products/registrar/
- Или используйте существующий домен

### 2. Добавить домен в Cloudflare
1. Зайдите на https://dash.cloudflare.com
2. Add a Site → введите ваш домен
3. Выберите Free план
4. Cloudflare даст вам nameservers - обновите их у регистратора

### 3. Создать A-запись
1. В Cloudflare DNS → Add record
2. Type: A
3. Name: vpn (или любое имя)
4. IPv4 address: 89.44.76.190
5. Proxy status: **Proxied** (оранжевое облако) ✅
6. Save

### 4. Настроить SSL/TLS
1. SSL/TLS → Overview
2. Выберите: **Full** (не Full Strict)

### 5. Получить Origin Certificate
1. SSL/TLS → Origin Server → Create Certificate
2. Скопируйте Certificate и Private Key
3. Сохраните на сервере

### 6. Настроить Nginx на сервере
Нужен Nginx для терминации TLS и проксирования на xray.

## После настройки домена запустите:
```bash
python setup_cdn_config.py your-domain.com
```

## Результат:
- VPN будет работать через домен: vpn.your-domain.com
- Трафик идёт через Cloudflare CDN
- Мобильные операторы видят только HTTPS на Cloudflare IP
- **Невозможно заблокировать** без блокировки всего Cloudflare

## Альтернатива без домена:
Если нет домена, можно использовать:
1. **Cloudflare Workers** - бесплатный прокси
2. **Fragment/Split** - разбивка пакетов для обхода DPI
3. **Разные порты** - 8080, 8443, 2053, 2083, 2087, 2096

Скажите, есть ли у вас домен или хотите настроить без домена?
