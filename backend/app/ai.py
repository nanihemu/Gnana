"""AI layer. Uses Claude when ANTHROPIC_API_KEY is set; otherwise a heuristic fallback keeps the app usable offline."""
import base64
import json
import os
import re
import random
from collections import Counter

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
_client = None


def _key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "").strip().strip('"').strip("'")


def configured() -> bool:
    k = _key()
    return bool(k) and "your-key-here" not in k


def client():
    global _client
    if _client is None and configured():
        import anthropic
        _client = anthropic.Anthropic(api_key=_key())
    return _client


def friendly(e: Exception) -> str:
    s = str(e)
    low = s.lower()
    if "401" in s or "authentication" in low or "invalid x-api-key" in low:
        return "the Anthropic API key was rejected (invalid). Check ANTHROPIC_API_KEY in .env"
    if "credit balance" in low or "billing" in low:
        return "the Anthropic account has no credit left"
    if "429" in s or "rate" in low and "limit" in low:
        return "the AI service is rate-limited right now, try again shortly"
    if "404" in s and "model" in low:
        return f"the model '{MODEL}' was not found. Set ANTHROPIC_MODEL in .env to a model your key can use"
    return s[:200]


_st = {"t": 0.0, "ok": False, "error": ""}


def status(force: bool = False) -> dict:
    """Cached health check of the AI engine: {configured, ok, error}."""
    import time
    if not configured():
        return {"configured": False, "ok": False, "error": "ANTHROPIC_API_KEY is not set"}
    ttl = 600 if _st["ok"] else 30
    if force or time.time() - _st["t"] > ttl:
        try:
            client().messages.create(model=MODEL, max_tokens=5, messages=[{"role": "user", "content": "hi"}])
            _st.update(ok=True, error="")
        except Exception as e:  # noqa
            _st.update(ok=False, error=friendly(e))
        _st["t"] = time.time()
    return {"configured": True, "ok": _st["ok"], "error": _st["error"]}


def enabled() -> bool:
    return status()["ok"]


def _ask(system: str, user, max_tokens=4000) -> str:
    msg = client().messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                   messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in msg.content if b.type == "text")


def _json(system: str, user, max_tokens=4000):
    out = _ask(system + "\nRespond with ONLY valid JSON, no markdown fences.", user, max_tokens)
    out = out.strip()
    out = re.sub(r"^```(?:json)?|```$", "", out, flags=re.M).strip()
    return json.loads(out)


def describe_image(path, ext):
    if not enabled():
        return ""
    media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}.get(ext)
    if not media:
        return ""
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}},
        {"type": "text", "text": "Transcribe all text in this image and describe diagrams, charts or figures in detail so a teacher could build a lesson from it."},
    ]
    return _ask("You extract learning content from images.", content, 2000)


# ---------- helpers for offline fallback ----------
STOP = set("the a an and or of to in is are was were be been it that this for on with as by at from which their his her its not but have has had they them we you i can will would should may might also than then there these those such into over under more most other some any".split())


def _sentences(text):
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 30]


def _keywords(text, n=8):
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text)]
    c = Counter(w for w in words if w not in STOP)
    return [w for w, _ in c.most_common(n)]


# ---------- public API ----------
def analyze(text: str, level: str, title: str = "") -> dict:
    text = text.strip()
    err = ""
    if enabled() and text:
        try:
            return _json(
                "You are an expert teacher. Analyse learning material for a student at level: " + level +
                ". Return JSON: {\"title\": str, \"summary\": str (150-250 words, level-appropriate), "
                "\"key_points\": [str] (5-8), \"topics\": [str] (2-6 short topic tags)}.",
                text[:60000])
        except Exception as e:  # noqa
            err = friendly(e)
    sents = _sentences(text)
    kws = _keywords(text)
    scored = sorted(sents, key=lambda s: -sum(k in s.lower() for k in kws))[:5]
    ordered = [s for s in sents if s in scored]
    out = {"title": title or (sents[0][:60] if sents else "Untitled"),
           "summary": " ".join(ordered) or text[:600],
           "key_points": ordered or ([text[:200]] if text else []),
           "topics": kws[:5] or ["general"]}
    if err:
        out["_fallback"] = err
    return out


def make_questions(text: str, level: str, n: int, mix: list[str], topics: list[str]) -> list[dict]:
    if enabled():
        try:
            qs = _json(
                f"You are an expert assessment writer for students at level: {level}. Create {n} questions from the material. "
                f"Allowed types: {mix} (mcq = 4 options, tf = true/false, short = short written answer). "
                "Return JSON list of objects: {\"type\": str, \"topic\": str (one of or close to " + str(topics) +
                "), \"question\": str, \"options\": [str] (mcq only), \"answer\": str (for mcq the exact option text; for tf 'True' or 'False'), "
                "\"explanation\": str}. Vary difficulty.", text[:60000], 6000)
            return _finalize(qs)
        except Exception:
            pass
    return _finalize(_fallback_questions(text, n, topics))


