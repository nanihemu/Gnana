"""AI Communicator: daily communication tasks that differ by class level, AI feedback, role-play practice, skill tracking."""
import datetime as dt
import random
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from . import ai
from .auth import require
from .db import get_db
from .models import CommTask, User, Classroom, Enrollment

router = APIRouter(prefix="/api/comm")

# ---------------------------------------------------------------- content per class level
BANK = {
    "primary": dict(secs=30, words=25,
        topics=["your favourite animal", "your best friend", "what you did yesterday", "your favourite food", "your family", "a place you like"],
        writes=["Write 4 sentences about your favourite toy or game.", "Write about your morning using: first, then, after that.",
                "Write a thank-you note to someone who helped you.", "Describe your school bag in 4 sentences."],
        vocab=["happy", "friendly", "delicious", "enormous", "gentle", "brave", "curious", "kind", "careful"]),
    "middle school": dict(secs=45, words=60,
        topics=["a hobby you enjoy and why", "a book or film you recommend", "a time you helped someone", "your ideal weekend",
                "why sleep matters", "a rule you would change at school"],
        writes=["Write a short paragraph about a place you would love to visit.", "Write a message inviting a friend to an event.",
                "Explain how to make your favourite snack, step by step.", "Write a short paragraph: should students wear uniforms?"],
        vocab=["enthusiastic", "reliable", "challenge", "improve", "opinion", "describe", "generous", "patient", "responsible"]),
    "high school": dict(secs=60, words=100,
        topics=["whether social media helps or harms students", "a leader you admire and why", "how to manage exam stress",
                "a problem in your community and a solution", "technology in the classroom", "what you want to do after school"],
        writes=["Write a formal email to your principal requesting a new club.", "Write a persuasive paragraph: homework should be limited.",
                "Write a 120-word statement about your career goals.", "Write the opening of a speech for a school assembly."],
        vocab=["persuade", "significant", "perspective", "consequence", "adapt", "collaborate", "evidence", "ambitious", "resilient"]),
    "undergraduate": dict(secs=90, words=150,
        topics=["a recent news story and your view", "how you handled a team conflict", "your strengths and weaknesses for an internship",
                "AI in your field of study", "a failure you learned from", "an idea you would pitch in 90 seconds"],
        writes=["Write a professional email to a professor asking for a recommendation.", "Write the opening paragraph of an internship cover letter.",
                "Summarise an article you read recently in 100 words.", "Write a LinkedIn 'About' summary."],
        vocab=["articulate", "leverage", "nuance", "initiative", "pragmatic", "collaborate", "insight", "rationale", "stakeholder"]),
    "postgraduate": dict(secs=120, words=200,
        topics=["your research question and why it matters", "your thesis explained to a non-expert", "limitations of your methodology",
                "how your work contributes to society", "responding to critical feedback", "a conference elevator pitch"],
        writes=["Write a 150-word abstract for a study of your choice.", "Write an email to a supervisor proposing a meeting agenda.",
                "Write a rebuttal to a reviewer's criticism.", "Write the opening of a fellowship statement of purpose."],
        vocab=["substantiate", "hypothesis", "corroborate", "ambiguity", "implication", "rigorous", "synthesise", "paradigm", "empirical"]),
    "professional": dict(secs=90, words=150,
        topics=["a 60-second project status update", "pitching a product to a sceptical client", "giving constructive feedback to a colleague",
                "negotiating a deadline extension", "introducing yourself at a networking event", "explaining a complex idea to a non-technical stakeholder"],
        writes=["Write a concise status email with risks and next steps.", "Write a polite but firm follow-up on an unpaid invoice.",
                "Write a meeting summary with action items.", "Write a message declining a request while offering an alternative."],
        vocab=["align", "prioritise", "deliverable", "escalate", "mitigate", "bandwidth", "scalable", "actionable", "consensus"]),
}

