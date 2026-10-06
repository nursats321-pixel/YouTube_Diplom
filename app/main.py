import asyncio
import os
import uuid

from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.services.youtube import get_video_info, download_video


app = FastAPI(
    title="YouTube Downloader",
    description="YouTube video downloader",
    version="1.0.0",
)

templates = Jinja2Templates(
    directory="app/templates"
)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


class VideoRequest(BaseModel):
    url: str
    height: int = 720
    format_id: str | None = None


download_tasks = {}


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
    )


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "YouTube Downloader",
    }


@app.post("/api/youtube/info")
async def youtube_info(data: VideoRequest):
    try:
        info = get_video_info(data.url)

        return {
            "success": True,
            "video": info,
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@app.post("/api/youtube/download")
async def youtube_download(data: VideoRequest):

    if not data.format_id:
        raise HTTPException(
            status_code=400,
            detail="Не выбран формат видео",
        )

    task_id = str(uuid.uuid4())

    download_tasks[task_id] = {
        "status": "starting",
        "progress": 0,
        "speed": "",
        "eta": "",
        "filename": None,
        "title": None,
        "height": data.height,
        "format_id": data.format_id,
        "error": None,
    }

    asyncio.create_task(
        run_download(
            task_id,
            data.url,
            data.height,
            data.format_id,
        )
    )

    return {
        "success": True,
        "task_id": task_id,
    }


async def run_download(
    task_id: str,
    url: str,
    height: int,
    format_id: str,
):
    try:

        download_tasks[task_id]["status"] = "downloading"

        def progress_callback(data):
            download_tasks[task_id].update(data)

        result = await asyncio.to_thread(
            download_video,
            url,
            height,
            format_id,
            progress_callback,
        )

        download_tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "speed": "",
            "eta": "",
            "filename": result["filename"],
            "title": result["title"],
            "height": result["height"],
            "format_id": format_id,
        })

    except Exception as e:

        download_tasks[task_id].update({
            "status": "error",
            "error": str(e),
        })


@app.websocket("/ws/download/{task_id}")
async def download_progress(
    websocket: WebSocket,
    task_id: str,
):
    await websocket.accept()

    try:

        while True:

            task = download_tasks.get(task_id)

            if task is None:

                await websocket.send_json({
                    "status": "error",
                    "error": "Задача не найдена",
                })

                break

            await websocket.send_json(task)

            if task["status"] in (
                "completed",
                "error",
            ):
                break

            await asyncio.sleep(0.5)

    except Exception:
        pass

    finally:

        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/api/youtube/file/{filename}")
async def youtube_file(filename: str):

    file_path = os.path.join(
        "downloads",
        filename,
    )

    if not os.path.exists(file_path):

        raise HTTPException(
            status_code=404,
            detail="Файл не найден",
        )

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="video/mp4",
    )
