const progress = document.querySelector("[data-task-id]");

if (progress) {
    const taskId = progress.dataset.taskId;
    const fill = document.getElementById("progress-fill");
    const percent = document.getElementById("progress-percent");
    const status = document.getElementById("progress-status");
    const details = document.getElementById("download-details");

    const poll = async () => {
        try {
            const response = await fetch(`/api/download-status/${taskId}`);
            const task = await response.json();
            if (!response.ok) throw new Error(task.detail);

            const value = Math.max(0, Math.min(100, Number(task.progress || 0)));
            fill.style.width = `${value}%`;
            percent.textContent = `${value.toFixed(1)}%`;
            details.textContent = task.speed || task.eta || "";

            if (task.status === "completed") {
                status.textContent = "Готово. Скачивание файла...";
                const link = document.createElement("a");
                link.href = `/download/file/${taskId}`;
                link.download = task.filename || "video.mp4";
                document.body.appendChild(link);
                link.click();
                link.remove();
                return;
            }
            if (task.status === "error") {
                status.textContent = task.error || "Ошибка скачивания";
                return;
            }
            status.textContent = task.status === "processing" ? "Обработка видео..." : "Скачивание...";
            setTimeout(poll, 800);
        } catch (error) {
            status.textContent = error.message || "Ошибка получения статуса";
        }
    };

    poll();
}
