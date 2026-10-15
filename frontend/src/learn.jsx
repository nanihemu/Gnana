import React, { useEffect, useRef, useState } from "react";
import { api, videoUrl, getToken } from "./api.js";

const LEVELS = ["primary", "middle school", "high school", "undergraduate", "postgraduate", "professional"];

// ---------- Upload + library ----------
export function Library({ me, onOpenQuiz, onAsk }) {
  const student = me.role === "student";
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(null);
  const refresh = () => api("/materials").then(setItems);
  useEffect(() => { refresh(); }, []);
  if (open) return <MaterialDetail id={open} me={me} back={() => { setOpen(null); refresh(); }} onOpenQuiz={onOpenQuiz} onAsk={onAsk} />;
  return (
    <div>
      {!student && <Upload me={me} done={(m) => { refresh(); setOpen(m.id); }} />}
      <h2>{student ? "Class content from your teachers" : "Your library"}</h2>
      <div className="grid">
        {items.map((m) => (
          <div className="card" key={m.id} style={{ cursor: "pointer" }} onClick={() => setOpen(m.id)}>
            <div className="row spread"><b>{m.title}</b><span className="pill">{m.kind}</span></div>
            {m.posted_by && <div className="muted">Posted by {m.posted_by}</div>}
            <p className="muted">{m.summary.slice(0, 140)}…</p>
            {m.topics.map((t) => <span className="pill" key={t}>{t}</span>)}
          </div>))}
      </div>
      {!items.length && <p className="muted">{student ? "Your teacher hasn't posted anything to your class yet." : "Nothing yet. Upload a file or paste text above."}</p>}
    </div>
  );
}

