# Kita — Multi-tenant Telegram-сервис создания ботов-предложек

## 📖 О проекте

**Kita** — multi-tenant Telegram-сервис, который позволяет пользователям моментально разворачивать собственную предложку для канала.


### ✨ Основные возможности
- **Мастер-бот:** регистрация пользовательских ботов предложек.
- **Управление юзерботом**: включение/выключение, смена токена, смена канала, авто-деактивация при потере прав.
- **Предложка:** принимает фото, видео, медиагруппы (альбомы), обычный текст и репосты с каналов.
- **Модерация:** назначение администраторов, блокировка пользователей, отправка сообщений пользователям.
- **Рассылка (broadcast):** отправка фото, видео, медиагрупп (альбомов), текста и репостов.
- **Локализация (i18n):** поддержка `ru` / `en`, редактирование переводов через `.po` файлы.


## ⚙️ Технологический стек

| Layer                    | Technology                                              |
| ------------------------ | ------------------------------------------------------- |
| Bot framework            | aiogram 3, aiogram-dialog                               |
| API / Webhooks           | FastAPI, Uvicorn                                        |
| Dependency Injection     | Dishka                                                  |
| Database                 | PostgreSQL 17, SQLAlchemy 2.0 (async), asyncpg, Alembic |
| Task Queue               | Taskiq, Redis Streams                                   |
| Cache / FSM / Rate Limit | Redis, orjson, token-bucket (Lua)                       |
| Token Encryption         | cryptography (Fernet)                                   |
| Infra                    | Docker Compose, Docker Secrets, Caddy                   |
| Package Manager          | uv                                                      |


## 🚀 Быстрый старт (Docker)

> [!WARNING]
> На проде три секрета (`TG_TOKEN`, `WEBHOOK_SECRET`, `ENCRYPTION_KEY`) должны находится **только** в `secrets/`, ни в коем случае не указывайте их в `.env`.


### Предварительные требования
- Наличие зарегистрированого домена
- A DNS запись указывающая на IP вашего сервера
- Установленный на сервере [Docker Engine](https://docs.docker.com/engine/install/)
- Открытые порты: 80 (ACME challenge) и WEBHOOK_PORT (по умолчанию 8443)

### Установка и запуск
1. **Склонируйте репозиторий**
```sh
git clone https://github.com/tellmeimcute/kita.git && cd kita
```

2. **Создайте .env файл в корне на основе шаблона .env.example**
```sh
cp .env.example .env
```

Сгенерируйте пароль БД и отредактируйте остальные переменные:
```sh
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 32)/" .env
nano .env
```

Обязательно заполните следующие переменные:
| Переменная       | Описание               | Пример        |
| ---------------- | ---------------------- | ------------- |
| `WEBHOOK_DOMAIN` | Домен                  | `example.com` |
| `WEBHOOK_PORT`   | Порт вебхука 8443, 443 | `8443`        |

3. **Создайте папку secrets**
```sh
mkdir -p secrets
```

4. **Создайте файл с токеном мастер бота**
```sh
echo YOUR_TOKEN > secrets/.tg_token
```

5. **Сгенерируйте ключ шифрования и secret_token для телеграм вебхука**
```sh
openssl rand -base64 32 > secrets/.encryption_key && openssl rand -hex 32 > secrets/.webhook_secret
```

6. **Создайте docker network и запустите**
```sh
docker network create kita-proxy
docker compose up -d
```

7. **Запуск Caddy реверс прокси**
> [!NOTE]
> Можно использовать любой реверс прокси. Главное чтобы был валидный TLS-сертификат и webhook-трафик принимался только с подсетей Telegram.

```sh
cd caddy
ln -s ../.env .env
docker compose up -d
```

## 🧪 Тестирование

```sh
uv sync --frozen --group dev
uv run pybabel compile -d locales -D messages # Если нет скомпилированных локалей
uv run pytest tests/ -v
```

- `tests/unit/` — юнит-тесты.
- `tests/integration/` — интеграционные тесты с помощью `testcontainers`.


## 🛠 Разработка

### Перевод | i18n
Переводы редактируются в `.po` файлах в папке `locales/`. После внесения изменений их необходимо скомпилировать.

1. **Компиляция**
```sh
uv run pybabel compile -d locales -D messages
```

2. **Обновление при добавлении новых ключей (i18n_key):**

Добавьте ключ в `messages.pot`, обновите локализацию, переведите и скомпилируйте:
```sh
uv run pybabel update -d locales -D messages -i locales/messages.pot
```
