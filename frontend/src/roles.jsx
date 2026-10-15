import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { ProgressView, Bar } from "./components.jsx";

// ---------- Teacher: classes + student progress ----------
export function Classes({ me }) {
  const [classes, setClasses] = useState([]);
  const [name, setName] = useState("");
  const [sel, setSel] = useState(null);
  const [student, setStudent] = useState(null);
  const refresh = () => api("/classrooms").then(setClasses);
  useEffect(() => { refresh(); }, []);
  const create = async () => { if (name.trim()) { await api("/classrooms", { method: "POST", body: { name } }); setName(""); refresh(); } };
  if (student) return (<div><button className="btn ghost" onClick={() => setStudent(null)}>← Back to class</button>
    <div style={{ marginTop: ".8rem" }}><ProgressView studentId={student} canWriteFeedback /></div></div>);
  if (sel) return <ClassDetail id={sel} back={() => { setSel(null); refresh(); }} openStudent={setStudent} />;
  return (
    <div>
      <div className="card"><h2>Create a class</h2>
        <div className="row"><input style={{ maxWidth: 320 }} placeholder="e.g. Grade 9 Biology" value={name} onChange={(e) => setName(e.target.value)} />
          <button className="btn" onClick={create}>Create</button></div></div>
      <div className="grid">{classes.map((c) => (
        <div className="card" key={c.id}><b>{c.name}</b><p className="muted">{c.students.length} students</p>
          <button className="btn" onClick={() => setSel(c.id)}>Open</button></div>))}</div>
    </div>
  );
}

function ClassDetail({ id, back, openStudent }) {
  const [rows, setRows] = useState([]);
  const [email, setEmail] = useState("");
  const [err, setErr] = useState("");
  const load = () => api(`/classrooms/${id}/progress`).then(setRows);
  useEffect(() => { load(); }, [id]);
  const add = async () => {
    setErr("");
    try { await api(`/classrooms/${id}/students`, { method: "POST", body: { student_email: email } }); setEmail(""); load(); }
    catch (e) { setErr(e.message); }
  };
  return (
    <div>
      <button className="btn ghost" onClick={back}>← Classes</button>
      <div className="card" style={{ marginTop: ".8rem" }}><h3>Add student by email</h3>
        <div className="row"><input style={{ maxWidth: 320 }} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="student@school.org" />
          <button className="btn" onClick={add}>Add</button></div>{err && <p className="err">{err}</p>}</div>
      <AssignComm classId={id} />
      <div className="card"><h3>Class progress</h3>
        <table><thead><tr><th>Student</th><th>Avg</th><th>Attempts</th><th>Trend</th><th>Strong</th><th>Needs work</th><th /></tr></thead><tbody>
          {rows.map((r) => (
            <tr key={r.student.id}><td>{r.student.name}</td>
              <td style={{ width: 120 }}>{r.attempts ? <><Bar pct={r.average} />{r.average}%</> : "—"}</td>
              <td>{r.attempts}</td><td>{r.trend}</td>
              <td>{r.strengths.map((t) => <span className="pill ok" key={t}>{t}</span>)}</td>
              <td>{r.weaknesses.map((t) => <span className="pill bad" key={t}>{t}</span>)}</td>
              <td><button className="btn ghost" onClick={() => openStudent(r.student.id)}>Details</button></td></tr>))}
        </tbody></table>
        {!rows.length && <p className="muted">No students yet.</p>}
      </div>
    </div>
  );
}

function AssignComm({ classId }) {
  const [f, setF] = useState({ title: "", prompt: "", skill: "speak", min_words: 50 });
  const [msg, setMsg] = useState("");
  const go = async () => {
    setMsg("");
    try {
      const r = await api("/comm/assign", { method: "POST", body: { ...f, classroom_id: classId, min_words: +f.min_words } });
      setMsg(`Assigned to ${r.assigned_to} students for today.`); setF({ ...f, title: "", prompt: "" });
    } catch (e) { setMsg(e.message); }
  };
  return (
    <div className="card"><h3>Assign a communication task (optional)</h3>
      <p className="muted">Students already get daily tasks matched to their level. Add your own for today.</p>
      <div className="grid">
        <div><label>Title</label><input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></div>
        <div><label>Type</label><select value={f.skill} onChange={(e) => setF({ ...f, skill: e.target.value })}>
          <option value="speak">Speaking</option><option value="write">Writing</option><option value="vocab">Vocabulary</option></select></div>
        <div><label>Minimum words</label><input type="number" value={f.min_words} onChange={(e) => setF({ ...f, min_words: e.target.value })} /></div>
      </div>
      <label>Task instructions</label><textarea value={f.prompt} onChange={(e) => setF({ ...f, prompt: e.target.value })} />
      <button className="btn" style={{ marginTop: ".5rem" }} onClick={go}>Assign to class</button>{msg && <span className="muted"> {msg}</span>}
    </div>
  );
}

