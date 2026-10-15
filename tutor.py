"""AI Tutor agent: teaches, explains, quizzes and converses. Languages: English->English, Telugu->English, Telugu."""
import re
from . import ai

LANGS = {
    "en": ("English → English",
           "Reply in clear, simple English suited to the student's level. If the student's English has mistakes, add one short line "
           "'Better: <corrected sentence>' so they learn."),
    "te_en": ("తెలుగు → English",
              "The student may write in Telugu (తెలుగు), English, or Telugu typed in English letters. First restate their message in "
              "English on one line starting 'In English:' so they learn the phrasing. Then answer in simple English, then add a short "
              "Telugu explanation of the key idea on a line starting 'తెలుగులో:'. Keep technical terms in English with the Telugu "
              "meaning in brackets."),
    "te": ("తెలుగు", "Reply entirely in Telugu (తెలుగు script), keeping technical terms in English in brackets."),
}

SYSTEM = """You are Gnana Tutor, a patient, encouraging teacher and conversation partner for a {level} student called {name}.
Rules:
- Teach step by step with short explanations and one concrete example. End with ONE small question to check understanding.
- When class material is provided, base answers on it. If you go beyond it, say so briefly.
- Help with learning only. If asked something unrelated or unsafe, kindly steer back to studying.
- For graded quiz questions, give hints and guide the student rather than just stating the final answer.
- Be warm, never condescending. Praise effort. Keep replies under 180 words unless asked for more.
- If the student seems stuck on a topic they struggle with, break it into smaller steps.
{weak}
Language instructions: {lang}
{material}"""


def reply(name: str, level: str, message: str, history: list, lang: str, material: dict | None, weak_topics: list[str]) -> str:
    lang = lang if lang in LANGS else "en"
    if ai.enabled():
        mat = ""
        if material:
            mat = f"\nClass material the student is studying — title: {material['title']}\n{material['text'][:20000]}"
        system = SYSTEM.format(level=level, name=name, lang=LANGS[lang][1], material=mat,
                               weak=("The student is weaker in: " + ", ".join(weak_topics) + ".") if weak_topics else "")
        msgs = [{"role": h["role"], "content": h["content"]} for h in history[-12:]
                if h.get("role") in ("user", "assistant") and h.get("content")]
        msgs.append({"role": "user", "content": message})
        out = ai.client().messages.create(model=ai.MODEL, max_tokens=1200, system=system, messages=msgs)
        return "".join(b.text for b in out.content if b.type == "text")
    return _offline(message, lang, material)


def _offline(message, lang, material):
    if lang != "en":
        return "Telugu support needs the AI engine. Ask your admin to set ANTHROPIC_API_KEY. (తెలుగు మద్దతుకు AI ఇంజిన్ అవసరం.)"
    if not material:
        return "Pick a class material above and ask me about it. (Full tutoring needs the AI engine to be enabled.)"
    kws = set(w.lower() for w in re.findall(r"[A-Za-z]{4,}", message)) - ai.STOP
    sents = ai._sentences(material["text"])
    best = sorted(sents, key=lambda s: -len(kws & set(w.lower() for w in re.findall(r"[A-Za-z]{4,}", s))))[:2]
    if best and kws & set(w.lower() for w in re.findall(r"[A-Za-z]{4,}", best[0])):
        return "From your class material: " + " ".join(best) + "\n\nCan you say that in your own words?"
    return "I couldn't find that in this material. Try rephrasing, or ask your teacher."


def summarize_lang(text: str, level: str, lang: str, simple: bool) -> str:
    if not ai.enabled():
        return ""
    target = {"en": "English", "te": "Telugu (తెలుగు script, keep technical terms in English in brackets)",
              "te_en": "English first, then the same summary in Telugu"}.get(lang, "English")
    style = "very simple words and short sentences" if simple else "level-appropriate wording"
    return ai._ask("You summarise teaching material for students.",
                   f"Summarise this for a {level} student in {target}, using {style}. 120-200 words, then 4 bullet key points.\n\n{text[:40000]}", 1500)
