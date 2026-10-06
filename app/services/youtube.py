import os

import yt_dlp


DOWNLOAD_DIR = "downloads"


def get_video_info(url: str):

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "cookiesfrombrowser": ("chrome",),
    }

    with yt_dlp.YoutubeDL(options) as ydl:

        info = ydl.extract_info(
            url,
            download=False,
        )

    formats = []

    for fmt in info.get("formats", []):

        height = fmt.get("height")
        width = fmt.get("width")
        vcodec = fmt.get("vcodec")
        format_id = fmt.get("format_id")

        if not height:
            continue

        if not format_id:
            continue

        if not vcodec:
            continue

        if vcodec == "none":
            continue

        if not vcodec.startswith("avc1"):
            continue

        formats.append({
            "format_id": format_id,
            "height": height,
            "width": width,
            "fps": fmt.get("fps"),
            "ext": fmt.get("ext"),
            "vcodec": vcodec,
            "acodec": fmt.get("acodec"),
        })

    unique_formats = {}

    for fmt in formats:

        height = fmt["height"]

        if height not in unique_formats:

            unique_formats[height] = fmt

    qualities = sorted(
        unique_formats.values(),
        key=lambda x: x["height"],
        reverse=True,
    )

    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "webpage_url": info.get("webpage_url"),
        "qualities": qualities,
    }


def download_video(
    url: str,
    height: int,
    format_id: str,
    progress_callback=None,
):

    os.makedirs(
        DOWNLOAD_DIR,
        exist_ok=True,
    )

    with yt_dlp.YoutubeDL({
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "cookiesfrombrowser": ("chrome",),
    }) as ydl:

        info = ydl.extract_info(
            url,
            download=False,
        )

    video_id = info.get("id")
    title = info.get("title")

    if not video_id:
        raise ValueError(
            "Не удалось определить ID видео"
        )

    if not format_id:
        raise ValueError(
            "Не выбран формат видео"
        )

    selected_format = None

    for fmt in info.get("formats", []):

        if str(fmt.get("format_id")) != str(format_id):
            continue

        vcodec = fmt.get("vcodec")

        if not vcodec:
            continue

        if vcodec == "none":
            continue

        if not vcodec.startswith("avc1"):
            continue

        selected_format = fmt

        break

    if selected_format is None:
        raise ValueError(
            f"Формат {format_id} недоступен"
        )

    real_height = selected_format.get(
        "height"
    )

    if real_height != height:
        raise ValueError(
            f"Формат {format_id} имеет "
            f"разрешение {real_height}p, "
            f"а выбран параметр {height}p"
        )

    filename = (
        f"{video_id}_{height}p.mp4"
    )

    output_path = os.path.join(
        DOWNLOAD_DIR,
        filename,
    )

    if os.path.exists(output_path):

        if progress_callback:

            progress_callback({
                "status": "completed",
                "progress": 100,
                "speed": "",
                "eta": "",
                "filename": filename,
                "title": title,
                "height": height,
            })

        return {
            "id": video_id,
            "title": title,
            "filename": filename,
            "height": height,
        }

    def progress_hook(data):

        if data["status"] == "downloading":

            downloaded = data.get(
                "downloaded_bytes",
                0,
            )

            total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
                or 0
            )

            if total:

                progress = (
                    downloaded / total
                ) * 100

            else:

                progress = 0

            speed = data.get("speed")
            eta = data.get("eta")

            if speed:

                speed_text = (
                    f"{speed / 1024 / 1024:.2f} MB/s"
                )

            else:

                speed_text = ""

            if eta is not None:

                minutes, seconds = divmod(
                    eta,
                    60,
                )

                if minutes:

                    eta_text = (
                        f"{int(minutes)} мин "
                        f"{int(seconds)} сек"
                    )

                else:

                    eta_text = (
                        f"{int(seconds)} сек"
                    )

            else:

                eta_text = ""

            if progress_callback:

                progress_callback({
                    "status": "downloading",
                    "progress": round(
                        progress,
                        1,
                    ),
                    "speed": speed_text,
                    "eta": eta_text,
                })

        elif data["status"] == "finished":

            if progress_callback:

                progress_callback({
                    "status": "processing",
                    "progress": 100,
                    "speed": "",
                    "eta": "",
                })

    format_string = (
        f"{format_id}+bestaudio[acodec^=mp4a]/"
        f"{format_id}+bestaudio/"
        f"{format_id}"
    )

    options = {

        "quiet": True,

        "no_warnings": True,

        "noplaylist": True,

        "cookiesfrombrowser": (
            "chrome",
        ),

        "format": format_string,

        "merge_output_format": "mp4",

        "outtmpl": output_path,

        "overwrites": False,

        "progress_hooks": [
            progress_hook
        ],
    }

    with yt_dlp.YoutubeDL(options) as ydl:

        ydl.extract_info(
            url,
            download=True,
        )

    if not os.path.exists(output_path):

        raise FileNotFoundError(
            "Готовый MP4 файл не найден"
        )

    if progress_callback:

        progress_callback({
            "status": "completed",
            "progress": 100,
            "speed": "",
            "eta": "",
            "filename": filename,
            "title": title,
            "height": height,
        })

    return {
        "id": video_id,
        "title": title,
        "filename": filename,
        "height": height,
    }