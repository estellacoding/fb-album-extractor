# FB Album Extractor

透過 Facebook Graph API 抓取相簿所有照片、OCR 辨識圖片文字，自動同步至 Google Sheets。

## 功能

- 透過 Facebook Graph API 抓取指定相簿的所有照片（自動翻頁，無張數限制）
- 使用 Apple Vision OCR 辨識圖片中的文字（支援繁體中文）
- 自動建立以 `相簿ID_日期` 命名的 Google Sheets 工作表
- 增量更新機制：已處理的照片自動跳過，不重複寫入
- 即時進度顯示（Server-Sent Events）

## 環境需求

- macOS（OCR 使用 Apple Vision，僅支援 macOS）
- Python 3.14+
- Conda

## 安裝

```bash
git clone https://github.com/estellacoding/fb-album-extractor.git
cd fb-album-extractor

conda create -n fb-album-extractor python=3.14
conda activate fb-album-extractor
pip install -r requirements.txt
```

## 設定

### 1. 環境變數

複製範本並填入設定：

```bash
cp .env.example .env
```

`.env` 內容：

```
FB_ACCESS_TOKEN=你的 Facebook Access Token
```

Access Token 留空時，前端輸入欄也可以直接貼入。

#### 取得 Long-lived Token（建議，有效期 60 天）

1. 至 [Meta for Developers](https://developers.facebook.com/apps/) 建立應用程式
2. 前往 [Graph API Explorer](https://developers.facebook.com/tools/explorer) 取得 Access Token（需包含 pages_show_list, business_management, pages_read_engagement, pages_manage_metadata, public_profile 權限）
3. 將短期 token 換成長期 token
4. 將回傳的 token 填入 `.env`

### 2. Google Sheets Service Account

1. 至 [Google Cloud Console](https://console.cloud.google.com/) 建立 Service Account
2. 下載 JSON 金鑰，放到 `credentials/` 資料夾
3. 將 Service Account 的 email 加為 Google Sheet 的「編輯者」
4. 在 `scraper/sheets_writer.py` 確認以下常數：

```python
CREDENTIALS_PATH = "./credentials/fb-album-extractor-490401-fe1cd7794ccf.json"
SPREADSHEET_ID   = "1B2vDGBhCu_Eah07eNkhshdwfe55G_l3B5_icdc7F0fM"
```

## 使用方式

```bash
conda activate fb-album-extractor
python app.py
```

開啟瀏覽器至 `http://localhost:8080`

1. 輸入相簿 ID（例如 `122119543826466169`）
2. Access Token 留空則自動使用 `.env` 設定，或直接貼入新 token
3. 點擊「開始抓取並 OCR」

## 輸出格式

### Google Sheets 工作表名稱

```
{相簿ID}_{YYYYMMDD}
```

例：`122119543826466169_20260317`

### 欄位說明

| 欄位 | 說明 |
|------|------|
| id | 照片 ID |
| link | Facebook 照片連結 |
| updated_time | 更新時間（UTC） |
| album_name | 相簿名稱 |
| album_id | 相簿 ID |
| 圖片文字內容 | Apple Vision OCR 辨識結果 |

## 注意事項

- 僅支援 **macOS**（Apple Vision Framework）
- Facebook Access Token 短期約 1–2 小時過期，建議換成 Long-lived Token（60 天）
- Graph API 有請求頻率限制，大量照片時翻頁之間有短暫延遲屬正常現象
- OCR 第一次執行時需要初始化 Apple Vision，之後會較快
