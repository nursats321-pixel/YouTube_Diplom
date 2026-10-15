# Media Downloader

Учебное веб-приложение на Python для получения информации о видео YouTube, просмотра доступных качеств и скачивания выбранного варианта. Пользователь может зарегистрироваться, войти, скачать ролик и управлять историей загрузок.

[Презентация проекта для защиты](presentation/Media_Downloader_Predefense.pptx)

## Технологии

- **FastAPI, Python, Uvicorn** — сервер и маршруты сайта.
- **Jinja2, HTML, CSS, JavaScript** — страницы и обновление прогресса.
- **yt-dlp** — информация о видео и загрузка.
- **FFmpeg** — объединение видео и аудио в MP4, если нужно.
- **Redis** — временный статус фоновой загрузки.
- **SQLite** локально; **PostgreSQL** можно подключить для хостинга.
- **Docker Compose** — запуск приложения и Redis вместе.

## Скачать и запустить с GitHub

Нужны Git, Docker Desktop (Windows/macOS) или Docker Engine с Compose (Linux), а также интернет. Python, Redis и FFmpeg отдельно для запуска через Docker устанавливать не требуется.

```bash
git clone https://github.com/nursats321-pixel/YouTube_Diplom.git
cd YouTube_Diplom
docker compose up --build -d
```

Первый запуск может занять несколько минут, пока Docker скачает зависимости и соберёт образ. Затем открой **http://127.0.0.1:10000**, зарегистрируйся и войди.

Основные команды:

```bash
docker compose logs -f app   # смотреть журнал
docker compose down          # остановить приложение
docker compose up -d         # запустить снова после первой сборки
```

Docker хранит локальную базу и скачанные файлы в volumes. Чтобы удалить их тоже, используй `docker compose down --volumes`.

## Доступ с других устройств

Чтобы комиссия открыла приложение со своих устройств, установи [cloudflared](https://developers.cloudflare.com/tunnel/get-started/), оставь Docker включённым и в отдельном окне терминала запусти:

```bash
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:10000
```

Открой выданную ссылку `https://....trycloudflare.com`. Она временная и работает, пока включены компьютер, Docker и окно туннеля. Пользуйся отдельным демонстрационным аккаунтом.

## Локальная разработка без Docker

Для запуска Python-кода напрямую нужны Python, Redis, FFmpeg и Deno для провайдера PO Token. В папке проекта создай и активируй виртуальное окружение.

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows PowerShell:**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Для обычного запуска и демонстрации рекомендуется Docker Compose: он также устанавливает системные зависимости.

## Как пользоваться

1. Создай аккаунт или войди.
2. Вставь ссылку на YouTube и нажми **Получить**.
3. Выбери показанное доступное качество и нажми **Скачать видео**.
4. Дождись загрузки файла. Историю можно открыть в меню, скачать запись повторно или удалить её.

Доступные качества и успешное скачивание зависят от ответа YouTube. Сервис может ограничить отдельные ролики или форматы.

## Отправить свои изменения в GitHub

После редактирования файлов из папки проекта выполни:

```bash
git status
git add README.md compose.yaml presentation/Media_Downloader_Predefense.pptx
git commit -m "Update project guide"
git push origin main
```

Если менял другие файлы, добавь их через `git add`. Не отправляй в GitHub `.env`, `youtube-cookies.txt`, `.secret_key`, локальную базу данных и скачанные видео.

## Где находится логика

- `app/main.py` — регистрация, вход, страницы, база данных, история и фоновые задачи.
- `app/services/youtube.py` — получение данных и форматов, скачивание через yt-dlp.
- `app/templates/` — HTML-страницы; `app/static/` — CSS и JavaScript.
- `Dockerfile` — сборка среды приложения; `compose.yaml` — приложение и Redis.
