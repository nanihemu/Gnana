"""Render an explainer video: slide images (Pillow) + narration (gTTS, silent fallback) stitched with ffmpeg."""
import os
import shutil
import subprocess
import tempfile
import textwrap
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720


def _font(size, bold=False):
    for name in (["DejaVuSans-Bold.ttf", "arialbd.ttf"] if bold else ["DejaVuSans.ttf", "arial.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_slide(slide, idx, total, path):
    accent = slide.get("accent", "#3b5bdb")
    img = Image.new("RGB", (W, H), "#f6f8fc")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=accent)
    if slide.get("caption"):  # burned-in subtitle so the video works muted
        d.rectangle([0, H - 130, W, H], fill="#1b2559")
        d.text((60, H - 115), "\n".join(textwrap.wrap(slide["narration"], 72)[:3]), font=_font(26), fill="#ffffff", spacing=6)
    d.text((70, 70), "\n".join(textwrap.wrap(slide["title"], 36)[:2]), font=_font(54, True), fill="#1b2559")
    y = 230
    for b in slide.get("bullets", [])[:4]:
        lines = textwrap.wrap(b, 62)[:3]
        d.ellipse([74, y + 14, 90, y + 30], fill=accent)
        d.text((110, y), "\n".join(lines), font=_font(34), fill="#2b3674", spacing=8)
        y += 48 * len(lines) + 30
    d.text((W - 150, H - 50), f"{idx}/{total}", font=_font(24), fill="#8a94b8")
    img.save(path)


def _tts(text, out_mp3, timeout=25):
    """Narration via gTTS (needs internet). Falls back to silence on any failure or hang."""
    import concurrent.futures as cf
    if os.environ.get("GNANA_TTS", "on") == "off":  # used by tests / offline servers
        return False
    def run():
        from gtts import gTTS
        gTTS(text=text, lang="en").save(out_mp3)
    ex = cf.ThreadPoolExecutor(max_workers=1)
    try:
        ex.submit(run).result(timeout=timeout)
        return os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 0
    except Exception:
        return False
    finally:
        ex.shutdown(wait=False)


def build_video(slides, out_path):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is not installed")
    with tempfile.TemporaryDirectory() as td:
        clips = []
        for i, s in enumerate(slides, 1):
            png = os.path.join(td, f"s{i}.png")
            mp3 = os.path.join(td, f"s{i}.mp3")
            clip = os.path.join(td, f"c{i}.mp4")
            render_slide(s, i, len(slides), png)
            narr = s.get("narration") or s["title"]
            if _tts(narr, mp3):
                audio = ["-i", mp3]
            else:  # silent track sized by word count (~2.5 words/sec)
                secs = max(7, int(len(narr.split()) / 2.2))
                audio = ["-f", "lavfi", "-t", str(secs), "-i", "anullsrc=r=44100:cl=mono"]
            cmd = ["ffmpeg", "-y", "-loop", "1", "-i", png, *audio, "-c:v", "libx264", "-tune", "stillimage",
                   "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",  # same audio format for every clip so concat works
                   "-pix_fmt", "yuv420p", "-r", "24", "-shortest", clip]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode != 0:
                raise RuntimeError(r.stderr.decode()[-400:])
            clips.append(clip)
        lst = os.path.join(td, "list.txt")
        with open(lst, "w") as f:
            f.writelines(f"file '{c}'\n" for c in clips)
        r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out_path], capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.decode()[-400:])
