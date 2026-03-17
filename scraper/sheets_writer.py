"""
Google Sheets writer for FB album photo data.
"""
import time
from datetime import date

import gspread

CREDENTIALS_PATH = "./credentials/fb-album-extractor-490401-fe1cd7794ccf.json"
SPREADSHEET_ID = "1B2vDGBhCu_Eah07eNkhshdwfe55G_l3B5_icdc7F0fM"
HEADERS = ["id", "link", "updated_time", "album_name", "album_id", "圖片文字內容"]
WRITE_SLEEP = 1.2


def _get_sheet_name(album_id: str) -> str:
    today = date.today().strftime("%Y%m%d")
    return f"{album_id}_{today}"


def get_or_create_worksheet(sheet_name: str) -> gspread.Worksheet:
    gc = gspread.service_account(filename=CREDENTIALS_PATH)
    sh = gc.open_by_key(SPREADSHEET_ID)
    try:
        ws = sh.worksheet(sheet_name)
        print(f"工作表已存在：{sheet_name}")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=5000, cols=len(HEADERS))
        ws.append_row(HEADERS, value_input_option="RAW")
        time.sleep(WRITE_SLEEP)
        print(f"建立新工作表：{sheet_name}")
    return ws


def get_existing_ids(ws: gspread.Worksheet) -> set:
    """Return set of photo IDs already in the sheet (column A, skip header)."""
    try:
        all_values = ws.get_all_values()
    except Exception:
        return set()
    if len(all_values) < 2:
        return set()
    return {row[0] for row in all_values[1:] if row}


def write_photos_to_sheet(
    photos: list[dict],
    album_id: str,
    progress_callback=None,
) -> int:
    """
    Write photos to Google Sheets.
    Skips photos whose ID already exists (incremental update).
    Returns count of newly written rows.
    """
    sheet_name = _get_sheet_name(album_id)
    ws = get_or_create_worksheet(sheet_name)
    existing_ids = get_existing_ids(ws)

    if existing_ids and progress_callback:
        progress_callback(f"Google Sheets 已有 {len(existing_ids)} 筆，跳過重複中...")

    written = 0
    for photo in photos:
        photo_id = photo.get("id", "")
        if photo_id in existing_ids:
            continue

        row = [
            photo_id,
            photo.get("link", ""),
            photo.get("updated_time", ""),
            photo.get("album_name", ""),
            photo.get("album_id", ""),
            photo.get("ocr_text", ""),
        ]
        ws.append_row(row, value_input_option="RAW")
        time.sleep(WRITE_SLEEP)
        written += 1

        if progress_callback and written % 5 == 0:
            progress_callback(f"已寫入 {written} 筆...")

    return written
