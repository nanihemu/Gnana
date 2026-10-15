import os
import shutil
import threading
import uuid
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import ai, comm, extract, tutor, video as videomod
from .analytics import student_stats
from .auth import hash_pw, check_pw, make_token, current_user, require, can_view_student
from .db import Base, engine, get_db, SessionLocal, DATA_DIR
from .models import User, Classroom, Enrollment, ParentLink, Material, Quiz, Attempt, Feedback

Base.metadata.create_all(engine)
app = FastAPI(title="Gnana")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(comm.router)

ROLES = {"student", "teacher", "parent", "admin"}


def user_out(u: User):
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "level": u.level}


# ---------------- auth ----------------
class RegisterIn(BaseModel):
    name: str
    email: str
    password: str
    role: str = "student"
    level: str = "high school"


class LoginIn(BaseModel):
    email: str
    password: str


@app.post("/api/auth/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if body.role not in ROLES:
        raise HTTPException(400, "Bad role")
    first_user = db.query(User).count() == 0
    # Only the very first account may self-register as admin; others cannot.
    if body.role == "admin" and not first_user:
        raise HTTPException(403, "Admins must be created by an existing admin")
    if db.query(User).filter_by(email=body.email.lower()).first():
        raise HTTPException(400, "Email already registered")
    u = User(name=body.name, email=body.email.lower(), password_hash=hash_pw(body.password), role=body.role, level=body.level)
    db.add(u); db.commit()
    return {"token": make_token(u), "user": user_out(u)}


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=body.email.lower()).first()
    if not u or not check_pw(body.password, u.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return {"token": make_token(u), "user": user_out(u)}


@app.get("/api/me")
def me(u: User = Depends(current_user)):
    st = ai.status()
    return {**user_out(u), "ai_enabled": st["ok"], "ai_error": st["error"]}


@app.get("/api/health")
def health():
    """Public status check: AI key, ffmpeg and storage. Open http://SERVER:8000/api/health to debug a deployment."""
    import shutil as sh
    st = ai.status()
    try:
        probe = os.path.join(DATA_DIR, ".probe")
        open(probe, "w").write("x"); os.remove(probe)
        writable = True
    except Exception:
        writable = False
    return {"ok": True, "ai": {"configured": st["configured"], "working": st["ok"], "error": st["error"], "model": ai.MODEL},
            "ffmpeg": bool(sh.which("ffmpeg")), "data_dir_writable": writable}


# ---------------- admin ----------------
@app.get("/api/admin/users")
def admin_users(db: Session = Depends(get_db), _: User = Depends(require("admin"))):
    return [user_out(u) for u in db.query(User).order_by(User.id)]


class UserIn(BaseModel):
    name: str
    email: str
    password: str
    role: str
    level: str = "high school"


@app.post("/api/admin/users")
def admin_create_user(body: UserIn, db: Session = Depends(get_db), _: User = Depends(require("admin"))):
    if body.role not in ROLES:
        raise HTTPException(400, "Bad role")
    if db.query(User).filter_by(email=body.email.lower()).first():
        raise HTTPException(400, "Email already registered")
    u = User(name=body.name, email=body.email.lower(), password_hash=hash_pw(body.password), role=body.role, level=body.level)
    db.add(u); db.commit()
    return user_out(u)


@app.delete("/api/admin/users/{uid}")
def admin_delete_user(uid: int, db: Session = Depends(get_db), me: User = Depends(require("admin"))):
    if uid == me.id:
        raise HTTPException(400, "Cannot delete yourself")
    u = db.get(User, uid)
    if u:
        db.query(Enrollment).filter_by(student_id=uid).delete()
        db.query(ParentLink).filter((ParentLink.parent_id == uid) | (ParentLink.student_id == uid)).delete()
        db.delete(u); db.commit()
    return {"ok": True}


class LinkIn(BaseModel):
    parent_email: str
    student_email: str


@app.post("/api/admin/parent-links")
def link_parent(body: LinkIn, db: Session = Depends(get_db), _: User = Depends(require("admin", "teacher"))):
    p = db.query(User).filter_by(email=body.parent_email.lower(), role="parent").first()
    s = db.query(User).filter_by(email=body.student_email.lower(), role="student").first()
    if not p or not s:
        raise HTTPException(404, "Parent or student not found")
    if not db.query(ParentLink).filter_by(parent_id=p.id, student_id=s.id).first():
        db.add(ParentLink(parent_id=p.id, student_id=s.id)); db.commit()
    return {"ok": True}


@app.get("/api/admin/overview")
def admin_overview(db: Session = Depends(get_db), _: User = Depends(require("admin"))):
    counts = {r: db.query(User).filter_by(role=r).count() for r in ROLES}
    attempts = db.query(Attempt).all()
    avg = round(100 * sum(a.score for a in attempts) / max(sum(a.total for a in attempts), 1))
    return {"users": counts, "materials": db.query(Material).count(), "quizzes": db.query(Quiz).count(),
            "attempts": len(attempts), "average": avg, "ai_enabled": ai.status()["ok"], "ai_error": ai.status()["error"]}


# ---------------- classrooms ----------------
class ClassIn(BaseModel):
    name: str


@app.post("/api/classrooms")
def create_class(body: ClassIn, db: Session = Depends(get_db), u: User = Depends(require("teacher", "admin"))):
    c = Classroom(name=body.name, teacher_id=u.id)
    db.add(c); db.commit()
    return {"id": c.id, "name": c.name}


def _class_out(db, c):
    ids = [e.student_id for e in db.query(Enrollment).filter_by(classroom_id=c.id)]
    studs = [user_out(db.get(User, i)) for i in ids]
    return {"id": c.id, "name": c.name, "teacher_id": c.teacher_id, "students": studs}


@app.get("/api/classrooms")
def list_classes(db: Session = Depends(get_db), u: User = Depends(current_user)):
    if u.role == "teacher":
        cs = db.query(Classroom).filter_by(teacher_id=u.id).all()
    elif u.role == "admin":
        cs = db.query(Classroom).all()
    elif u.role == "student":
        cs = [db.get(Classroom, e.classroom_id) for e in db.query(Enrollment).filter_by(student_id=u.id)]
    else:
        return []
    return [_class_out(db, c) for c in cs]


class EnrollIn(BaseModel):
    student_email: str


@app.post("/api/classrooms/{cid}/students")
def enroll(cid: int, body: EnrollIn, db: Session = Depends(get_db), u: User = Depends(require("teacher", "admin"))):
    c = db.get(Classroom, cid)
    if not c or (u.role == "teacher" and c.teacher_id != u.id):
        raise HTTPException(404, "Class not found")
    s = db.query(User).filter_by(email=body.student_email.lower(), role="student").first()
    if not s:
        raise HTTPException(404, "No student with that email")
    if not db.query(Enrollment).filter_by(classroom_id=cid, student_id=s.id).first():
        db.add(Enrollment(classroom_id=cid, student_id=s.id)); db.commit()
    return _class_out(db, c)


@app.get("/api/classrooms/{cid}/progress")
def class_progress(cid: int, db: Session = Depends(get_db), u: User = Depends(require("teacher", "admin"))):
    c = db.get(Classroom, cid)
    if not c or (u.role == "teacher" and c.teacher_id != u.id):
        raise HTTPException(404, "Class not found")
    out = []
    for e in db.query(Enrollment).filter_by(classroom_id=cid):
        s = db.get(User, e.student_id)
        st = student_stats(db, s.id)
        out.append({"student": user_out(s), "attempts": st["attempts"], "average": st["average"], "trend": st["trend"],
                    "weaknesses": [w["topic"] for w in st["weaknesses"]], "strengths": [w["topic"] for w in st["strengths"]]})
    return out


# ---------------- materials ----------------
def _visible_materials(db, u):
    q = db.query(Material)
    if u.role == "admin":
        return q.order_by(Material.id.desc()).all()
    if u.role == "teacher":
        return q.filter_by(owner_id=u.id).order_by(Material.id.desc()).all()
    if u.role == "student":
        cids = [e.classroom_id for e in db.query(Enrollment).filter_by(student_id=u.id)]
        # Students only see what their teachers posted to classes they are enrolled in.
        return [m for m in q.order_by(Material.id.desc()) if m.classroom_id in cids]
    return []


def mat_out(m: Material, full=False, db: Session | None = None):
    teacher = db.get(User, m.owner_id) if db else None
    d = {"id": m.id, "title": m.title, "kind": m.kind, "level": m.level, "summary": m.summary, "key_points": m.key_points,
         "topics": m.topics, "video_status": m.video_status, "video_error": m.video_error, "classroom_id": m.classroom_id,
         "created_at": m.created_at.isoformat(), "filename": m.filename, "has_file": bool(m.file_path),
         "posted_by": teacher.name if teacher else ""}
    cl = db.get(Classroom, m.classroom_id) if (db and m.classroom_id) else None
    d["class_name"] = cl.name if cl else ""
    if full:
        d["text"] = m.text[:20000]
    return d


def _get_material(db, u, mid):
    m = db.get(Material, mid)
    if not m or m not in _visible_materials(db, u):
        raise HTTPException(404, "Material not found")
    return m


@app.post("/api/materials")
async def upload_material(title: str = Form(""), text: str = Form(""), level: Optional[str] = Form(None),
                          classroom_id: Optional[int] = Form(None), file: Optional[UploadFile] = File(None),
                          db: Session = Depends(get_db), u: User = Depends(require("teacher", "admin"))):
    if not file and not text.strip():
        raise HTTPException(400, "Provide a file or some text")
    if classroom_id:
        c = db.get(Classroom, classroom_id)
        if not c or (u.role == "teacher" and c.teacher_id != u.id):
            raise HTTPException(403, "Cannot post to that class")
    kind, filename, body, path, warning = "text", "", text, "", ""
    if file and file.filename:
        filename = os.path.basename(file.filename)
        path = os.path.join(DATA_DIR, "uploads", f"{uuid.uuid4().hex}_{filename}")
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        try:
            kind, extracted = extract.extract_text(path, filename)
        except extract.ExtractError as e:
            kind = extract.detect_kind(filename)
            if not e.soft and not text.strip():  # unreadable and nothing else to learn from: don't save junk
                os.remove(path)
                raise HTTPException(422, str(e))
            extracted, warning = "", str(e)
        body = (text + "\n" + extracted).strip()
    lvl = level or u.level
    a = ai.analyze(body, lvl, title) if body else {"summary": warning, "key_points": [], "topics": []}
    if a.get("_fallback"):
        warning = (warning + " " if warning else "") + f"AI summary unavailable ({a['_fallback']}); a basic summary was used."
    m = Material(owner_id=u.id, classroom_id=classroom_id, title=title or filename or a.get("title") or "Untitled",
                 filename=filename, kind=kind, level=lvl, text=body, summary=a.get("summary", ""),
                 key_points=a.get("key_points", []), topics=a.get("topics", []), file_path=path)
    db.add(m); db.commit()
    out = mat_out(m, True, db)
    out["warning"] = warning
    return out


@app.get("/api/materials")
def list_materials(db: Session = Depends(get_db), u: User = Depends(current_user)):
    return [mat_out(m, db=db) for m in _visible_materials(db, u)]


@app.get("/api/materials/{mid}")
def get_material(mid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    d = mat_out(_get_material(db, u, mid), True, db)
    if u.role == "student":
        d.pop("text", None)  # students get summary/notes, not the raw extracted text
    return d


def _user_from_token(db, token):
    import jwt as _jwt
    from .auth import SECRET
    try:
        return db.get(User, int(_jwt.decode(token, SECRET, algorithms=["HS256"])["sub"]))
    except Exception:
        raise HTTPException(401, "Invalid token")


@app.get("/api/materials/{mid}/file")
def get_original_file(mid: int, token: str = "", db: Session = Depends(get_db)):
    """The teacher's original upload (video, audio, PDF, image...). Token via query because <video>/<a> can't send headers."""
    m = _get_material(db, _user_from_token(db, token), mid)
    if not m.file_path or not os.path.exists(m.file_path):
        raise HTTPException(404, "No original file")
    return FileResponse(m.file_path, filename=m.filename)


class ShareIn(BaseModel):
    classroom_id: Optional[int] = None  # None = make private


@app.post("/api/materials/{mid}/share")
def share_material(mid: int, body: ShareIn, db: Session = Depends(get_db), u: User = Depends(require("teacher", "admin"))):
    """Share an already-uploaded material (and its quizzes) with a class, or make it private."""
    m = _get_material(db, u, mid)
    if u.role != "admin" and m.owner_id != u.id:
        raise HTTPException(403, "Not your material")
    if body.classroom_id:
        c = db.get(Classroom, body.classroom_id)
        if not c or (u.role == "teacher" and c.teacher_id != u.id):
            raise HTTPException(404, "Class not found")
    m.classroom_id = body.classroom_id
    for q in db.query(Quiz).filter_by(material_id=mid):
        q.classroom_id = body.classroom_id
    db.commit()
    return mat_out(m, db=db)


class SumIn(BaseModel):
    lang: str = "en"  # en | te | te_en
    simple: bool = True


@app.post("/api/materials/{mid}/summarize")
def summarize_material(mid: int, body: SumIn, db: Session = Depends(get_db), u: User = Depends(current_user)):
    m = _get_material(db, u, mid)
    out = tutor.summarize_lang(m.text or m.summary, m.level, body.lang, body.simple)
    if not out:
        if body.lang != "en":
            raise HTTPException(503, "Telugu summaries need the AI engine (ANTHROPIC_API_KEY)")
        out = m.summary
    return {"summary": out}


class TutorIn(BaseModel):
    message: str
    lang: str = "en"  # en (English→English) | te_en (Telugu→English) | te
    material_id: Optional[int] = None
    history: list[dict] = []


@app.post("/api/tutor/chat")
def tutor_chat(body: TutorIn, db: Session = Depends(get_db), u: User = Depends(require("student", "teacher", "admin"))):
    if not body.message.strip():
        raise HTTPException(400, "Say something first")
    mat = None
    if body.material_id:
        m = _get_material(db, u, body.material_id)
        mat = {"title": m.title, "text": m.text or m.summary}
    weak = [t["topic"] for t in student_stats(db, u.id)["weaknesses"]] if u.role == "student" else []
    try:
        text = tutor.reply(u.name, u.level, body.message[:4000], body.history, body.lang, mat, weak)
    except Exception as e:  # noqa
        raise HTTPException(502, "Tutor is unavailable: " + str(e)[:200])
    return {"reply": text}


@app.delete("/api/materials/{mid}")
def delete_material(mid: int, db: Session = Depends(get_db), u: User = Depends(require("teacher", "admin"))):
    m = _get_material(db, u, mid)
    if u.role != "admin" and m.owner_id != u.id:
        raise HTTPException(403, "Not your material")
    for q in db.query(Quiz).filter_by(material_id=mid):
        db.query(Attempt).filter_by(quiz_id=q.id).delete()
        db.delete(q)
    db.delete(m); db.commit()
    return {"ok": True}


def _video_job(mid: int):
    db = SessionLocal()
    try:
        m = db.get(Material, mid)
        slides = ai.video_script(m.text, m.summary, m.key_points, m.level, m.title)
        out = os.path.join(DATA_DIR, "videos", f"{mid}.mp4")
        videomod.build_video(slides, out)
        m.video_path, m.video_status, m.video_error = out, "ready", ""
    except Exception as e:  # noqa
        m = db.get(Material, mid)
        m.video_status, m.video_error = "failed", str(e)[:400]
    db.commit(); db.close()


@app.post("/api/materials/{mid}/video")
def make_video(mid: int, db: Session = Depends(get_db), u: User = Depends(require("teacher", "admin"))):
    m = _get_material(db, u, mid)
    if not (m.text or "").strip():
        raise HTTPException(422, "This material has no readable text to build a video from.")
    if m.video_status == "processing":
        return mat_out(m, db=db)
    m.video_status = "processing"; db.commit()
    threading.Thread(target=_video_job, args=(mid,), daemon=True).start()
    return mat_out(m, db=db)


@app.get("/api/materials/{mid}/video")
def get_video(mid: int, token: str = "", db: Session = Depends(get_db)):
    # <video> tags can't send headers, so accept the JWT as a query param here.
    import jwt as _jwt
    from .auth import SECRET
    try:
        uid = int(_jwt.decode(token, SECRET, algorithms=["HS256"])["sub"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    u = db.get(User, uid)
    m = _get_material(db, u, mid)
    if m.video_status != "ready" or not os.path.exists(m.video_path):
        raise HTTPException(404, "Video not ready")
    return FileResponse(m.video_path, media_type="video/mp4")


# ---------------- quizzes ----------------
class QuizIn(BaseModel):
    count: int = 8
    kind: str = "quiz"  # quiz|assessment
    types: list[str] = ["mcq", "tf", "short"]
    classroom_id: Optional[int] = None


def quiz_out(q: Quiz, reveal: bool):
    qs = q.questions if reveal else [{k: v for k, v in x.items() if k not in ("answer", "explanation")} for x in q.questions]
    return {"id": q.id, "title": q.title, "kind": q.kind, "material_id": q.material_id, "classroom_id": q.classroom_id,
            "count": len(q.questions), "questions": qs, "created_at": q.created_at.isoformat()}


@app.post("/api/materials/{mid}/quizzes")
def make_quiz(mid: int, body: QuizIn, db: Session = Depends(get_db), u: User = Depends(require("teacher", "admin"))):
    m = _get_material(db, u, mid)
    count = max(3, min(body.count, 30))
    qs = ai.make_questions(m.text or m.summary, m.level, count, body.types, m.topics)
    if not qs:
        raise HTTPException(422, "Not enough content to build questions")
    q = Quiz(material_id=mid, creator_id=u.id, classroom_id=body.classroom_id or m.classroom_id,
             title=f"{'Assessment' if body.kind == 'assessment' else 'Quiz'}: {m.title}", kind=body.kind, questions=qs)
    db.add(q); db.commit()
    return quiz_out(q, True)


def _visible_quizzes(db, u):
    if u.role == "admin":
        return db.query(Quiz).order_by(Quiz.id.desc()).all()
    if u.role == "teacher":
        return db.query(Quiz).filter_by(creator_id=u.id).order_by(Quiz.id.desc()).all()
    if u.role == "student":
        mids = {m.id for m in _visible_materials(db, u)}
        cids = [e.classroom_id for e in db.query(Enrollment).filter_by(student_id=u.id)]
        return [q for q in db.query(Quiz).order_by(Quiz.id.desc())
                if q.material_id in mids and q.classroom_id in cids]  # teacher-posted only
    return []


@app.get("/api/quizzes")
def list_quizzes(db: Session = Depends(get_db), u: User = Depends(current_user)):
    out = []
    for q in _visible_quizzes(db, u):
        d = quiz_out(q, False)
        d.pop("questions")
        if u.role == "student":
            best = db.query(Attempt).filter_by(quiz_id=q.id, student_id=u.id).order_by(Attempt.score.desc()).first()
            d["best_pct"] = round(100 * best.score / best.total) if best and best.total else None
        out.append(d)
    return out


@app.get("/api/quizzes/{qid}")
def get_quiz(qid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    q = db.get(Quiz, qid)
    if not q or q not in _visible_quizzes(db, u):
        raise HTTPException(404, "Quiz not found")
    return quiz_out(q, u.role in ("teacher", "admin"))


class SubmitIn(BaseModel):
    answers: dict[str, str]
    seconds: int = 0


@app.post("/api/quizzes/{qid}/submit")
def submit(qid: int, body: SubmitIn, db: Session = Depends(get_db), u: User = Depends(require("student"))):
    q = db.get(Quiz, qid)
    if not q or q not in _visible_quizzes(db, u):
        raise HTTPException(404, "Quiz not found")
    results, score = [], 0.0
    for item in q.questions:
        given = body.answers.get(str(item["id"]), "")
        if item["type"] == "short":
            s, comment = ai.grade_short(item["question"], item["answer"], given)
        else:
            s = 1.0 if given.strip().lower() == str(item["answer"]).strip().lower() else 0.0
            comment = ""
        score += s
        results.append({"id": item["id"], "topic": item.get("topic", "general"), "question": item["question"], "given": given,
                        "answer": item["answer"], "score": s, "explanation": item.get("explanation", ""), "comment": comment})
    a = Attempt(quiz_id=qid, student_id=u.id, score=score, total=len(q.questions), results=results, seconds=body.seconds)
    db.add(a); db.commit()
    return {"attempt_id": a.id, "score": score, "total": a.total, "pct": round(100 * score / a.total), "results": results}


# ---------------- progress & feedback ----------------
@app.get("/api/students/{sid}/progress")
def progress(sid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    if not can_view_student(db, u, sid):
        raise HTTPException(403, "You can't view this student")
    s = db.get(User, sid)
    fb = db.query(Feedback).filter_by(student_id=sid).order_by(Feedback.id.desc()).limit(10).all()
    return {"student": user_out(s), "stats": student_stats(db, sid), "communication": comm.summary(db, sid),
            "feedback": [{"id": f.id, "text": f.text, "by": "AI tutor" if f.author_id is None else db.get(User, f.author_id).name,
                          "created_at": f.created_at.isoformat()} for f in fb]}


@app.post("/api/students/{sid}/feedback/ai")
def ai_feedback(sid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    if not can_view_student(db, u, sid):
        raise HTTPException(403, "You can't view this student")
    s = db.get(User, sid)
    st = student_stats(db, sid)
    if st["attempts"] == 0:
        raise HTTPException(422, "No quiz attempts yet")
    f = Feedback(student_id=sid, author_id=None, text=ai.student_feedback(s.name, s.level, st))
    db.add(f); db.commit()
    return {"id": f.id, "text": f.text}


class FbIn(BaseModel):
    text: str


@app.post("/api/students/{sid}/feedback")
def teacher_feedback(sid: int, body: FbIn, db: Session = Depends(get_db), u: User = Depends(require("teacher", "admin"))):
    if not can_view_student(db, u, sid):
        raise HTTPException(403, "You can't view this student")
    db.add(Feedback(student_id=sid, author_id=u.id, text=body.text)); db.commit()
    return {"ok": True}


@app.get("/api/parent/children")
def children(db: Session = Depends(get_db), u: User = Depends(require("parent"))):
    return [user_out(db.get(User, l.student_id)) for l in db.query(ParentLink).filter_by(parent_id=u.id)]


# ---------------- serve built frontend if present ----------------
DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(DIST):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