SCENARIOS = {
    "primary": [("friend", "Meet a new friend", "a friendly classmate meeting the student for the first time"),
                ("canteen", "Order food at the canteen", "a canteen helper taking the student's order"),
                ("weekend", "Tell your teacher about your weekend", "a kind teacher asking about the student's weekend")],
    "middle school": [("library", "Ask the librarian for help", "a helpful school librarian"),
                      ("hobby", "Explain your hobby to a classmate", "a curious classmate who knows nothing about the hobby"),
                      ("sorry", "Apologise to a friend", "a friend who is a little upset about something the student did")],
    "high school": [("council", "School council Q&A", "a student panel asking tough but fair questions to a council candidate"),
                    ("admission", "College admission interview", "a friendly college admissions interviewer"),
                    ("debate", "Debate: homework should be limited", "a debate opponent who disagrees politely")],
    "undergraduate": [("internship", "Internship interview", "a hiring manager interviewing for an internship"),
                      ("viva", "Project viva", "an examiner asking about the student's project"),
                      ("network", "Networking with a professional", "an industry professional at a networking event")],
    "postgraduate": [("conference", "Conference Q&A", "a researcher asking questions after the student's talk"),
                     ("supervisor", "Supervisor meeting", "a thesis supervisor reviewing progress"),
                     ("fellowship", "Fellowship interview", "a fellowship panel member")],
    "professional": [("client", "Client negotiation", "a client negotiating scope and price"),
                     ("standup", "Team stand-up update", "a team lead asking for a concise update"),
                     ("salary", "Salary discussion", "a manager in a compensation review")],
}

FILLERS = ["um", "uh", "like", "you know", "basically", "actually", "i mean", "sort of", "kind of"]
CRITERIA = ["clarity", "grammar", "vocabulary", "structure"]


def band(level: str) -> str:
    return level if level in BANK else "high school"


# ---------------------------------------------------------------- daily tasks
def _today() -> str:
    return dt.date.today().isoformat()


