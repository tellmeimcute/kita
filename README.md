## kita - telegram suggestions bot

Telegram бот для быстрого запуска пользовательских Telegram-ботов предложкек c автопостингом в канал, рассылками и модерацией.

---

### ✨ Основные возможности
- **Мастер-бот:** регистрация пользовательских ботов предложек.
- **Предложка:** принимает фото, видео, медиагруппы (альбомы), обычный текст и репосты с каналов.
- **Рассылка:** отправка фото, видео, медиагрупп (альбомов), текста и репостов.
- **Модерация:** назначение нескольких администраторов, блокировка пользователей.
- **Локализация (i18n):** поддержка `ru` / `en`, редактирование переводов через `.po` файлы.


## 🚀 Быстрый старт (Docker)

### Предварительные требования
Установите на хост [Docker Engine](https://docs.docker.com/engine/install/)

### Установка и запуск
1. **Склонируйте репозиторий**
```sh
git clone https://github.com/tellmeimcute/kita.git
cd kita
```

2. **Создайте .env файл в корне на основе .env.example**
```sh
cp .env.example .env
vim .env
```

3. **Создайте папку secrets**
```sh
mkdir -p secrets
```

4. **Создайте файл с токеном телеграм бота**
```sh
echo YOUR_TOKEN > secrets/.tg_token
```

5. **Сгенирируйте ключ шифрования и secret_token для телеграм вебхука**
```sh
openssl rand -base64 32 > secrets/.encryption_key
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

> [!CAUTION]
> Бот обязательно должен работать через реверс прокси.
>
> *Рекомендуемое:* **Caddy** (или Nginx).

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
