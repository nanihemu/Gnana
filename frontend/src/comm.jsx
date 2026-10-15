import React, { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { Bar } from "./components.jsx";

const SR = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);
const SKILL = { speak: "Speaking", write: "Writing", vocab: "Vocabulary" };

export function Communicator() {
  const [view, setView] = useState("today");
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(null);
  const load = () => api("/comm/today").then(setData);
  useEffect(() => { load(); }, []);
  if (!data) return <p className="muted">Loading…</p>;
  const s = data.summary;
  return (
    <div>
      <div className="grid">
        <div className="card"><div className="muted">Level</div><div className="stat" style={{ fontSize: "1.2rem", textTransform: "capitalize" }}>{data.level}</div></div>
        <div className="card"><div className="muted">Day streak</div><div className="stat">{s.streak}</div></div>
        <div className="card"><div className="muted">Today</div><div className="stat">{s.today_done}/{s.today_total}</div></div>
        <div className="card"><div className="muted">XP</div><div className="stat">{s.xp}</div></div>
      </div>
      <div className="row" style={{ marginBottom: ".8rem" }}>
        {[["today", "Today's tasks"], ["practice", "Practice conversation"], ["skills", "My skills"]].map(([k, l]) => (
          <button key={k} className={"btn " + (view === k ? "" : "ghost")} onClick={() => { setView(k); setOpen(null); }}>{l}</button>))}
      </div>
      {view === "today" && !open && <Today data={data} onOpen={setOpen} />}
      {view === "today" && open && <TaskRunner task={data.tasks.find((t) => t.id === open)} back={() => { setOpen(null); load(); }} />}
      {view === "practice" && <Practice />}
      {view === "skills" && <Skills s={s} />}
    </div>
  );
}

function Today({ data, onOpen }) {
  return (
    <div className="grid">
      {data.tasks.map((t) => (
        <div className="card" key={t.id}>
          <div className="row spread"><b>{t.title}</b>
            <span className={"pill " + (t.status === "done" ? "ok" : "")}>{t.status === "done" ? "done · +" + t.xp + " XP" : SKILL[t.skill]}</span></div>
          {t.source === "teacher" && <span className="pill">From your teacher</span>}
          <p className="muted">{t.prompt}</p>
          <button className={"btn " + (t.status === "done" ? "ghost" : "")} onClick={() => onOpen(t.id)}>{t.status === "done" ? "See feedback" : "Start"}</button>
        </div>))}
    </div>
  );
}

function Scores({ scores }) {
  return Object.entries(scores || {}).map(([k, v]) => (
    <div key={k} className="row" style={{ marginBottom: ".4rem" }}>
      <div style={{ width: 100, textTransform: "capitalize" }}>{k}</div><div style={{ flex: 1 }}><Bar pct={v * 20} /></div><div style={{ width: 36 }}>{v}/5</div>
    </div>));
}