function Upload({ me, done }) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [level, setLevel] = useState(me.level || "high school");
  const [cls, setCls] = useState("");
  const [classes, setClasses] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const file = useRef();
  useEffect(() => { if (me.role !== "student") api("/classrooms").then(setClasses); }, []);
  const go = async () => {
    setErr(""); setBusy(true);
    try {
      const f = new FormData();
      f.append("title", title); f.append("text", text); f.append("level", level);
      if (cls) f.append("classroom_id", cls);
      if (file.current.files[0]) f.append("file", file.current.files[0]);
      const m = await api("/materials", { method: "POST", form: f });
      setTitle(""); setText(""); file.current.value = "";
      done(m);
    } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  return (
    <div className="card">
      <h2>Add learning material</h2>
      <div className="grid">
        <div><label>Title (optional)</label><input value={title} onChange={(e) => setTitle(e.target.value)} /></div>
        <div><label>Learner level</label>
          <select value={level} onChange={(e) => setLevel(e.target.value)}>{LEVELS.map((l) => <option key={l}>{l}</option>)}</select></div>
        {me.role !== "student" && (
          <div><label>Share with class</label>
            <select value={cls} onChange={(e) => setCls(e.target.value)}><option value="">Private</option>
              {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>)}
      </div>
      <label>File: PDF, Word, PowerPoint, text, image, audio or video</label>
      <input type="file" ref={file} />
      <label>…or paste text</label>
      <textarea value={text} onChange={(e) => setText(e.target.value)} />
      {err && <p className="err">{err}</p>}
      <button className="btn" style={{ marginTop: ".6rem" }} disabled={busy} onClick={go}>{busy ? "Analysing…" : "Analyse & summarise"}</button>
    </div>
  );
}

// ---------- Material detail: summary, video, quiz generation ----------
function OriginalFile({ m }) {
  const url = `/api/materials/${m.id}/file?token=${encodeURIComponent(getToken())}`;
  const ext = (m.filename.split(".").pop() || "").toLowerCase();
  return (
    <div className="card">
      <h3>Teacher's original {m.kind === "video" ? "video" : m.kind === "audio" ? "audio" : "file"}</h3>
      {m.kind === "video" && <video controls src={url} />}
      {m.kind === "audio" && <audio controls src={url} style={{ width: "100%" }} />}
      {m.kind === "image" && <img src={url} alt={m.title} style={{ maxWidth: "100%", borderRadius: 10 }} />}
      {ext === "pdf" && <iframe title="pdf" src={url} style={{ width: "100%", height: 480, border: 0 }} />}
      <p><a href={url} download={m.filename}>Download {m.filename}</a></p>
    </div>
  );
}

function StudentSummary({ m }) {
  const [lang, setLang] = useState("en");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const go = async () => {
    setBusy(true); setErr("");
    try { setOut((await api(`/materials/${m.id}/summarize`, { method: "POST", body: { lang, simple: true } })).summary); }
    catch (e) { setErr(e.message); }
    setBusy(false);
  };
  return (
    <div className="card">
      <h3>Summarise this for me</h3>
      <div className="row">
        <select value={lang} onChange={(e) => setLang(e.target.value)} style={{ width: 240 }}>
          <option value="en">Simple English</option><option value="te">తెలుగు (Telugu)</option><option value="te_en">English + తెలుగు</option></select>
        <button className="btn" disabled={busy} onClick={go}>{busy ? "Summarising…" : "Summarise"}</button>
      </div>
      {err && <p className="err">{err}</p>}
      {out && <p style={{ whiteSpace: "pre-wrap" }}>{out}</p>}
    </div>
  );
}

function MaterialDetail({ id, me, back, onOpenQuiz, onAsk }) {
  const student = me.role === "student";
  const [m, setM] = useState(null);
  const [quizzes, setQuizzes] = useState([]);
  const [count, setCount] = useState(8);
  const [kind, setKind] = useState("quiz");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const load = () => api(`/materials/${id}`).then(setM);
  useEffect(() => { load(); api("/quizzes").then((q) => setQuizzes(q.filter((x) => x.material_id === id))); }, [id]);
  useEffect(() => {
    if (m && m.video_status === "processing") { const t = setTimeout(load, 3000); return () => clearTimeout(t); }
  }, [m]);
  if (!m) return <p className="muted">Loading…</p>;
  const makeVideo = async () => { setM(await api(`/materials/${id}/video`, { method: "POST" })); };
  const makeQuiz = async () => {
    setBusy(true); setErr("");
    try { const q = await api(`/materials/${id}/quizzes`, { method: "POST", body: { count: +count, kind } }); onOpenQuiz(q.id); }
    catch (e) { setErr(e.message); }
    setBusy(false);
  };
  const del = async () => { if (confirm("Delete this material and its quizzes?")) { await api(`/materials/${id}`, { method: "DELETE" }); back(); } };
  return (
    <div>
      <button className="btn ghost" onClick={back}>← Back</button>
      <div className="card" style={{ marginTop: ".8rem" }}>
        <div className="row spread"><h2>{m.title}</h2><span className="pill">{m.kind} · {m.level}</span></div>
        <h3>Summary</h3><p>{m.summary}</p>
        <h3>Key points</h3><ul>{m.key_points.map((k, i) => <li key={i}>{k}</li>)}</ul>
        {m.topics.map((t) => <span className="pill" key={t}>{t}</span>)}
        {m.posted_by && <p className="muted">Posted by {m.posted_by}</p>}
      </div>
      {m.has_file && <OriginalFile m={m} />}
      {student && m.video_status === "ready" && (
        <div className="card"><h3>Explainer video</h3><video controls src={videoUrl(m.id)} /></div>)}
      {student && <StudentSummary m={m} />}
      {student && (
        <div className="card">
          <h3>Learn with the AI tutor</h3>
          <p className="muted">Ask questions about this lesson in English or Telugu.</p>
          <button className="btn" onClick={() => onAsk(m.id)}>Ask the tutor about this</button>
          <h3 style={{ marginTop: "1rem" }}>Quizzes & assessments</h3>
          {quizzes.map((q) => (
            <div key={q.id} className="row spread" style={{ marginBottom: ".4rem" }}>
              <span>{q.title} <span className="muted">({q.count} q){q.best_pct != null && ` · best ${q.best_pct}%`}</span></span>
              <button className="btn ghost" onClick={() => onOpenQuiz(q.id)}>Start</button></div>))}
          {!quizzes.length && <p className="muted">No assessments posted for this lesson yet.</p>}
        </div>)}
      {!student && <div className="grid">
        <div className="card">
          <h3>Explainer video</h3>
          {m.video_status === "ready" && <video controls src={videoUrl(m.id)} />}
          {m.video_status === "processing" && <p className="muted">Rendering your video… this takes a minute.</p>}
          {m.video_status === "failed" && <p className="err">Failed: {m.video_error}</p>}
          {(m.video_status === "none" || m.video_status === "failed") &&
            <button className="btn" onClick={makeVideo}>Generate video</button>}
        </div>
        <div className="card">
          <h3>Questions</h3>
          <div className="row">
            <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ width: 140 }}>
              <option value="quiz">Quiz</option><option value="assessment">Assessment</option></select>
            <input type="number" min="3" max="30" value={count} onChange={(e) => setCount(e.target.value)} style={{ width: 80 }} />
            <button className="btn" disabled={busy} onClick={makeQuiz}>{busy ? "Creating…" : "Generate"}</button>
          </div>
          {err && <p className="err">{err}</p>}
          {quizzes.map((q) => (
            <div key={q.id} className="row spread" style={{ marginTop: ".5rem" }}>
              <span>{q.title} <span className="muted">({q.count} q)</span></span>
              <button className="btn ghost" onClick={() => onOpenQuiz(q.id)}>Open</button></div>))}
        </div>
      </div>}
      {!student && <button className="btn danger" onClick={del}>Delete material</button>}
    </div>
  );
}

