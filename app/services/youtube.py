import os
import shutil
import tempfile
import threading

import yt_dlp


DOWNLOAD_DIR = "downloads"

_cookies_copy_path = None
_cookies_source_mtime = None
_cookies_lock = threading.Lock()


def writable_cookies_file(source_path: str):
    global _cookies_copy_path
    global _cookies_source_mtime

    source_mtime = os.stat(
        source_path
    ).st_mtime_ns

    with _cookies_lock:
        if (
            _cookies_copy_path is None
            or _cookies_source_mtime != source_mtime
            or not os.path.exists(_cookies_copy_path)
        ):
            _cookies_copy_path = os.path.join(
                tempfile.gettempdir(),
                f"youtube-cookies-{os.getpid()}.txt",
            )

            shutil.copyfile(
                source_path,
                _cookies_copy_path,
            )

            os.chmod(
                _cookies_copy_path,
                0o600,
            )

            _cookies_source_mtime = source_mtime

    return _cookies_copy_path


def ydl_options():
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    cookies_file = os.getenv(
        "YTDLP_COOKIES_FILE"
    )

    if cookies_file:
        exists = os.path.isfile(
            cookies_file
        )

        print(
            f"YouTube cookies: {cookies_file}, exists={exists}"
        )

        if not exists:
            raise FileNotFoundError(
                "Файл cookies из YTDLP_COOKIES_FILE не найден"
            )

        cookies_copy = writable_cookies_file(
            cookies_file
        )

        options["cookiefile"] = cookies_copy

    return options


def get_video_info(url: str):
    options = ydl_options()

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(
            url,
            download=False,
        )

    formats = []

    for fmt in info.get(
        "formats",
        [],
    ):
        format_id = fmt.get(
            "format_id"
        )

        width = fmt.get(
            "width"
        )

        height = fmt.get(
            "height"
        )

        vcodec = fmt.get(
            "vcodec"
        )

        acodec = fmt.get(
            "acodec"
        )

        if not format_id:
            continue

        if not height:
            continue

        if not width:
            continue

        if not vcodec:
            continue

        if vcodec == "none":
            continue

        if not vcodec.startswith(
            "avc1"
        ):
            continue

        formats.append({
            "format_id": format_id,
            "height": int(height),
            "width": int(width),
            "fps": fmt.get("fps"),
            "ext": fmt.get("ext"),
            "vcodec": vcodec,
            "acodec": acodec,
        })

    unique_formats = {}

    for fmt in formats:
        quality = fmt["height"]

        if quality not in unique_formats:
            unique_formats[quality] = fmt

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
        "webpage_url": info.get(
            "webpage_url"
        ),
        "qualities": qualities,
    }


def download_video(
    url: str,
    height: int,
    format_id=None,
    progress_callback=None,
):
    os.makedirs(
        DOWNLOAD_DIR,
        exist_ok=True,
    )

    options = ydl_options()

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(
            url,
            download=False,
        )

    video_id = info.get(
        "id"
    )

    title = (
        info.get("title")
        or "YouTube video"
    )

    if not video_id:
        raise ValueError(
            "Не удалось определить ID видео"
        )

    selected_format = None

    for fmt in info.get(
        "formats",
        [],
    ):
        fmt_height = fmt.get(
            "height"
        )

        fmt_width = fmt.get(
            "width"
        )

        fmt_id = fmt.get(
            "format_id"
        )

        vcodec = fmt.get(
            "vcodec"
        )

        if not fmt_height:
            continue

        if not fmt_width:
            continue

        if not fmt_id:
            continue

        if int(fmt_height) != int(height):
            continue

        if not vcodec:
            continue

        if vcodec == "none":
            continue

        if not vcodec.startswith(
            "avc1"
        ):
            continue

        selected_format = fmt
        break

    if selected_format is None:
        raise ValueError(
            f"Качество {height}p недоступно"
        )

    selected_format_id = selected_format[
        "format_id"
    ]

    filename = (
        f"{video_id}_{height}p.mp4"
    )

    output_path = os.path.join(
        DOWNLOAD_DIR,
        filename,
    )

    if os.path.exists(
        output_path
    ):
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

            speed = data.get(
                "speed"
            )

            if speed:
                speed_text = (
                    f"{speed / 1024 / 1024:.2f} MB/s"
                )
            else:
                speed_text = ""

            eta = data.get(
                "eta"
            )

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

    download_options = ydl_options()

    download_options.update({
        "format": (
            f"{selected_format_id}+"
            "bestaudio[acodec^=mp4a]/"
            f"{selected_format_id}+"
            "bestaudio/"
            f"{selected_format_id}"
        ),
        "merge_output_format": "mp4",
        "concurrent_fragment_downloads": 8,
        "outtmpl": output_path,
        "overwrites": False,
        "progress_hooks": [
            progress_hook
        ],
    })

    with yt_dlp.YoutubeDL(
        download_options
    ) as ydl:
        ydl.extract_info(
            url,
            download=True,
        )

    if not os.path.exists(
        output_path
    ):
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