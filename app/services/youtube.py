import os

import yt_dlp


DOWNLOAD_DIR = "downloads"


def ydl_options():
    """Use yt-dlp's maintained YouTube clients and format selection logic."""
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 3,
        "file_access_retries": 3,
    }


def _video_formats(info):
    formats = []
    for fmt in info.get("formats", []):
        height, width = fmt.get("height"), fmt.get("width")
        if not height or not width or not fmt.get("format_id"):
            continue
        if fmt.get("vcodec") in (None, "none"):
            continue
        formats.append(fmt)
    return formats


def get_video_info(url: str):
    with yt_dlp.YoutubeDL(ydl_options()) as ydl:
        info = ydl.extract_info(url, download=False)

    by_height = {}
    for fmt in _video_formats(info):
        height = int(fmt["height"])
        current = by_height.get(height)
        score = (fmt.get("acodec") not in (None, "none"), fmt.get("fps") or 0,
                 fmt.get("filesize") or fmt.get("filesize_approx") or 0)
        if current is None or score > current[0]:
            by_height[height] = (score, fmt)

    qualities = []
    for height, (_, fmt) in sorted(by_height.items(), reverse=True):
        qualities.append({
            "format_id": str(height),
            "height": height,
            "width": int(fmt["width"]),
            "fps": fmt.get("fps"),
            "ext": fmt.get("ext"),
            "vcodec": fmt.get("vcodec"),
            "acodec": fmt.get("acodec"),
        })

    return {
        "id": info.get("id"),
        "title": info.get("title") or "YouTube video",
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "webpage_url": info.get("webpage_url"),
        "qualities": qualities,
    }


def download_video(url: str, height: int, format_id=None, progress_callback=None):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    with yt_dlp.YoutubeDL(ydl_options()) as ydl:
        info = ydl.extract_info(url, download=False)

    video_id = info.get("id")
    title = info.get("title") or "YouTube video"
    if not video_id:
        raise ValueError("Не удалось определить ID видео")

    available_heights = [int(fmt["height"]) for fmt in _video_formats(info)]
    if int(height) not in available_heights:
        raise ValueError(f"Качество {height}p больше недоступно")

    filename = f"{video_id}_{int(height)}p.mp4"
    output_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        if progress_callback:
            progress_callback({"status": "completed", "progress": 100,
                               "filename": filename, "title": title, "height": int(height)})
        return {"id": video_id, "title": title, "filename": filename, "height": int(height)}

    def progress_hook(data):
        if not progress_callback:
            return
        if data["status"] == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            speed = data.get("speed")
            eta = data.get("eta")
            progress_callback({
                "status": "downloading",
                "progress": round(data.get("downloaded_bytes", 0) / total * 100, 1) if total else 0,
                "speed": f"{speed / 1024 / 1024:.2f} MB/s" if speed else "",
                "eta": f"{int(eta)} сек" if eta is not None else "",
            })
        elif data["status"] == "finished":
            progress_callback({"status": "processing", "progress": 100, "speed": "", "eta": ""})

    options = ydl_options()
    options.update({
        "format": (
            f"bestvideo[height={int(height)}][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
            f"bestvideo[height={int(height)}]+bestaudio/"
            f"best[height={int(height)}]"
        ),
        "merge_output_format": "mp4",
        "concurrent_fragment_downloads": 4,
        "outtmpl": output_path,
        "overwrites": True,
        "progress_hooks": [progress_hook],
    })
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.extract_info(url, download=True)

    if not os.path.exists(output_path):
        raise FileNotFoundError("Готовый MP4 файл не найден. Проверьте, что установлен FFmpeg.")
    if progress_callback:
        progress_callback({"status": "completed", "progress": 100, "speed": "", "eta": "",
                           "filename": filename, "title": title, "height": int(height)})
    return {"id": video_id, "title": title, "filename": filename, "height": int(height)}
