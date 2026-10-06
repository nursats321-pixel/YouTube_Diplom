const downloadButton = document.getElementById("download");
const clearUrlButton = document.getElementById("clear-url");
const urlInput = document.getElementById("url");
const result = document.getElementById("result");

let currentVideo = null;
let currentSocket = null;
let downloadState = "idle";

if (clearUrlButton) {
    clearUrlButton.addEventListener("click", () => {
        if (currentSocket) {
            currentSocket.close();
            currentSocket = null;
        }

        urlInput.value = "";
        result.innerHTML = "";
        currentVideo = null;
        downloadState = "idle";

        downloadButton.disabled = false;
        downloadButton.textContent = "Получить";

        urlInput.focus();
    });
}

downloadButton.addEventListener("click", async () => {
    if (downloadState !== "idle") {
        return;
    }

    const url = urlInput.value.trim();

    if (!url) {
        showError("Введите ссылку на YouTube");
        return;
    }

    if (currentSocket) {
        currentSocket.close();
        currentSocket = null;
    }

    downloadState = "loading";

    downloadButton.disabled = true;
    downloadButton.textContent = "Получаем информацию...";
    result.innerHTML = "";

    try {
        const response = await fetch("/api/youtube/info", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                url: url
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Не удалось получить информацию"
            );
        }

        if (!data.video) {
            throw new Error("Видео не найдено");
        }

        currentVideo = data.video;

        renderVideo(currentVideo);

        downloadState = "ready";

    } catch (error) {
        downloadState = "idle";
        showError(error.message);

    } finally {
        downloadButton.disabled = false;
        downloadButton.textContent = "Получить";
    }
});

function renderVideo(video) {
    const qualities = video.qualities || [];

    if (qualities.length === 0) {
        showError(
            "Для этого видео не удалось определить доступные качества"
        );
        return;
    }

    const qualityOptions = qualities
        .map((format) => {
            const height = Number(format.height);
            const formatId = String(format.format_id);

            return `
                <option value="${escapeHtml(formatId)}">
                    ${height}p
                </option>
            `;
        })
        .join("");

    result.innerHTML = `
        <div class="video-card">

            <div class="video-preview">
                <img
                    src="${escapeHtml(video.thumbnail || "")}"
                    alt="Превью видео"
                >
            </div>

            <div class="video-info">

                <h3>
                    ${escapeHtml(video.title || "Без названия")}
                </h3>

                <p class="video-author">
                    <strong>Автор:</strong>
                    ${escapeHtml(video.uploader || "Неизвестно")}
                </p>

                <p class="video-duration">
                    <strong>Длительность:</strong>
                    ${formatDuration(video.duration)}
                </p>

                <div class="quality-container">

                    <label for="quality">
                        Качество видео
                    </label>

                    <select id="quality">
                        ${qualityOptions}
                    </select>

                </div>

                <button
                    class="download-video"
                    id="download-video"
                    type="button"
                >
                    Скачать видео
                </button>

                <div
                    class="progress-container"
                    id="progress-container"
                    style="display: none;"
                >

                    <div class="progress-text">

                        <span id="progress-percent">
                            0%
                        </span>

                        <span id="progress-status">
                            Подготовка...
                        </span>

                    </div>

                    <div class="progress-bar">

                        <div
                            class="progress-fill"
                            id="progress-fill"
                        ></div>

                    </div>

                    <div class="download-details">

                        <span id="download-speed">
                            —
                        </span>

                        <span id="download-eta">
                            —
                        </span>

                    </div>

                </div>

            </div>

        </div>
    `;

    setupDownload(video);
}

