import asyncio
import json
import os
import uuid

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from redis import Redis

from app.services.youtube import download_video, get_video_info


DOWNLOAD_DIR = "downloads"
TASK_TTL_SECONDS = 60 * 60
redis_client = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True,
)

app = FastAPI(
    title="YouTube Downloader",
    description="YouTube video downloader",
    version="1.0.0",
)

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def page(request: Request, **context):
    return templates.TemplateResponse(request, "index.html", context)


def task_key(task_id: str):
    return f"youtube-download:{task_id}"


def save_task(task_id: str, **data):
    values = {key: str(value) for key, value in data.items() if value is not None}
    redis_client.hset(task_key(task_id), mapping=values)
    redis_client.expire(task_key(task_id), TASK_TTL_SECONDS)


@app.get("/")
async def home(request: Request):
    return page(request)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "YouTube Downloader"}


@app.post("/video")
async def video_info(request: Request, url: str = Form(...)):
    url = url.strip()
    if not url:
        return page(request, error="Введите ссылку на YouTube.")

    try:
        video = await asyncio.to_thread(get_video_info, url)
    except Exception as error:
        return page(request, error=str(error), url=url)

    if not video["qualities"]:
        return page(
            request,
            error="Для этого видео не удалось определить доступные качества.",
            url=url,
        )

    return page(request, video=video, url=url)


@app.post("/download")
async def start_download(
    request: Request,
    url: str = Form(...),
    format_id: str = Form(...),
):
    try:
        video = await asyncio.to_thread(get_video_info, url)
        selected_format = next(
            (
                item for item in video["qualities"]
                if str(item["format_id"]) == format_id
            ),
            None,
        )
        if selected_format is None:
            return page(request, error="Выбранное качество недоступно.", url=url)

        task_id = str(uuid.uuid4())
        save_task(
            task_id,
            status="starting",
            progress=0,
            title=video["title"],
            height=selected_format["height"],
            format_id=format_id,
            url=url,
            video=json.dumps(video),
        )
        asyncio.create_task(
            run_download(task_id, url, selected_format["height"], format_id)
        )
    except Exception as error:
        return page(request, error=str(error), url=url)

    return RedirectResponse(url=f"/download/{task_id}", status_code=303)


@app.get("/download/{task_id}")
async def download_page(request: Request, task_id: str):
    task = redis_client.hgetall(task_key(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    video_json = task.get("video")
    video = json.loads(video_json) if video_json else None
    return page(
        request,
        task_id=task_id,
        url=task.get("url", ""),
        video=video,
        selected_format_id=task.get("format_id"),
    )


async def run_download(task_id: str, url: str, height: int, format_id: str):
    try:
        save_task(task_id, status="downloading", progress=0)

        def progress_callback(data):
            save_task(task_id, **data)

        result = await asyncio.to_thread(
            download_video,
            url,
            height,
            format_id,
            progress_callback,
        )
        save_task(
            task_id,
            status="completed",
            progress=100,
            filename=result["filename"],
            title=result["title"],
            height=result["height"],
        )
    except Exception as error:
        save_task(task_id, status="error", error=str(error))


@app.get("/api/download-status/{task_id}")
async def download_status(task_id: str):
    task = redis_client.hgetall(task_key(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


@app.get("/download/file/{task_id}")
async def download_file(task_id: str):
    task = redis_client.hgetall(task_key(task_id))
    filename = task.get("filename")
    if task.get("status") != "completed" or not filename:
        raise HTTPException(status_code=404, detail="Файл ещё не готов")

    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Готовый файл не найден")

    return FileResponse(path=file_path, filename=filename, media_type="video/mp4")
