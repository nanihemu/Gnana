"""Turn any uploaded file (doc, image, audio, video, text) into plain text for analysis.

Raises ExtractError instead of returning error text, so a failure is never saved as lesson content.
ExtractError.soft=True means the file can still be shared as-is (e.g. a video with no transcription installed).
"""
import os
import shutil
import subprocess
import tempfile
from . import ai

DOC_EXT = {".pdf", ".docx", ".pptx", ".txt", ".md", ".csv", ".html", ".htm", ".rtf", ".json"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


class ExtractError(Exception):
    def __init__(self, msg, soft=False):
        super().__init__(msg)
        self.soft = soft


def detect_kind(filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]
    if ext in IMG_EXT:
        return "image"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in VIDEO_EXT:
        return "video"
    return "document"


def extract_text(path: str, filename: str) -> tuple[str, str]:
    """Returns (kind, text). Raises ExtractError on failure."""
    ext = os.path.splitext(filename.lower())[1]
    kind = detect_kind(filename)
    try:
        if kind == "image":
            text = _image(path, ext)
        elif kind == "audio":
            text = _transcribe(path)
        elif kind == "video":
            text = _video(path)
        else:
            text = _document(path, ext)
    except ExtractError:
        raise
    except Exception as e:  # noqa
        raise ExtractError(f"Could not read {filename}: {ai.friendly(e)}", soft=kind in ("audio", "video"))
    if not text or not text.strip():
        hint = " It may be a scanned PDF; upload it as images instead." if ext == ".pdf" else ""
        raise ExtractError(f"No readable text found in {filename}.{hint}", soft=kind in ("audio", "video"))
    return kind, text


def _document(path, ext):
    if ext == ".pdf":
        from pypdf import PdfReader
        r = PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in r.pages)
    if ext == ".docx":
        import docx
        d = docx.Document(path)
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    if ext == ".pptx":
        from pptx import Presentation
        out = []
        for i, s in enumerate(Presentation(path).slides, 1):
            out.append(f"Slide {i}")
            for sh in s.shapes:
                if sh.has_text_frame:
                    out.append(sh.text_frame.text)
        return "\n".join(out)
    with open(path, "rb") as f:
        raw = f.read()
    txt = raw.decode("utf-8", errors="ignore")
    if ext in (".html", ".htm"):
        import re
        txt = re.sub(r"<(script|style).*?</\1>", " ", txt, flags=re.S)
        txt = re.sub(r"<[^>]+>", " ", txt)
    return txt


def _image(path, ext):
    st = ai.status()
    if st["ok"]:
        try:
            text = ai.describe_image(path, ext)
        except Exception as e:  # noqa
            raise ExtractError("Could not read the image with the AI engine: " + ai.friendly(e))
        if text:
            return text
    try:
        import pytesseract
        from PIL import Image
        text = pytesseract.image_to_string(Image.open(path))
        if text.strip():
            return text
    except Exception:
        pass
    why = st["error"] or "the AI engine is not available"
    raise ExtractError(f"Images need the AI engine to be read, but {why}. Fix ANTHROPIC_API_KEY and try again.")


def _transcribe(path):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ExtractError("The file was saved and students can play it, but no summary was made because speech-to-text "
                           "(faster-whisper) is not installed.", soft=True)
    model = WhisperModel(os.environ.get("WHISPER_MODEL", "base"), compute_type="int8")
    segs, _ = model.transcribe(path)
    return " ".join(s.text.strip() for s in segs)


def _video(path):
    if not shutil.which("ffmpeg"):
        raise ExtractError("ffmpeg is not installed, so audio could not be extracted from the video.", soft=True)
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "a.wav")
        r = subprocess.run(["ffmpeg", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", wav], capture_output=True)
        if r.returncode != 0:
            raise ExtractError("This video has no readable audio track, so no summary was made.", soft=True)
        return _transcribe(wav)
