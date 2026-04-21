# Руководство по устранению проблем

## 🚨 Сервер недоступен по SSH

### Возможные причины:
1. Проблема с интернет-соединением
2. Сервер перезагружается
3. Firewall заблокировал доступ
4. Сервер завис после изменений

### Шаги диагностики:

#### 1. Проверьте доступность сервера
```bash
ping 89.44.76.190
```

Если пинг не проходит - проблема с сетью или сервер выключен.

#### 2. Проверьте SSH порт
```bash
telnet 89.44.76.190 22
# или
nc -zv 89.44.76.190 22
```

#### 3. Попробуйте подключиться через VNC/Console
Если у вас есть доступ к панели управления хостинга, подключитесь через VNC или Web Console.

---

## 🔧 VPN не работает после миграции на Reality

### Быстрая диагностика (если SSH доступен):

#### 1. Проверьте статус сервисов
```bash
ssh root@89.44.76.190 'systemctl status x-ui vpn-bot'
```

#### 2. Проверьте логи x-ui
```bash
ssh root@89.44.76.190 'journalctl -u x-ui -n 50 --no-pager'
```

#### 3. Проверьте логи Xray
```bash
ssh root@89.44.76.190 'journalctl -u x-ui -n 100 --no-pager | grep -i error'
```

#### 4. Проверьте конфигурацию Reality
```bash
ssh root@89.44.76.190 'cat /usr/local/x-ui/bin/config.json | grep -A 10 realitySettings'
```

---

## 🔄 Восстановление из резервной копии

Если Reality не работает, восстановите старую конфигурацию:

### Вариант 1: Автоматическое восстановление
```bash
ssh root@89.44.76.190 '/root/restore_from_reality.sh'
```

### Вариант 2: Ручное восстановление
```bash
ssh root@89.44.76.190

# Остановить сервисы
systemctl stop x-ui vpn-bot

# Восстановить конфигурацию x-ui
cp /root/backup_before_reality_20260420_214857/config.json /usr/local/x-ui/bin/config.json

# Восстановить бота
rm -rf /opt/vpn_bot
cp -r /root/backup_before_reality_20260420_214857/vpn_bot /opt/vpn_bot

# Запустить сервисы
systemctl start x-ui vpn-bot

# Проверить статус
systemctl status x-ui vpn-bot
```

---

## 🧪 Тестирование VPN ключа

### 1. Получите тестовый ключ
Откройте бота @djan_vpn_bot и создайте пробный ключ.

### 2. Проверьте формат ключа
Reality ключ должен выглядеть так:
```
vless://UUID@89.44.76.190:443?type=tcp&security=reality&pbk=...&fp=chrome&sni=www.google.com&sid=...&flow=xtls-rprx-vision#...
```

Старый ключ (без Reality):
```
vless://UUID@89.44.76.190:443?type=tcp&security=none&encryption=none#...
```

### 3. Используйте правильный клиент
Reality поддерживают:
- ✅ **Karing** (рекомендуется)
- ✅ **Throne**
- ✅ v2rayNG (Android)
- ✅ Streisand (iOS)

Не поддерживают Reality:
- ❌ Старые версии клиентов
- ❌ Некоторые веб-клиенты

---

## 🔍 Проверка портов и firewall

### Проверьте, что порт 443 открыт
```bash
ssh root@89.44.76.190 'netstat -tulpn | grep :443'
```

Должно быть:
```
tcp6       0      0 :::443                  :::*                    LISTEN      PID/xray-linux-amd64
```

### Проверьте firewall
```bash
ssh root@89.44.76.190 'iptables -L -n | grep 443'
```

---

## 📊 Проверка клиентов в базе данных

### Посмотрите список клиентов
```bash
ssh root@89.44.76.190 'sqlite3 /etc/x-ui/x-ui.db "SELECT id, email, flow FROM (SELECT json_extract(value, '\''$.id'\'') as id, json_extract(value, '\''$.email'\'') as email, json_extract(value, '\''$.flow'\'') as flow FROM inbounds, json_each(json_extract(settings, '\''$.clients'\'')) WHERE protocol='\''vless'\'');"'
```

Все клиенты должны иметь `flow=xtls-rprx-vision` после миграции.

---

## 🌐 Проверка веб-панели x-ui

Откройте в браузере:
```
https://89.44.76.190:2053
```

Логин: `admin`  
Пароль: `admin`

Проверьте:
1. Inbound на порту 443 активен
2. Протокол: VLESS
3. Security: Reality
4. Количество клиентов: 13

---

## 🔧 Если Reality не работает - откат на старую конфигурацию

### Быстрый откат (TCP без Reality)
```bash
ssh root@89.44.76.190 << 'EOF'
# Обновить stream_settings на старую конфигурацию
sqlite3 /etc/x-ui/x-ui.db << 'SQL'
UPDATE inbounds SET stream_settings = '{
  "network": "tcp",
  "security": "none",
  "tcpSettings": {
    "acceptProxyProtocol": false,
    "header": {"type": "none"}
  },
  "sockopt": {
    "tcpFastOpen": true,
    "tcpNoDelay": true,
    "tcpCongestion": "bbr",
    "mark": 255
  }
}' WHERE protocol='vless';
SQL

# Перезапустить x-ui
systemctl restart x-ui
sleep 3
systemctl status x-ui
EOF
```

### Обновить бота для генерации старых ключей
```bash
ssh root@89.44.76.190 << 'EOF'
# Временно изменить формат ключей в боте
sed -i 's/security=reality/security=none/g' /opt/vpn_bot/bot/services/vpn_service.py
sed -i 's/&pbk=.*&fp=chrome&sni=www.google.com&sid=.*&spx=%2F&flow=xtls-rprx-vision//g' /opt/vpn_bot/bot/services/vpn_service.py

# Перезапустить бота
systemctl restart vpn-bot
EOF
```

---

## 📞 Контакты для поддержки

Если ничего не помогло:
1. Проверьте панель управления хостингом
2. Перезагрузите сервер через панель
3. Проверьте логи в панели управления
4. Свяжитесь с поддержкой хостинга

---

## 📝 Полезные команды

### Перезапуск всех сервисов
```bash
ssh root@89.44.76.190 'systemctl restart x-ui vpn-bot && sleep 3 && systemctl status x-ui vpn-bot'
```

### Просмотр всех логов
```bash
ssh root@89.44.76.190 'journalctl -u x-ui -u vpn-bot -n 100 --no-pager'
```

### Проверка дискового пространства
```bash
ssh root@89.44.76.190 'df -h'
```

### Проверка памяти
```bash
ssh root@89.44.76.190 'free -h'
```

### Проверка процессов
```bash
ssh root@89.44.76.190 'ps aux | grep -E "(xray|x-ui|python)"'
```
