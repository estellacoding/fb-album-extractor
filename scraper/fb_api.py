"""
Facebook Graph API — fetch all photos from an album with paging.
"""
import time
import requests

FB_API_BASE = "https://graph.facebook.com/v25.0"
PAGE_LIMIT = 25  # photos per page request


def fetch_album_photos(album_id: str, access_token: str, progress_callback=None) -> list[dict]:
    """
    Fetch all photos from a Facebook album using paging.next until exhausted.
    Returns a list of photo dicts with keys:
        id, link, updated_time, album (name+id), image_url (largest)
    """
    url = f"{FB_API_BASE}/{album_id}/photos"
    params = {
        "fields": "id,link,updated_time,album,images",
        "access_token": access_token,
        "limit": PAGE_LIMIT,
    }

    photos = []
    page = 1

    while url:
        if progress_callback:
            progress_callback(f"抓取第 {page} 頁照片（已取得 {len(photos)} 張）...")

        try:
            resp = requests.get(url, params=params if page == 1 else None, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"FB API 請求失敗：{e}") from e

        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"FB API 錯誤：{data['error'].get('message', data['error'])}")

        for item in data.get("data", []):
            # Pick the largest image (first in list = highest resolution)
            images = item.get("images", [])
            largest = images[0]["source"] if images else None

            photos.append({
                "id": item.get("id", ""),
                "link": item.get("link", ""),
                "updated_time": item.get("updated_time", ""),
                "album_name": item.get("album", {}).get("name", ""),
                "album_id": item.get("album", {}).get("id", album_id),
                "image_url": largest,
            })

        paging = data.get("paging", {})
        next_url = paging.get("next")
        url = next_url
        params = None  # next URL already contains all params
        page += 1

        if next_url:
            time.sleep(0.3)  # be gentle with the API

    return photos