function setupDownload(video) {
    const downloadVideoButton =
        document.getElementById("download-video");

    const qualitySelect =
        document.getElementById("quality");

    const progressContainer =
        document.getElementById("progress-container");

    const progressFill =
        document.getElementById("progress-fill");

    const progressPercent =
        document.getElementById("progress-percent");

    const progressStatus =
        document.getElementById("progress-status");

    const downloadSpeed =
        document.getElementById("download-speed");

    const downloadEta =
        document.getElementById("download-eta");

    downloadState = "ready";

    downloadVideoButton.onclick = async () => {
        if (downloadState === "downloading") {
            return;
        }

        if (downloadState === "completed") {
            downloadFile(downloadVideoButton.dataset.filename);
            return;
        }

        const url = urlInput.value.trim();
        const selectedFormatId = qualitySelect.value;

        const selectedOption =
            qualitySelect.options[
                qualitySelect.selectedIndex
            ];

        const selectedHeight =
            Number(
                selectedOption.textContent
                    .replace("p", "")
                    .trim()
            );

        if (!url) {
            showError("Ссылка на видео потеряна");
            return;
        }

        if (!selectedFormatId) {
            showError("Выберите качество видео");
            return;
        }

        if (!selectedHeight) {
            showError("Не удалось определить качество");
            return;
        }

        downloadState = "downloading";

        downloadVideoButton.disabled = true;
        qualitySelect.disabled = true;
        downloadVideoButton.textContent = "Запуск...";

        progressContainer.style.display = "block";

        progressStatus.textContent =
            "Создаём задачу...";

        progressPercent.textContent =
            "0%";

        progressFill.style.width =
            "0%";

        downloadSpeed.textContent =
            "—";

        downloadEta.textContent =
            "—";

        try {
            const downloadResponse =
                await fetch(
                    "/api/youtube/download",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            url: url,
                            height: selectedHeight,
                            format_id: selectedFormatId
                        })
                    }
                );

            const downloadData =
                await downloadResponse.json();

            if (!downloadResponse.ok) {
                throw new Error(
                    downloadData.detail ||
                    "Ошибка запуска скачивания"
                );
            }

            const taskId =
                downloadData.task_id;

            if (!taskId) {
                throw new Error(
                    "Сервер не вернул ID задачи"
                );
            }

            const protocol =
                window.location.protocol === "https:"
                    ? "wss:"
                    : "ws:";

            const wsUrl =
                `${protocol}//${window.location.host}` +
                `/ws/download/${taskId}`;

            currentSocket =
                new WebSocket(wsUrl);

            currentSocket.onopen = () => {
                progressStatus.textContent =
                    "Скачивание...";
            };

            currentSocket.onmessage = (event) => {
                const task =
                    JSON.parse(event.data);

                if (task.status === "starting") {
                    progressStatus.textContent =
                        "Подготовка...";
                }

                if (task.status === "downloading") {
                    const progress =
                        Number(task.progress || 0);

                    const safeProgress =
                        Math.max(
                            0,
                            Math.min(
                                100,
                                progress
                            )
                        );

                    progressFill.style.width =
                        `${safeProgress}%`;

                    progressPercent.textContent =
                        `${safeProgress.toFixed(1)}%`;

                    progressStatus.textContent =
                        "Скачивание...";

                    downloadSpeed.textContent =
                        task.speed || "—";

                    downloadEta.textContent =
                        task.eta
                            ? `Осталось: ${task.eta}`
                            : "—";
                }

                if (task.status === "processing") {
                    progressFill.style.width =
                        "100%";

                    progressPercent.textContent =
                        "100%";

                    progressStatus.textContent =
                        "Обработка видео...";

                    downloadSpeed.textContent =
                        "Конвертация в MP4";

                    downloadEta.textContent =
                        "Пожалуйста, подождите";
                }

                if (task.status === "completed") {
                    progressFill.style.width =
                        "100%";

                    progressPercent.textContent =
                        "100%";

                    progressStatus.textContent =
                        "Готово";

                    downloadSpeed.textContent =
                        "Файл готов";

                    downloadEta.textContent =
                        "—";

                    downloadVideoButton.disabled =
                        false;

                    qualitySelect.disabled =
                        false;

                    downloadVideoButton.textContent =
                        "Скачать файл";

                    downloadVideoButton.dataset.filename =
                        task.filename;

                    downloadState = "completed";

                    if (currentSocket) {
                        currentSocket.close();
                        currentSocket = null;
                    }
                }

                if (task.status === "error") {
                    downloadState = "ready";

                    downloadVideoButton.disabled =
                        false;

                    qualitySelect.disabled =
                        false;

                    downloadVideoButton.textContent =
                        "Скачать видео";

                    throw new Error(
                        task.error ||
                        "Ошибка скачивания"
                    );
                }
            };

            currentSocket.onerror = () => {
                downloadState = "ready";

                showError(
                    "Ошибка соединения с сервером"
                );

                downloadVideoButton.disabled =
                    false;

                qualitySelect.disabled =
                    false;

                downloadVideoButton.textContent =
                    "Скачать видео";
            };

            currentSocket.onclose = () => {
                currentSocket = null;
            };

        } catch (error) {
            downloadState = "ready";

            showError(error.message);

            downloadVideoButton.disabled =
                false;

            qualitySelect.disabled =
                false;

            downloadVideoButton.textContent =
                "Скачать видео";

            progressContainer.style.display =
                "none";

            if (currentSocket) {
                currentSocket.close();
                currentSocket = null;
            }
        }
    };
}

function downloadFile(filename) {
    if (!filename) {
        showError("Файл не найден");
        return;
    }

    const link =
        document.createElement("a");

    link.href =
        `/api/youtube/file/${encodeURIComponent(
            filename
        )}`;

    link.download =
        filename;

    document.body.appendChild(link);

    link.click();

    link.remove();

    setTimeout(() => {
        if (currentVideo) {
            renderVideo(currentVideo);
        }
    }, 500);
}

function showError(message) {
    result.innerHTML = `
        <div class="error-message">
            <strong>Ошибка</strong>
            <p>${escapeHtml(message)}</p>
        </div>
    `;

    downloadState = "idle";
}

function formatDuration(seconds) {
    if (!seconds) {
        return "Неизвестно";
    }

    seconds = Number(seconds);

    const hours =
        Math.floor(seconds / 3600);

    const minutes =
        Math.floor(
            (seconds % 3600) / 60
        );

    const remainingSeconds =
        Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
    }

    return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
