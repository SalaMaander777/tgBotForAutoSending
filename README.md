# Telegram Bot + FastAPI Admin Panel

A Telegram bot with a web-based admin panel for managing subscribers and sending broadcasts to a channel.

## Features

- **Subscription tracking** — tracks when users subscribe/unsubscribe from a Telegram channel
- **Broadcast system** — send text or image messages to all subscribers with rate limiting
- **Admin panel** — web UI for managing users, broadcasts, and settings
- **Invite links** — auto-generates personal invite links for new users
- **Export** — download user list as CSV

## Stack

- [aiogram 3.17](https://docs.aiogram.dev/) — Telegram bot framework
- [FastAPI 0.115](https://fastapi.tiangolo.com/) — admin panel backend
- [SQLAlchemy 2 + asyncpg](https://docs.sqlalchemy.org/) — async PostgreSQL ORM
- [Alembic](https://alembic.sqlalchemy.org/) — database migrations
- [Jinja2](https://jinja.palletsprojects.com/) — HTML templates
- [Docker + Nginx](https://www.docker.com/) — containerized deployment

## Quick Start

### Requirements

- Docker & Docker Compose
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Bot must be **admin** in the target channel

### Development (polling mode)

```bash
cp .env.example .env
# Edit .env — fill in BOT_TOKEN, CHANNEL_ID, DATABASE_URL, ADMIN_PASSWORD_HASH
python scripts/create_admin.py  # generates ADMIN_PASSWORD_HASH
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Admin panel will be available at: http://localhost:8000/admin

### Production (webhook mode)

```bash
cp .env.example .env
# Edit .env — fill in all variables including WEBHOOK_BASE_URL
docker-compose up -d
```

### Run without Docker

```bash
pip install -e .
python -m uvicorn admin.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `BOT_MODE` | `webhook` (prod) or `polling` (dev) |
| `WEBHOOK_BASE_URL` | Public HTTPS URL for webhook (prod only) |
| `CHANNEL_ID` | Telegram channel ID (negative number, e.g. `-1001234567890`) |
| `DATABASE_URL` | PostgreSQL asyncpg URL (e.g. `postgresql+asyncpg://user:pass@host/db`) |
| `ADMIN_USERNAME` | Admin panel login |
| `ADMIN_PASSWORD_HASH` | bcrypt hash — generate with `python scripts/create_admin.py` |
| `SECRET_KEY` | Cookie signing secret (random 32+ character string) |

## Project Structure

```
├── bot/
│   ├── handlers/         # Telegram update handlers
│   ├── middlewares/      # DB session middleware
│   ├── keyboards/        # Inline keyboards
│   └── tasks/            # Background tasks (broadcast)
├── admin/
│   ├── routers/          # FastAPI route handlers
│   ├── templates/        # Jinja2 HTML templates
│   └── auth.py           # Session-based authentication
├── core/
│   ├── models/           # SQLAlchemy ORM models
│   ├── crud/             # Database operations
│   ├── config.py         # Settings via pydantic-settings
│   └── database.py       # Async engine + session factory
├── migrations/           # Alembic migrations
├── scripts/
│   └── create_admin.py   # Generate bcrypt password hash
├── static/css/           # Admin panel styles
└── docker/               # Dockerfile + nginx config
```

## Database Models

| Model | Description |
|-------|-------------|
| `users` | Telegram users who started the bot |
| `channel_events` | Subscribe/unsubscribe events per user |
| `settings` | Key-value config (welcome message, channel link) |
| `broadcasts` | Broadcast history with delivery stats |

## Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description"
```

## Architecture Notes

- **Single process**: bot (aiogram) + admin panel (FastAPI) run together in one uvicorn process
- **Broadcast rate limit**: 25 messages per batch, 1 second between batches (stays under Telegram's 30/s limit)
- **Image broadcasts**: image is uploaded once to get a `file_id`, then reused for all recipients
- **Auth**: cookie-based session using `itsdangerous.TimestampSigner` + bcrypt password verification

---

# Инструкция по развёртыванию

## Содержание

1. [Предварительная подготовка](#предварительная-подготовка)
2. [Получение токена бота](#получение-токена-бота)
3. [Развёртывание на Linux (сервер/VPS)](#развёртывание-на-linux-серверvps)
4. [Развёртывание на Windows (разработка)](#развёртывание-на-windows-разработка)
5. [Настройка переменных окружения](#настройка-переменных-окружения)
6. [Проверка работоспособности](#проверка-работоспособности)
7. [Управление и обслуживание](#управление-и-обслуживание)
8. [Решение частых проблем](#решение-частых-проблем)

---

## Предварительная подготовка

### Требования

| Компонент | Минимальная версия |
|-----------|-------------------|
| Docker | 24.0+ |
| Docker Compose | 2.20+ (плагин `docker compose`) |
| Python | 3.11+ (только для `scripts/create_admin.py`) |

### Что нужно иметь заранее

- **Токен Telegram-бота** — получить у [@BotFather](https://t.me/BotFather)
- **ID Telegram-канала** — отрицательное число, например `-1001234567890`
- **Бот должен быть администратором канала** — без этого не будут работать приглашения и отслеживание подписок
- **Публичный домен с HTTPS** — только для продакшен-режима (webhook)

---

## Получение токена бота

1. Откройте Telegram, найдите [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot` и следуйте инструкциям
3. Сохраните полученный токен вида `1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi`

### Получение ID канала

1. Добавьте бота в канал как администратора
2. Отправьте любое сообщение в канал
3. Откройте в браузере: `https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates`
4. В ответе найдите поле `"chat": {"id": -1001234567890}` — это и есть `CHANNEL_ID`

---

## Развёртывание на Linux (сервер/VPS)

### Установка Docker

```bash
# Ubuntu / Debian
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавить текущего пользователя в группу docker (чтобы не писать sudo)
sudo usermod -aG docker $USER
newgrp docker

# Проверить установку
docker --version
docker compose version
```

### Клонирование проекта

```bash
git clone <URL_РЕПОЗИТОРИЯ> tg_bot
cd tg_bot
```

### Настройка переменных окружения

```bash
cp .env.example .env
nano .env  # или vim .env
```

Заполните файл `.env` (подробнее — в разделе [Настройка переменных окружения](#настройка-переменных-окружения)).

### Генерация хэша пароля администратора

```bash
pip install bcrypt
python scripts/create_admin.py
```

Скрипт попросит ввести пароль и выдаст строку вида `ADMIN_PASSWORD_HASH=$2b$12$...` — скопируйте её в `.env`.

### Режим разработки (polling, без домена)

Подходит для тестирования без публичного домена:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Админ-панель доступна по адресу: **http://localhost:8000/admin**

Запуск в фоне:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

### Продакшен-режим (webhook, с доменом и HTTPS)

#### Шаг 1. Подготовьте SSL-сертификат

Вариант А — Let's Encrypt (бесплатно):
```bash
sudo apt-get install -y certbot
sudo certbot certonly --standalone -d ВАШ_ДОМЕН

mkdir -p docker/ssl
sudo cp /etc/letsencrypt/live/ВАШ_ДОМЕН/fullchain.pem docker/ssl/
sudo cp /etc/letsencrypt/live/ВАШ_ДОМЕН/privkey.pem docker/ssl/
sudo chmod 644 docker/ssl/*.pem
```

Вариант Б — самоподписанный (только для тестов):
```bash
mkdir -p docker/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/ssl/privkey.pem \
  -out docker/ssl/fullchain.pem \
  -subj "/CN=ВАШ_ДОМЕН"
```

#### Шаг 2. Укажите домен в nginx.conf

```bash
sed -i 's/YOUR_DOMAIN/ВАШ_ДОМЕН/g' docker/nginx.conf
```

#### Шаг 3. Установите переменные окружения

В файле `.env`:
```env
BOT_MODE=webhook
WEBHOOK_BASE_URL=https://ВАШ_ДОМЕН
```

#### Шаг 4. Запуск

```bash
docker compose up --build -d
```

#### Шаг 5. Проверка

```bash
docker compose ps           # все контейнеры должны быть Up
docker compose logs app     # логи приложения
curl https://ВАШ_ДОМЕН/admin/
```

---

## Развёртывание на Windows (разработка)

На Windows рекомендуется использовать **режим разработки (polling)** — он не требует домена и HTTPS.

### Установка Docker Desktop

1. Скачайте [Docker Desktop для Windows](https://www.docker.com/products/docker-desktop/)
2. Запустите установщик, следуйте инструкциям
3. При первом запуске Docker Desktop может попросить включить WSL 2 — согласитесь и перезагрузите компьютер
4. После установки убедитесь, что Docker Desktop запущен (иконка в трее)

Проверка в PowerShell или Git Bash:
```bash
docker --version
docker compose version
```

### Клонирование проекта

```bash
git clone <URL_РЕПОЗИТОРИЯ> tg_bot
cd tg_bot
```

### Настройка переменных окружения

```bash
# Git Bash / WSL
cp .env.example .env

# PowerShell
copy .env.example .env
```

Откройте `.env` в любом редакторе (Notepad++, VS Code) и заполните.

### Генерация хэша пароля

```bash
pip install bcrypt
python scripts/create_admin.py
```

Если Python не установлен — используйте онлайн-генератор bcrypt и вставьте результат в `ADMIN_PASSWORD_HASH` в `.env`.

### Запуск в режиме разработки

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Дождитесь строки `INFO: Application startup complete.` и откройте: **http://localhost:8000/admin**

### Остановка

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

---

## Настройка переменных окружения

```env
# === БОТ ===
BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi
BOT_MODE=polling            # polling — разработка, webhook — продакшен

# === WEBHOOK (только если BOT_MODE=webhook) ===
WEBHOOK_BASE_URL=https://ВАШ_ДОМЕН
WEBHOOK_PATH=/webhook/bot
WEBHOOK_SECRET=случайная_строка_32_символа

# === КАНАЛ ===
CHANNEL_ID=-1001234567890

# === БАЗА ДАННЫХ ===
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/tgbot
POSTGRES_PASSWORD=пароль_для_postgres

# === АДМИН-ПАНЕЛЬ ===
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$...хэш_из_скрипта...
SECRET_KEY=случайная_строка_минимум_32_символа

# === ПРИЛОЖЕНИЕ ===
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false
```

### Генерация случайных строк для SECRET_KEY и WEBHOOK_SECRET

Linux / Git Bash:
```bash
openssl rand -hex 32
```

PowerShell:
```powershell
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
```

---

## Проверка работоспособности

```bash
# Статус контейнеров (migrate с Exited (0) — норма)
docker compose ps

# Логи
docker compose logs -f app
docker compose logs -f postgres
docker compose logs -f nginx   # только в продакшене
```

**Тест бота:** найдите бота в Telegram, отправьте `/start` — должен ответить и выдать ссылку на канал.

**Тест панели:** откройте `http://localhost:8000/admin` (dev) или `https://ВАШ_ДОМЕН/admin` (prod), войдите с данными из `.env`.

---

## Управление и обслуживание

### Перезапуск после изменений

```bash
# Разработка
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Продакшен
docker compose up --build -d
```

### Миграции базы данных

```bash
docker compose exec app bash
alembic revision --autogenerate -m "описание"
alembic upgrade head
exit
```

### Бэкап базы данных

```bash
# Создать дамп
docker compose exec postgres pg_dump -U postgres tgbot > backup_$(date +%Y%m%d).sql

# Восстановить
docker compose exec -T postgres psql -U postgres tgbot < backup_20240101.sql
```

### Обновление SSL-сертификата (Linux, Let's Encrypt)

```bash
sudo certbot renew
sudo cp /etc/letsencrypt/live/ВАШ_ДОМЕН/fullchain.pem docker/ssl/
sudo cp /etc/letsencrypt/live/ВАШ_ДОМЕН/privkey.pem docker/ssl/
sudo chmod 644 docker/ssl/*.pem
docker compose restart nginx
```

---

## Решение частых проблем

### Бот не отвечает

```bash
docker compose logs app
docker compose exec app env | grep BOT_TOKEN
```

### Ошибка подключения к базе данных

```bash
docker compose ps postgres
docker compose logs postgres
```

Убедитесь, что в `DATABASE_URL` хост указан как `postgres` (имя сервиса Docker), а не `localhost`.

### Не работает webhook (продакшен)

1. Откройте порты: `sudo ufw allow 80 && sudo ufw allow 443`
2. Убедитесь, что SSL-сертификаты лежат в `docker/ssl/`
3. Проверьте, что `YOUR_DOMAIN` в `docker/nginx.conf` заменён на реальный домен
4. Проверьте логи: `docker compose logs nginx`

### Контейнер падает при запуске

```bash
docker compose logs app --tail=50
docker compose build --no-cache
```

### Ошибка "password authentication failed" для PostgreSQL

```bash
# ВНИМАНИЕ: удалит все данные в БД!
docker compose down -v
docker compose up --build
```

### Windows: "docker daemon is not running"

Запустите **Docker Desktop** через меню Пуск и дождитесь, пока иконка в трее перестанет анимироваться.

### Windows: WSL 2 не установлен

```powershell
# PowerShell от имени администратора
wsl --install
# Перезагрузить компьютер
```
