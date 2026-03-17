"""
FB Album Extractor
Flask web application — fetch FB album photos, OCR, write to Google Sheets.

Run with:
    conda activate fb-album-extractor
    python app.py

Then open: http://localhost:8080
"""
import json
import os
import queue
import threading
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

load_dotenv()

from scraper.fb_api import fetch_album_photos
from scraper.ocr import extract_text_from_url
from scraper.sheets_writer import write_photos_to_sheet

app = Flask(__name__)

jobs: dict = {}
jobs_lock = threading.Lock()


def _background_job(job_id: str, album_id: str, access_token: str, spreadsheet_id: str) -> None:
    q = jobs[job_id]["queue"]

    def notify(message: str, status: str = "progress") -> None:
        q.put(json.dumps({"status": status, "message": message}))

    try:
        # 1. Fetch all photos from the album
        notify("連接 Facebook Graph API，抓取相簿照片中...")
        photos = fetch_album_photos(album_id, access_token, progress_callback=notify)

        if not photos:
            notify("找不到照片，請確認相簿 ID 和 Access Token。", status="error")
            with jobs_lock:
                jobs[job_id]["status"] = "error"
            return

        album_name = photos[0].get("album_name", album_id) if photos else album_id
        notify(f"共找到 {len(photos)} 張照片（相簿：{album_name}）")

        # 2. OCR each photo
        notify("開始圖片文字辨識（Apple Vision OCR）...")
        for i, photo in enumerate(photos):
            image_url = photo.get("image_url", "")
            if image_url:
                ocr_text = extract_text_from_url(image_url)
                photo["ocr_text"] = ocr_text
            else:
                photo["ocr_text"] = ""

            if (i + 1) % 10 == 0 or i == len(photos) - 1:
                notify(f"OCR 進度：{i + 1}/{len(photos)}")

        # 3. Write to Google Sheets
        notify("寫入 Google Sheets 中...")
        written = write_photos_to_sheet(photos, album_id, progress_callback=notify, spreadsheet_id=spreadsheet_id)

        with jobs_lock:
            jobs[job_id]["status"] = "done"

        notify(f"完成！新增 {written} 筆（共 {len(photos)} 張），已同步至 Google Sheets。", status="done")

    except Exception as exc:
        with jobs_lock:
            jobs[job_id]["status"] = "error"
        notify(f"錯誤：{exc}", status="error")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start_job():
    data = request.get_json() or {}
    album_id = data.get("album_id", "").strip()
    access_token = (data.get("access_token", "").strip()
                    or os.getenv("FB_ACCESS_TOKEN", "").strip())
    spreadsheet_id = (data.get("spreadsheet_id", "").strip()
                      or os.getenv("GOOGLE_SPREADSHEET_ID", "").strip())

    if not album_id:
        return jsonify({"error": "請輸入相簿 ID。"}), 400
    if not access_token:
        return jsonify({"error": "請輸入 Access Token（或在 .env 設定 FB_ACCESS_TOKEN）。"}), 400
    if not spreadsheet_id:
        return jsonify({"error": "請輸入 Google Spreadsheet ID（或在 .env 設定 GOOGLE_SPREADSHEET_ID）。"}), 400

    job_id = str(uuid.uuid4())
    with jobs_lock:
        jobs[job_id] = {"queue": queue.Queue(), "status": "running"}

    threading.Thread(
        target=_background_job,
        args=(job_id, album_id, access_token, spreadsheet_id),
        daemon=True,
    ).start()
    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>")
def progress(job_id: str):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    def generate():
        q = jobs[job_id]["queue"]
        while True:
            try:
                msg = q.get(timeout=30)
                yield f"data: {msg}\n\n"
                if json.loads(msg).get("status") in ("done", "error"):
                    break
            except queue.Empty:
                yield 'data: {"status": "heartbeat"}\n\n'

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


if __name__ == "__main__":
    Path("downloads").mkdir(exist_ok=True)
    print("\n FB Album Extractor is running!")
    print(" Open your browser to: http://localhost:8080\n")
    app.run(debug=False, host="127.0.0.1", port=8080, threaded=True)