def ensure_daily(db: Session, user: User) -> list[CommTask]:
    day = _today()
    tasks = db.query(CommTask).filter_by(student_id=user.id, day=day).order_by(CommTask.id).all()
    if not any(t.source == "auto" for t in tasks):
        b = BANK[band(user.level)]
        rng = random.Random(f"{user.id}-{day}")
        topic = rng.choice(b["topics"])
        words = rng.sample(b["vocab"], 3)
        specs = [
            ("speak", f"Speak: {topic}", f"Speak for about {b['secs']} seconds on: {topic}. Open clearly, give one example, finish with a closing sentence.",
             {"seconds": b["secs"], "min_words": b["words"]}),
            ("write", "Write", rng.choice(b["writes"]) + f" Aim for at least {b['words']} words.", {"min_words": b["words"]}),
            ("vocab", "Word power", f"Use each word in a sentence of your own, then join them in a short paragraph: {', '.join(words)}.",
             {"words": words, "min_words": max(15, b["words"] // 2)}),
        ]
        for skill, title, prompt, target in specs:
            db.add(CommTask(student_id=user.id, day=day, level=band(user.level), skill=skill, title=title, prompt=prompt, target=target))
        db.commit()
        tasks = db.query(CommTask).filter_by(student_id=user.id, day=day).order_by(CommTask.id).all()
    return tasks


def task_out(t: CommTask) -> dict:
    return {"id": t.id, "day": t.day, "skill": t.skill, "title": t.title, "prompt": t.prompt, "target": t.target, "status": t.status,
            "source": t.source, "level": t.level, "scores": t.scores, "feedback": t.feedback, "xp": t.xp, "response": t.response}


# ---------------------------------------------------------------- evaluation
def metrics(text: str, seconds: int) -> dict:
    words = re.findall(r"[A-Za-z']+", text)
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    fill = sum(len(re.findall(rf"\b{re.escape(f)}\b", low)) for f in FILLERS)
    sents = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    m = {"words": len(words), "sentences": len(sents), "fillers": fill,
         "unique_ratio": round(len({w.lower() for w in words}) / max(len(words), 1), 2),
         "avg_sentence_len": round(len(words) / max(len(sents), 1), 1)}
    if seconds > 0:
        m["wpm"] = round(len(words) / seconds * 60)
    return m


def evaluate(task: CommTask, text: str, seconds: int, tele: bool) -> dict:
    m = metrics(text, seconds if task.skill == "speak" else 0)
    if ai.enabled():
        try:
            extra = ' Also include "fluency" (1-5, judged from fillers, pace and flow) in scores.' if task.skill == "speak" else ""
            tel = ' Also include "telugu_note": a short Telugu (తెలుగు) explanation of the main feedback.' if tele else ""
            r = ai._json(
                f"You are a warm, encouraging communication coach for a {task.level} student. Judge against {task.level}-level expectations. "
                "The text may be a speech transcript (no punctuation guarantees; do not penalise missing punctuation for speech). "
                'Return JSON: {"scores": {"clarity":1-5,"grammar":1-5,"vocabulary":1-5,"structure":1-5}, "strengths":[2 short strings], '
                '"improvements":[{"issue":str,"fix":str} (2-3)], "improved_version": str (a better version of THEIR text, same meaning, same level), '
                '"tip": str (one practical tip for tomorrow)}.' + extra + tel,
                f"Task: {task.prompt}\nStudent response ({seconds}s, metrics {m}):\n{text[:6000]}", 1800)
            r["metrics"] = m
            return r
        except Exception:
            pass
    return _offline_eval(task, text, m)


def _offline_eval(task, text, m):
    tgt = task.target.get("min_words", 20)
    clarity = 4 if 6 <= m["avg_sentence_len"] <= 22 else 3 if m["avg_sentence_len"] <= 30 else 2
    vocab = 5 if m["unique_ratio"] > 0.75 else 4 if m["unique_ratio"] > 0.6 else 3 if m["unique_ratio"] > 0.45 else 2
    structure = 4 if m["sentences"] >= 3 and m["words"] >= tgt else 3 if m["sentences"] >= 2 else 2
    scores = {"clarity": clarity, "grammar": 3, "vocabulary": vocab, "structure": structure}
    if task.skill == "speak":
        scores["fluency"] = 4 if m["fillers"] <= 1 else 3 if m["fillers"] <= 4 else 2
    strengths, imp = [], []
    if m["words"] >= tgt:
        strengths.append(f"You reached the target of {tgt} words.")
    if m["unique_ratio"] > 0.6:
        strengths.append("Good variety of words, with little repetition.")
    if not strengths:
        strengths.append("You completed the task. Showing up every day is what builds skill.")
    if m["words"] < tgt:
        imp.append({"issue": f"Only {m['words']} words (target {tgt}).", "fix": "Add an example or a reason to each main point."})
    if m["fillers"] > 1:
        imp.append({"issue": f"{m['fillers']} filler words (um, like, you know…).", "fix": "Pause silently instead of using a filler."})
    if m["avg_sentence_len"] > 25:
        imp.append({"issue": "Very long sentences.", "fix": "Split them into two shorter sentences."})
    if m.get("wpm") and (m["wpm"] > 170 or m["wpm"] < 90):
        imp.append({"issue": f"Pace was {m['wpm']} words/min.", "fix": "Aim for about 110–150 words per minute."})
    if not imp:
        imp.append({"issue": "Nothing major from the basic checks.", "fix": "Try adding a stronger opening line."})
    return {"scores": scores, "strengths": strengths[:2], "improvements": imp[:3], "improved_version": "",
            "tip": "Enable the AI engine for grammar corrections and a rewritten model answer.", "metrics": m, "offline": True}


class SubmitIn(BaseModel):
    response: str
    seconds: int = 0
    tele: bool = False  # explain feedback in Telugu as well


@router.get("/today")
def today(db: Session = Depends(get_db), u: User = Depends(require("student", "teacher", "admin"))):
    tasks = ensure_daily(db, u)
    return {"day": _today(), "level": band(u.level), "tasks": [task_out(t) for t in tasks], "summary": summary(db, u.id)}


@router.post("/tasks/{tid}/submit")
def submit(tid: int, body: SubmitIn, db: Session = Depends(get_db), u: User = Depends(require("student", "teacher", "admin"))):
    t = db.get(CommTask, tid)
    if not t or t.student_id != u.id:
        raise HTTPException(404, "Task not found")
    if t.status == "done":
        raise HTTPException(409, "Already completed. Come back for tomorrow's tasks.")
    text = body.response.strip()
    if len(re.findall(r"\w+", text)) < 3:
        raise HTTPException(400, "Write or speak a little more first")
    fb = evaluate(t, text[:6000], max(0, min(body.seconds, 1800)), body.tele)
    sc = {k: max(1, min(5, int(v))) for k, v in fb.get("scores", {}).items()}
    avg = sum(sc.values()) / max(len(sc), 1)
    met = fb.get("metrics", {}).get("words", 0) >= t.target.get("min_words", 0)
    t.status, t.response, t.seconds, t.scores, t.feedback = "done", text, body.seconds, sc, fb
    t.xp = round(avg * 10) + (5 if met else 0)
    t.completed_at = dt.datetime.utcnow()
    db.commit()
    return {"task": task_out(t), "summary": summary(db, u.id)}


# ---------------------------------------------------------------- teacher assignment
class AssignIn(BaseModel):
    classroom_id: int
    title: str
    prompt: str
    skill: str = "speak"
    min_words: int = 50


@router.post("/assign")
def assign(body: AssignIn, db: Session = Depends(get_db), u: User = Depends(require("teacher", "admin"))):
    c = db.get(Classroom, body.classroom_id)
    if not c or (u.role == "teacher" and c.teacher_id != u.id):
        raise HTTPException(404, "Class not found")
    if body.skill not in ("speak", "write", "vocab"):
        raise HTTPException(400, "skill must be speak, write or vocab")
    n = 0
    for e in db.query(Enrollment).filter_by(classroom_id=c.id):
        s = db.get(User, e.student_id)
        db.add(CommTask(student_id=s.id, day=_today(), level=band(s.level), skill=body.skill, source="teacher", title=body.title[:200],
                        prompt=body.prompt, target={"min_words": body.min_words}))
        n += 1
    db.commit()
    return {"assigned_to": n}


# ---------------------------------------------------------------- progress
def summary(db: Session, sid: int) -> dict:
    done = db.query(CommTask).filter_by(student_id=sid, status="done").order_by(CommTask.day).all()
    by_day, per_skill, per_crit = {}, {}, {}
    for t in done:
        avg = sum(t.scores.values()) / max(len(t.scores), 1)
        by_day.setdefault(t.day, []).append(avg)
        per_skill.setdefault(t.skill, []).append(avg)
        for k, v in t.scores.items():
            per_crit.setdefault(k, []).append(v)
    days = set(by_day)
    d, streak = dt.date.today(), 0
    if d.isoformat() not in days:
        d -= dt.timedelta(days=1)
    while d.isoformat() in days:
        streak += 1
        d -= dt.timedelta(days=1)
    pct = lambda xs: round(100 * (sum(xs) / len(xs)) / 5)  # noqa
    today_tasks = db.query(CommTask).filter_by(student_id=sid, day=_today()).all()
    crit = {k: pct(v) for k, v in per_crit.items()}
    weakest = min(crit, key=crit.get) if crit else None
    return {"streak": streak, "xp": sum(t.xp for t in done), "completed": len(done),
            "today_done": sum(t.status == "done" for t in today_tasks), "today_total": len(today_tasks),
            "skills": {k: pct(v) for k, v in per_skill.items()}, "criteria": crit, "focus": weakest,
            "daily": [{"day": k, "pct": pct(v)} for k, v in sorted(by_day.items())][-14:]}


@router.get("/progress")
def my_progress(db: Session = Depends(get_db), u: User = Depends(require("student", "teacher", "admin"))):
    return summary(db, u.id)


# ---------------------------------------------------------------- role-play conversation partner
@router.get("/scenarios")
def scenarios(u: User = Depends(require("student", "teacher", "admin"))):
    return [{"id": i, "title": t} for i, t, _ in SCENARIOS[band(u.level)]]


class ChatIn(BaseModel):
    scenario_id: str
    message: str = ""
    history: list[dict] = []
    tele: bool = False


@router.post("/chat")
def chat(body: ChatIn, u: User = Depends(require("student", "teacher", "admin"))):
    sc = next((s for s in SCENARIOS[band(u.level)] if s[0] == body.scenario_id), None)
    if not sc:
        raise HTTPException(404, "Scenario not found")
    first = not body.history and not body.message.strip()
    if ai.enabled():
        system = (
            f"You are role-playing: {sc[2]}. The learner is a {band(u.level)} student named {u.name} practising spoken English communication. "
            f"Stay in character, speak naturally at {band(u.level)} level, keep each turn to 1–3 sentences, and always end with a question or prompt "
            "so the learner keeps talking. After your in-character reply, add a new line starting 'Coach:' with ONE specific, kind improvement for the "
            "learner's last message (a corrected sentence or a better phrase), or praise if it was strong. "
            + ("In the Coach line, also add a very short Telugu (తెలుగు) explanation. " if body.tele else "")
            + ("Begin the role-play now with your opening line (no Coach line yet)." if first else ""))
        msgs = [{"role": h["role"], "content": h["content"]} for h in body.history[-14:] if h.get("role") in ("user", "assistant") and h.get("content")]
        msgs.append({"role": "user", "content": body.message.strip() or "Hello"})
        try:
            out = ai.client().messages.create(model=ai.MODEL, max_tokens=500, system=system, messages=msgs)
            return {"reply": "".join(b.text for b in out.content if b.type == "text")}
        except Exception as e:  # noqa
            raise HTTPException(502, "Partner unavailable: " + str(e)[:200])
    if first:
        return {"reply": f"[{sc[1]}] Hello! Let's practise. Tell me a little about yourself."}
    m = metrics(body.message, 0)
    tip = "Try a longer answer with one example." if m["words"] < 12 else "Nice length. Add a reason using 'because'."
    return {"reply": f"Interesting! Can you tell me more?\nCoach: {tip} (Full role-play needs the AI engine.)"}
