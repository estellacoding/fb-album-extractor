"""
OCR using macOS Vision framework — supports Traditional Chinese (zh-Hant).
"""
import urllib.request
import tempfile
from pathlib import Path

try:
    import Vision
    from Foundation import NSURL
    _VISION_AVAILABLE = True
except ImportError:
    _VISION_AVAILABLE = False


def download_image(url: str, dest: Path) -> bool:
    """Download image from URL to dest path. Returns True on success."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            dest.write_bytes(response.read())
        return True
    except Exception as e:
        print(f"  圖片下載失敗：{e}")
        return False


def extract_text_from_url(image_url: str) -> str:
    """Download image to temp file and run Apple Vision OCR."""
    if not _VISION_AVAILABLE:
        return "[Vision framework 不可用，請在 macOS 上執行]"

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        if not download_image(image_url, tmp_path):
            return ""
        return _run_vision_ocr(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _run_vision_ocr(image_path: Path) -> str:
    """Run Vision OCR on a local image file."""
    try:
        img_url = NSURL.fileURLWithPath_(str(image_path.resolve()))
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLanguages_(["zh-Hant", "zh-Hans", "en-US"])
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(True)

        handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(img_url, {})
        success, error = handler.performRequests_error_([request], None)

        if not success or error:
            return ""

        texts = []
        for obs in request.results():
            candidates = obs.topCandidates_(1)
            if candidates:
                texts.append(candidates[0].string())

        return "\n".join(texts).strip()
    except Exception as e:
        print(f"  OCR 錯誤：{e}")
        return ""