// ---------- Quiz list + taking quiz ----------
export function Quizzes({ me, openId, clearOpen }) {
  const [list, setList] = useState([]);
  const [cur, setCur] = useState(openId || null);
  useEffect(() => { api("/quizzes").then(setList); }, [cur]);
  useEffect(() => { if (openId) setCur(openId); }, [openId]);
  if (cur) return <QuizRunner id={cur} me={me} back={() => { setCur(null); clearOpen && clearOpen(); }} />;
  return (
    <div>
      <h2>Quizzes & assessments</h2>
      <div className="grid">
        {list.map((q) => (
          <div className="card" key={q.id}>
            <div className="row spread"><b>{q.title}</b><span className="pill">{q.kind}</span></div>
            <p className="muted">{q.count} questions {q.best_pct != null && <>· best <b>{q.best_pct}%</b></>}</p>
            <button className="btn" onClick={() => setCur(q.id)}>{me.role === "student" ? "Start" : "View"}</button>
          </div>))}
      </div>
      {!list.length && <p className="muted">No quizzes yet. Open a material and generate one.</p>}
    </div>
  );
}

function QuizRunner({ id, me, back }) {
  const [q, setQ] = useState(null);
  const [ans, setAns] = useState({});
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");
  const t0 = useRef(Date.now());
  useEffect(() => { api(`/quizzes/${id}`).then(setQ); t0.current = Date.now(); }, [id]);
  if (!q) return <p className="muted">Loading…</p>;
  const isStudent = me.role === "student";
  const submit = async () => {
    setErr("");
    try { setRes(await api(`/quizzes/${id}/submit`, { method: "POST", body: { answers: ans, seconds: Math.round((Date.now() - t0.current) / 1000) } })); }
    catch (e) { setErr(e.message); }
  };
  if (res) {
    return (
      <div>
        <div className="card"><h2>Result: {res.pct}%</h2><p>{res.score.toFixed(1)} / {res.total}</p>
          <button className="btn" onClick={back}>Done</button></div>
        {res.results.map((r, i) => (
          <div key={r.id} className={"card " + (r.score >= 0.6 ? "right" : "wrong")}>
            <b>{i + 1}. {r.question}</b> <span className="pill">{r.topic}</span>
            <p>Your answer: {r.given || <i>blank</i>}</p>
            {r.score < 1 && <p>Correct answer: <b>{r.answer}</b></p>}
            {r.comment && <p className="muted">{r.comment}</p>}
            {r.explanation && <p className="muted">{r.explanation}</p>}
          </div>))}
      </div>);
  }
  return (
    <div>
      <button className="btn ghost" onClick={back}>← Back</button>
      <div className="card" style={{ marginTop: ".8rem" }}>
        <h2>{q.title}</h2>
        {q.questions.map((x, i) => (
          <div className="q" key={x.id}>
            <b>{i + 1}. {x.question}</b> <span className="pill">{x.topic}</span>
            {(x.type === "mcq" || x.type === "tf") && (x.options.length ? x.options : ["True", "False"]).map((o) => (
              <label key={o} className={"opt " + (ans[x.id] === o ? "sel" : "")} style={{ color: "inherit", fontSize: "1rem" }}>
                <input type="radio" style={{ width: "auto", marginRight: 8 }} disabled={!isStudent} checked={ans[x.id] === o}
                  onChange={() => setAns({ ...ans, [x.id]: o })} />{o}</label>))}
            {x.type === "short" && <textarea disabled={!isStudent} value={ans[x.id] || ""} onChange={(e) => setAns({ ...ans, [x.id]: e.target.value })} />}
            {!isStudent && <p className="muted">Answer: <b>{x.answer}</b> — {x.explanation}</p>}
          </div>))}
        {err && <p className="err">{err}</p>}
        {isStudent && <button className="btn" style={{ marginTop: "1rem" }} onClick={submit}>Submit</button>}
      </div>
    </div>
  );
}
