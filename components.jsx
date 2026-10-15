import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { SkillBars } from "./comm.jsx";

export const tone = (p) => (p >= 75 ? "ok" : p >= 60 ? "warn" : "bad");

export function Bar({ pct }) {
  return (
    <div className={"bar " + tone(pct)}>
      <i style={{ width: Math.max(2, pct) + "%" }} />
    </div>
  );
}

export function LineChart({ data }) {
  if (!data.length) return <p className="muted">No activity yet.</p>;
  const W = 520, H = 160, P = 24;
  const pts = data.map((d, i) => [
    P + (data.length === 1 ? (W - 2 * P) / 2 : (i * (W - 2 * P)) / (data.length - 1)),
    H - P - (d.pct / 100) * (H - 2 * P),
  ]);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%" }}>
      {[0, 50, 100].map((g) => {
        const y = H - P - (g / 100) * (H - 2 * P);
        return (
          <g key={g}>
            <line x1={P} x2={W - P} y1={y} y2={y} stroke="#e3e8f4" />
            <text x={2} y={y + 4} fontSize="10" fill="#6b7699">{g}</text>
          </g>
        );
      })}
      <polyline fill="none" stroke="#3b5bdb" strokeWidth="2.5" points={pts.map((p) => p.join(",")).join(" ")} />
      {pts.map((p, i) => (
        <g key={i}>
          <circle cx={p[0]} cy={p[1]} r="4" fill="#3b5bdb" />
          <text x={p[0]} y={H - 6} fontSize="9" textAnchor="middle" fill="#6b7699">{data[i].day.slice(5)}</text>
        </g>
      ))}
    </svg>
  );
}

// Day-to-day progress dashboard for one student. Used by student, parent, teacher and admin views.
export function ProgressView({ studentId, canWriteFeedback }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  const load = () => api(`/students/${studentId}/progress`).then(setD).catch((e) => setErr(e.message));
  useEffect(() => { setD(null); load(); }, [studentId]);

  const genAI = async () => {
    setBusy(true); setErr("");
    try { await api(`/students/${studentId}/feedback/ai`, { method: "POST" }); await load(); }
    catch (e) { setErr(e.message); }
    setBusy(false);
  };
  const addNote = async () => {
    if (!note.trim()) return;
    await api(`/students/${studentId}/feedback`, { method: "POST", body: { text: note } });
    setNote(""); load();
  };

  if (err && !d) return <p className="err">{err}</p>;
  if (!d) return <p className="muted">Loading…</p>;
  const s = d.stats;
  return (
    <div>
      <h2>{d.student.name} <span className="badge">{d.student.level}</span></h2>
      <div className="grid">
        <div className="card"><div className="muted">Average score</div><div className="stat">{s.average}%</div></div>
        <div className="card"><div className="muted">Attempts</div><div className="stat">{s.attempts}</div></div>
        <div className="card"><div className="muted">Trend</div><div className="stat" style={{ fontSize: "1.3rem" }}>{s.trend}</div></div>
        <div className="card"><div className="muted">Day streak</div><div className="stat">{s.streak}</div></div>
      </div>
      <div className="card"><h3>Daily performance</h3><LineChart data={s.daily} /></div>
      <div className="grid">
        <div className="card">
          <h3>Where they're strong</h3>
          {s.strengths.length ? s.strengths.map((t) => (
            <div key={t.topic} style={{ marginBottom: ".6rem" }}>
              <div className="row spread"><b>{t.topic}</b><span className="muted">{t.pct}% · {t.questions} q</span></div><Bar pct={t.pct} />
            </div>)) : <p className="muted">Not enough data yet (needs 2+ questions per topic at 75%+).</p>}
        </div>
        <div className="card">
          <h3>Where they need work</h3>
          {s.weaknesses.length ? s.weaknesses.map((t) => (
            <div key={t.topic} style={{ marginBottom: ".6rem" }}>
              <div className="row spread"><b>{t.topic}</b><span className="muted">{t.pct}% · {t.questions} q</span></div><Bar pct={t.pct} />
            </div>)) : <p className="muted">No weak topics detected.</p>}
        </div>
      </div>
      {d.communication && (
        <div className="card">
          <h3>Communication skills</h3>
          <p className="muted">{d.communication.completed} tasks done · {d.communication.streak}-day streak · {d.communication.xp} XP</p>
          <SkillBars s={d.communication} />
        </div>)}
      <div className="card">
        <h3>All topics</h3>
        {s.topics.map((t) => (
          <div key={t.topic} className="row" style={{ marginBottom: ".4rem" }}>
            <div style={{ width: 160 }}>{t.topic}</div><div style={{ flex: 1 }}><Bar pct={t.pct} /></div><div style={{ width: 44 }}>{t.pct}%</div>
          </div>))}
        {!s.topics.length && <p className="muted">Take a quiz to see topic breakdown.</p>}
      </div>
      <div className="card">
        <div className="row spread"><h3>Feedback</h3>
          <button className="btn ghost" disabled={busy || !s.attempts} onClick={genAI}>{busy ? "Thinking…" : "Generate AI feedback"}</button></div>
        {err && <p className="err">{err}</p>}
        {d.feedback.map((f) => (
          <div className="fb" key={f.id}><div className="muted">{f.by} · {new Date(f.created_at + "Z").toLocaleString()}</div>{f.text}</div>))}
        {!d.feedback.length && <p className="muted">No feedback yet.</p>}
        {canWriteFeedback && (
          <div style={{ marginTop: ".6rem" }}>
            <textarea placeholder="Write your own feedback…" value={note} onChange={(e) => setNote(e.target.value)} />
            <button className="btn" style={{ marginTop: ".4rem" }} onClick={addNote}>Post feedback</button>
          </div>)}
      </div>
      <div className="card">
        <h3>Recent attempts</h3>
        <table><thead><tr><th>When</th><th>Quiz</th><th>Score</th><th>Time</th></tr></thead><tbody>
          {s.history.map((h) => (
            <tr key={h.attempt_id}><td>{new Date(h.date + "Z").toLocaleDateString()}</td><td>{h.quiz}</td>
              <td><span className={"pill " + (h.pct >= 60 ? "ok" : "bad")}>{h.pct}%</span></td><td>{h.seconds}s</td></tr>))}
        </tbody></table>
      </div>
    </div>
  );
}
