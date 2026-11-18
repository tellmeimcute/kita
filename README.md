# Kita — multi-tenant Telegram-сервис предложек

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
| Cache / FSM / Rate Limit | Redis, token-bucket + GCRA pacing (Lua)                 |
| Token Encryption         | cryptography (Fernet)                                   |
| Infra                    | Docker Compose, Docker Secrets, Caddy                   |
| Package Manager          | uv                                                      |


## 🚀 Быстрый старт (Docker)

> [!WARNING]
> На проде все секреты (`TG_TOKEN`, `WEBHOOK_SECRET`, `ENCRYPTION_KEYS`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`) должны находится **только** в `secrets/`, ни в коем случае не указывайте их в `.env`.


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

Отредактируйте остальные переменные:
```sh
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

5. **Сгенерируйте секреты (ключ шифрования, secret_token вебхука, пароли Postgres и Redis)**:
```sh
./scripts/generate_encryption_key.sh
./scripts/generate_redis_secrets.sh
openssl rand -hex 32 > secrets/.webhook_secret
openssl rand -hex 32 > secrets/.postgres_password
```

> [!NOTE]
> Postgres читает пароль из `secrets/.postgres_password` (через `POSTGRES_PASSWORD_FILE`), Redis — ACL-файл `secrets/.redis_acl` (директива `aclfile`), а приложение — пароль из `secrets/.redis_password`.
> 
> Если том Postgres уже инициализирован, значение в `secrets/.postgres_password` должно совпадать с текущим паролем БД.

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

## Ротация ключей шифрования

> [!WARNING]
> Перед ротацией рекомендуется сделать бекап БД и текущих ключей шифрования.

Ключи хранятся в `secrets/.encryption_keys`: **первая строка — актуальный ключ**, им шифруются новые данные, остальные строки — старые ключи, ими только расшифровываются уже сохранённые токены.
Ключ и зашифрованный токен могут иметь префикс версии (`v1:`, `v2:`, `vN:`); без префикса считается версией `v1`.

1. **Сгенерируйте новый ключ и поставьте его первым в файле с ключами.**

Префикс версии обязателен — без него ключ будет считаться `v1`. Старые ключи нужно оставить как минимум до полной ротации БД — они нужны для расшифровки существующих токенов. Скрипт сам определит следующую версию по текущему первому ключу и допишет старые ключи следом:
```sh
./scripts/generate_encryption_key.sh
```

2. **Перезапустите контейнеры**, чтобы подхватился новый ключ:

```sh
docker compose up -d --force-recreate bot worker
```

3. **Дождитесь запуска контейнеров и запустите ротацию** — скрипт батчами перешифрует зашифрованные данные новым ключем:

```sh
docker compose run --rm -e PYTHONPATH=/app/src --entrypoint uv bot run python -m scripts.rotate_encryption
```

4. **После полной ротации удалите старые ключи**, оставив только актуальный. Убедиться, что ротация завершена, можно повторным запуском скрипта из шага 3 — он должен вывести `Rotated 0 tokens`.

```sh
./scripts/remove_old_encryption_keys.sh
docker compose up -d --force-recreate bot worker
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