def _finalize(qs):
    for i, q in enumerate(qs):
        q["id"] = i + 1
        q.setdefault("options", [])
        q.setdefault("explanation", "")
        q.setdefault("topic", "general")
    return qs


def _fallback_questions(text, n, topics):
    sents = _sentences(text)
    random.shuffle(sents)
    allkw = _keywords(text, 30)
    qs = []
    for s in sents:
        if len(qs) >= n:
            break
        words = re.findall(r"[A-Za-z][A-Za-z\-]{4,}", s)
        cand = [w for w in words if w.lower() not in STOP]
        if not cand:
            continue
        ans = max(cand, key=lambda w: allkw.index(w.lower()) * -1 if w.lower() in allkw else -99)
        blank = re.sub(re.escape(ans), "_____", s, count=1, flags=re.I)
        topic = next((t for t in topics if t.lower() in s.lower()), topics[0] if topics else "general")
        if len(qs) % 3 == 2:
            qs.append({"type": "tf", "topic": topic, "question": "True or false: " + s, "answer": "True",
                       "options": ["True", "False"], "explanation": "Stated in the material."})
            continue
        distract = [w for w in allkw if w != ans.lower()][:20]
        random.shuffle(distract)
        opts = [ans] + [d for d in distract[:3]]
        random.shuffle(opts)
        qs.append({"type": "mcq", "topic": topic, "question": "Fill in the blank: " + blank, "options": opts,
                   "answer": ans, "explanation": "Original sentence: " + s})
    return qs


def grade_short(question: str, expected: str, given: str) -> tuple[float, str]:
    given = (given or "").strip()
    if not given:
        return 0.0, "No answer given."
    if enabled():
        try:
            r = _json("Grade a student's short answer. Return {\"score\": number 0..1, \"comment\": str (one sentence)}.",
                      f"Question: {question}\nExpected: {expected}\nStudent: {given}", 300)
            return float(r["score"]), r.get("comment", "")
        except Exception:
            pass
    exp = set(_keywords(expected, 10)) or set(expected.lower().split())
    got = set(w.lower() for w in re.findall(r"[A-Za-z]+", given))
    overlap = len(exp & got) / max(len(exp), 1)
    return round(min(1.0, overlap * 1.3), 2), "Graded by keyword match (enable AI for richer grading)."


def video_script(material_text: str, summary: str, key_points: list, level: str, title: str) -> list[dict]:
    """List of slides: {title, bullets, narration}."""
    if enabled():
        try:
            slides = _json(
                f"Write an engaging explainer video script for students at level: {level}. 5-8 slides. "
                "Return JSON list of {\"title\": str, \"bullets\": [str] (max 4, short), \"narration\": str (2-4 spoken sentences)}. "
                "First slide is an intro, last is a recap.", f"Title: {title}\n\n{material_text[:30000]}", 4000)
            return slides
        except Exception:
            pass
    slides = [{"title": title, "bullets": [], "narration": f"Welcome. In this lesson we will cover {title}."}]
    for i, kp in enumerate(key_points[:6], 1):
        slides.append({"title": f"Key idea {i}", "bullets": [kp[:110]], "narration": kp})
    slides.append({"title": "Recap", "bullets": [k[:70] for k in key_points[:3]], "narration": "Let's recap. " + summary[:300]})
    return slides


def student_feedback(name: str, level: str, stats: dict) -> str:
    if enabled():
        try:
            return _ask("You are a supportive tutor writing short feedback (120-180 words) for a student, in plain text, "
                        "addressed in third person for parents/teachers but encouraging. Cover strengths, weak areas with concrete next steps, "
                        "and trend. Do not invent data.", f"Student: {name} ({level})\nStats JSON: {json.dumps(stats)}", 600)
        except Exception:
            pass
    s = [f"{name} has completed {stats['attempts']} attempt(s) with an overall average of {stats['average']}%."]
    if stats["strengths"]:
        s.append("Strong topics: " + ", ".join(t["topic"] for t in stats["strengths"]) + ".")
    if stats["weaknesses"]:
        s.append("Needs practice in: " + ", ".join(t["topic"] for t in stats["weaknesses"]) + ". Revisit the summaries and retake quizzes on these topics.")
    s.append(f"Trend: {stats['trend']}.")
    return " ".join(s)
