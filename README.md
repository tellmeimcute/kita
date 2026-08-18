## kita - telegram suggestions service bot

Telegram бот для быстрого запуска пользовательских Telegram-ботов предложек c автопостингом в канал, рассылками и модерацией.

---

### ✨ Основные возможности
- **Мастер-бот:** регистрация пользовательских ботов предложек.
- **Предложка:** принимает фото, видео, медиагруппы (альбомы), обычный текст и репосты с каналов.
- **Рассылка:** отправка фото, видео, медиагрупп (альбомов), текста и репостов.
- **Модерация:** назначение нескольких администраторов, блокировка пользователей.
- **Локализация (i18n):** поддержка `ru` / `en`, редактирование переводов через `.po` файлы.


## 🚀 Быстрый старт (Docker)

### Предварительные требования
- Наличие зарегистрированого домена
- A/AAAA DNS запись указывающая на IP вашего сервера
- Установленный на сервере [Docker Engine](https://docs.docker.com/engine/install/)
- Открытые порты: 80 (ACME challenge) и WEBHOOK_PORT (по умолчанию 8443)

### Установка и запуск
1. **Склонируйте репозиторий**
```sh
git clone https://github.com/tellmeimcute/kita.git && cd kita
```

2. **Создайте .env файл в корне на основе .env.example**
```sh
cp .env.example .env
```

Генирируем пароль БД
```sh
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 32)/" .env
```

Редактируем оставшиеся переменные
```sh
nano .env
```

Обязательно заполните следующие:
| Переменная       | Описание                     | Пример        |
| ---------------- | ---------------------------- | ------------- |
| `WEBHOOK_DOMAIN` | Домен                        | `example.com` |
| `WEBHOOK_PORT`   | Принимается только 8443, 443 | `8443`        |

1. **Создайте папку secrets**
```sh
mkdir -p secrets
```

1. **Создайте файл с токеном телеграм бота**
```sh
echo YOUR_TOKEN > secrets/.tg_token
```

1. **Сгенерируйте ключ шифрования и secret_token для телеграм вебхука**
```sh
openssl rand -base64 32 > secrets/.encryption_key
```

```sh
openssl rand -hex 32 > secrets/.webhook_secret
```

6. **Создайте docker network**
```sh
docker network create kita-proxy
```

7. **Запуск**
```sh
docker compose up -d
```

8. **Опционально: посмотреть логи.**
```sh
docker compose logs -f -t
```

### Запуск Caddy реверс прокси

```sh
cd caddy
```

```sh
ln -s ../.env .env
```

```sh
docker compose up -d
```

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
