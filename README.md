## kita - telegram suggestions bot

Бот принимает предложку (видео/картинки/mediagroup), автопостит в канал после прохождении модерации и имеет возможность назначения нескольких администраторов.

---

### ✨ Основные возможности
- Принимает фото, видео, и медиагруппы (альбомы)
- Поддержка нескольких администраторов
- Бан нежелательных пользователей
- i18n можно отредактировать на свой вкус


### Перевод | i18n
Перевод можно подредактировать в .po файлах. После редактирования перекомпилировать.
```shell
uv run pybabel compile -d locales -D messages
```

## Использование

### Установка
Проект использует менеджер пакетов [uv](https://docs.astral.sh/uv/).

Склонируйте репозиторий:
```
git clone https://github.com/tellmeimcute/kita.git
cd kita
```

Создайте .env файл в корне на основе .env.example
```
TG_TOKEN=bot_secret_token
DB_URL=db_url
ADMIN_ID=your_telegram_id
CHANNEL_ID=-100xxxxxxxxxx
```

Установите зависимости и скомпилируйте перевод.
```shell
uv sync
uv run pybabel compile -d locales -D messages
```

Можно запускать бота.
```
uv run .\src\main.py
```