// ---------- Parent ----------
export function Parent() {
  const [kids, setKids] = useState(null);
  const [sel, setSel] = useState(null);
  useEffect(() => { api("/parent/children").then((k) => { setKids(k); if (k[0]) setSel(k[0].id); }); }, []);
  if (!kids) return <p className="muted">Loading…</p>;
  if (!kids.length) return <div className="card"><h2>No children linked yet</h2><p className="muted">Ask the school admin or a teacher to link your account to your child's.</p></div>;
  return (
    <div>
      {kids.length > 1 && <div className="row" style={{ marginBottom: ".8rem" }}>{kids.map((k) =>
        <button key={k.id} className={"btn " + (k.id === sel ? "" : "ghost")} onClick={() => setSel(k.id)}>{k.name}</button>)}</div>}
      {sel && <ProgressView studentId={sel} />}
    </div>
  );
}

// ---------- Admin ----------
export function Admin() {
  const [ov, setOv] = useState(null);
  const [users, setUsers] = useState([]);
  const [f, setF] = useState({ name: "", email: "", password: "", role: "student", level: "high school" });
  const [link, setLink] = useState({ parent_email: "", student_email: "" });
  const [view, setView] = useState(null);
  const [msg, setMsg] = useState("");
  const load = () => { api("/admin/overview").then(setOv); api("/admin/users").then(setUsers); };
  useEffect(() => { load(); }, []);
  const create = async () => {
    setMsg("");
    try { await api("/admin/users", { method: "POST", body: f }); setF({ ...f, name: "", email: "", password: "" }); load(); }
    catch (e) { setMsg(e.message); }
  };
  const doLink = async () => {
    setMsg("");
    try { await api("/admin/parent-links", { method: "POST", body: link }); setMsg("Linked."); } catch (e) { setMsg(e.message); }
  };
  if (view) return (<div><button className="btn ghost" onClick={() => setView(null)}>← Back</button>
    <div style={{ marginTop: ".8rem" }}><ProgressView studentId={view} canWriteFeedback /></div></div>);
  return (
    <div>
      {ov && <div className="grid">
        {Object.entries(ov.users).map(([r, n]) => <div className="card" key={r}><div className="muted" style={{ textTransform: "capitalize" }}>{r}s</div><div className="stat">{n}</div></div>)}
        <div className="card"><div className="muted">Materials</div><div className="stat">{ov.materials}</div></div>
        <div className="card"><div className="muted">Quizzes</div><div className="stat">{ov.quizzes}</div></div>
        <div className="card"><div className="muted">Platform avg score</div><div className="stat">{ov.average}%</div></div>
        <div className="card"><div className="muted">AI engine</div><div className="stat" style={{ fontSize: "1.1rem" }}>{ov.ai_enabled ? "Claude connected" : "Offline fallback"}</div></div>
      </div>}
      {msg && <p className="err">{msg}</p>}
      <div className="grid">
        <div className="card"><h3>Create user</h3>
          <label>Name</label><input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
          <label>Email</label><input value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
          <label>Password</label><input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
          <label>Role</label><select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
            {["student", "teacher", "parent", "admin"].map((r) => <option key={r}>{r}</option>)}</select>
          <button className="btn" style={{ marginTop: ".6rem" }} onClick={create}>Create</button></div>
        <div className="card"><h3>Link parent to student</h3>
          <label>Parent email</label><input value={link.parent_email} onChange={(e) => setLink({ ...link, parent_email: e.target.value })} />
          <label>Student email</label><input value={link.student_email} onChange={(e) => setLink({ ...link, student_email: e.target.value })} />
          <button className="btn" style={{ marginTop: ".6rem" }} onClick={doLink}>Link</button></div>
      </div>
      <div className="card"><h3>All users</h3>
        <table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th /></tr></thead><tbody>
          {users.map((u) => (
            <tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td><span className="badge">{u.role}</span></td>
              <td className="row">{u.role === "student" && <button className="btn ghost" onClick={() => setView(u.id)}>Progress</button>}
                <button className="btn danger" onClick={async () => { if (confirm("Delete " + u.name + "?")) { await api("/admin/users/" + u.id, { method: "DELETE" }).catch((e) => setMsg(e.message)); load(); } }}>Delete</button></td></tr>))}
        </tbody></table></div>
    </div>
  );
}