function Feedback({ task }) {
  const f = task.feedback || {};
  const m = f.metrics || {};
  return (
    <div className="card">
      <h3>Your feedback · +{task.xp} XP</h3>
      <Scores scores={task.scores} />
      <div className="row" style={{ margin: ".6rem 0" }}>
        <span className="pill">{m.words} words</span>
        {m.wpm ? <span className="pill">{m.wpm} words/min</span> : null}
        <span className={"pill " + (m.fillers > 2 ? "bad" : "ok")}>{m.fillers} fillers</span>
      </div>
      <h3>What you did well</h3><ul>{(f.strengths || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
      <h3>Improve next</h3>
      <ul>{(f.improvements || []).map((s, i) => <li key={i}><b>{s.issue}</b> {s.fix}</li>)}</ul>
      {f.improved_version && <><h3>A stronger version</h3><div className="fb">{f.improved_version}</div></>}
      {f.telugu_note && <><h3>తెలుగులో</h3><div className="fb">{f.telugu_note}</div></>}
      {f.tip && <p><b>Tip for tomorrow:</b> {f.tip}</p>}
      {f.offline && <p className="muted">Basic feedback only. Turn on the AI engine for grammar fixes and model answers.</p>}
    </div>
  );
}

function TaskRunner({ task, back }) {
  const [text, setText] = useState(task.response || "");
  const [res, setRes] = useState(task.status === "done" ? task : null);
  const [tele, setTele] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [listening, setListening] = useState(false);
  const [secs, setSecs] = useState(0);
  const rec = useRef(); const started = useRef(0); const base = useRef("");
  useEffect(() => {
    if (!listening) return;
    const t = setInterval(() => setSecs(Math.round((Date.now() - started.current) / 1000)), 500);
    return () => clearInterval(t);
  }, [listening]);

  const mic = () => {
    if (!SR) return alert("Speech input isn't supported in this browser. Use Chrome or Edge, or type your answer.");
    if (listening) { rec.current.stop(); return; }
    const r = new SR();
    r.lang = "en-IN"; r.continuous = true; r.interimResults = true;
    base.current = text ? text + " " : "";
    r.onresult = (e) => {
      let t = "";
      for (let i = 0; i < e.results.length; i++) t += e.results[i][0].transcript;
      setText(base.current + t);
    };
    r.onend = () => setListening(false);
    r.onerror = () => setListening(false);
    rec.current = r; started.current = Date.now(); setSecs(0); setListening(true); r.start();
  };

  const submit = async () => {
    setBusy(true); setErr("");
    try {
      const r = await api(`/comm/tasks/${task.id}/submit`, { method: "POST", body: { response: text, seconds: secs, tele } });
      setRes(r.task);
    } catch (e) { setErr(e.message); }
    setBusy(false);
  };

  const words = (text.match(/\S+/g) || []).length;
  const goal = task.target.min_words;
  return (
    <div>
      <button className="btn ghost" onClick={back}>← Back</button>
      <div className="card" style={{ marginTop: ".8rem" }}>
        <div className="row spread"><h2>{task.title}</h2><span className="pill">{SKILL[task.skill]}</span></div>
        <p>{task.prompt}</p>
        {task.skill === "speak" && <p className="muted">Tip: press Speak and talk naturally. Your words appear below. You can fix any mis-heard words before submitting.</p>}
        {!res && (<>
          {task.skill === "speak" && <div className="row"><button className="btn" onClick={mic}>{listening ? `● Stop (${secs}s)` : "Speak"}</button>
            <span className="muted">Goal: about {task.target.seconds}s</span></div>}
          <textarea style={{ minHeight: 160, marginTop: ".6rem" }} value={text} onChange={(e) => setText(e.target.value)}
            placeholder={task.skill === "speak" ? "Your speech appears here (or type it)…" : "Type your answer…"} />
          <div className="row spread" style={{ marginTop: ".4rem" }}>
            <span className={"pill " + (words >= goal ? "ok" : "")}>{words}/{goal} words</span>
            <label className="row" style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={tele} onChange={(e) => setTele(e.target.checked)} /> Explain feedback in Telugu too</label>
          </div>
          {err && <p className="err">{err}</p>}
          <button className="btn" style={{ marginTop: ".6rem" }} disabled={busy} onClick={submit}>{busy ? "Your coach is reading…" : "Get feedback"}</button>
        </>)}
        {res && <div className="fb"><b>Your answer</b><br />{res.response}</div>}
      </div>
      {res && <Feedback task={res} />}
    </div>
  );
}

function Practice() {
  const [list, setList] = useState([]);
  const [sid, setSid] = useState("");
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [tele, setTele] = useState(false);
  const [listening, setListening] = useState(false);
  const end = useRef(); const rec = useRef();
  useEffect(() => { api("/comm/scenarios").then((l) => { setList(l); if (l[0]) setSid(l[0].id); }); }, []);
  useEffect(() => { end.current && end.current.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const call = async (message, history) => {
    setBusy(true);
    try {
      const r = await api("/comm/chat", { method: "POST", body: { scenario_id: sid, message, history, tele } });
      setMsgs((m) => [...m, { role: "assistant", content: r.reply }]);
    } catch (e) { setMsgs((m) => [...m, { role: "assistant", content: "Sorry: " + e.message }]); }
    setBusy(false);
  };
  const start = () => { setMsgs([]); call("", []); };
  const send = (override) => {
    const message = (override ?? text).trim();
    if (!message || busy) return;
    const history = msgs;
    setMsgs([...msgs, { role: "user", content: message }]); setText("");
    call(message, history);
  };
  const mic = () => {
    if (!SR) return alert("Speech input isn't supported in this browser. Use Chrome or Edge.");
    if (listening) { rec.current.stop(); return; }
    const r = new SR(); r.lang = "en-IN";
    r.onresult = (e) => send(e.results[0][0].transcript);
    r.onend = () => setListening(false); r.onerror = () => setListening(false);
    rec.current = r; setListening(true); r.start();
  };
  const render = (m) => {
    const [say, ...coach] = m.content.split(/\n\s*Coach:/);
    return (<>
      <div>{say}</div>
      {coach.length > 0 && <div style={{ marginTop: ".4rem", padding: ".4rem .6rem", borderRadius: 8, background: "#fff8e1", color: "#7a5b00", fontSize: ".9rem" }}>
        <b>Coach:</b> {coach.join(" ")}</div>}
    </>);
  };
  return (
    <div>
      <div className="card">
        <div className="row">
          <select style={{ maxWidth: 320 }} value={sid} onChange={(e) => setSid(e.target.value)}>{list.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}</select>
          <button className="btn" onClick={start}>{msgs.length ? "Restart" : "Start role-play"}</button>
          <label className="row" style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={tele} onChange={(e) => setTele(e.target.checked)} /> Coach notes in Telugu too</label>
        </div>
        <p className="muted">Talk to an AI partner in a real-life situation for your level. After each reply, a coach note shows one thing to improve.</p>
      </div>
      {msgs.length > 0 && (<>
        <div className="card" style={{ minHeight: 300 }}>
          {msgs.map((m, i) => (
            <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", margin: ".5rem 0" }}>
              <div style={{ maxWidth: "80%", whiteSpace: "pre-wrap", padding: ".6rem .85rem", borderRadius: 12,
                background: m.role === "user" ? "#3b5bdb" : "#eef1fb", color: m.role === "user" ? "#fff" : "#1b2559" }}>
                {m.role === "user" ? m.content : render(m)}</div>
            </div>))}
          {busy && <p className="muted">Typing…</p>}<div ref={end} />
        </div>
        <div className="card row">
          <button className="btn ghost" onClick={mic}>{listening ? "● Listening…" : "Speak"}</button>
          <input style={{ flex: 1, minWidth: 200 }} value={text} placeholder="Say or type your reply…" onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} />
          <button className="btn" disabled={busy} onClick={() => send()}>Send</button>
        </div>
      </>)}
    </div>
  );
}

export function SkillBars({ s }) {
  if (!s.completed) return <p className="muted">No communication tasks completed yet.</p>;
  return (<>
    <h3>By skill</h3>
    {Object.entries(s.skills).map(([k, v]) => (
      <div key={k} className="row" style={{ marginBottom: ".4rem" }}><div style={{ width: 110 }}>{SKILL[k] || k}</div><div style={{ flex: 1 }}><Bar pct={v} /></div><div style={{ width: 40 }}>{v}%</div></div>))}
    <h3>By criteria</h3>
    {Object.entries(s.criteria).map(([k, v]) => (
      <div key={k} className="row" style={{ marginBottom: ".4rem" }}><div style={{ width: 110, textTransform: "capitalize" }}>{k}</div><div style={{ flex: 1 }}><Bar pct={v} /></div><div style={{ width: 40 }}>{v}%</div></div>))}
    {s.focus && <p>Focus area: <b style={{ textTransform: "capitalize" }}>{s.focus}</b></p>}
  </>);
}

function Skills({ s }) {
  return (
    <div className="card">
      <h2>My communication skills</h2>
      <p className="muted">{s.completed} tasks completed · {s.streak}-day streak · {s.xp} XP</p>
      <SkillBars s={s} />
      {s.daily.length > 0 && <><h3>Last days</h3>
        <div className="row">{s.daily.map((d) => <span key={d.day} className={"pill " + (d.pct >= 70 ? "ok" : d.pct < 50 ? "bad" : "")}>{d.day.slice(5)}: {d.pct}%</span>)}</div></>}
    </div>
  );
}
