import React, { useEffect, useState } from "react";
import { api, setToken, getToken } from "./api.js";
import { ProgressView } from "./components.jsx";
import { Library, Quizzes } from "./learn.jsx";
import { Classes, Parent, Admin } from "./roles.jsx";
import { Tutor } from "./tutor.jsx";
import { Communicator } from "./comm.jsx";

function Auth({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", password: "", role: "student", level: "high school" });
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const go = async () => {
    setErr("");
    try {
      const r = await api(mode === "login" ? "/auth/login" : "/auth/register", { method: "POST", body: f });
      setToken(r.token); onAuth();
    } catch (e) { setErr(e.message); }
  };
  return (
    <div className="card auth">
      <h1 className="logo">Gnana</h1>
      <p className="muted">Learn from anything. Upload it, understand it, test yourself, track progress.</p>
      {mode === "register" && <><label>Name</label><input value={f.name} onChange={set("name")} />
        <label>I am a</label><select value={f.role} onChange={set("role")}>
          <option value="student">Student</option><option value="teacher">Teacher</option><option value="parent">Parent</option>
          <option value="admin">Admin (first account only)</option></select>
        {f.role === "student" && <><label>Level</label><select value={f.level} onChange={set("level")}>
          {["primary", "middle school", "high school", "undergraduate", "postgraduate", "professional"].map((l) => <option key={l}>{l}</option>)}</select></>}</>}
      <label>Email</label><input value={f.email} onChange={set("email")} />
      <label>Password</label><input type="password" value={f.password} onChange={set("password")} onKeyDown={(e) => e.key === "Enter" && go()} />
      {err && <p className="err">{err}</p>}
      <button className="btn" style={{ marginTop: ".8rem", width: "100%" }} onClick={go}>{mode === "login" ? "Log in" : "Create account"}</button>
      <p className="muted" style={{ textAlign: "center", cursor: "pointer" }} onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "New here? Create an account" : "Have an account? Log in"}</p>
    </div>
  );
}

const TABS = {
  student: [["library", "Class content"], ["quizzes", "Assessments"], ["progress", "My progress"], ["tutor", "AI Tutor"], ["comm", "Communicator"]],
  teacher: [["classes", "Classes"], ["library", "Materials"], ["quizzes", "Quizzes"], ["tutor", "AI Tutor"]],
  parent: [["parent", "My child"]],
  admin: [["admin", "Admin"], ["classes", "Classes"], ["library", "Materials"]],
};

export default function App() {
  const [me, setMe] = useState(null);
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState("");
  const [quizId, setQuizId] = useState(null);
  const [askId, setAskId] = useState(null);

  const loadMe = () => api("/me").then((u) => { setMe(u); setTab(TABS[u.role][0][0]); }).catch(() => setToken("")).finally(() => setReady(true));
  useEffect(() => { if (getToken()) loadMe(); else setReady(true); }, []);
  if (!ready) return null;
  if (!me) return <Auth onAuth={loadMe} />;

  const openQuiz = (id) => { setQuizId(id); setTab("quizzes"); };
  return (
    <>
      <div className="top">
        <span className="logo">Gnana</span>
        <div className="tabs">{TABS[me.role].map(([k, l]) => (
          <button key={k} className={"tab " + (tab === k ? "on" : "")} onClick={() => { setTab(k); setQuizId(null); }}>{l}</button>))}</div>
        <span>{me.name}</span><span className="badge">{me.role}</span>
        <button className="btn ghost" onClick={() => { setToken(""); setMe(null); }}>Log out</button>
      </div>
      <div className="wrap">
        {tab === "library" && <Library me={me} onOpenQuiz={openQuiz} onAsk={(id) => { setAskId(id); setTab("tutor"); }} />}
        {tab === "tutor" && <Tutor me={me} initialMaterial={askId} />}
        {tab === "comm" && <Communicator />}
        {tab === "quizzes" && <Quizzes me={me} openId={quizId} clearOpen={() => setQuizId(null)} />}
        {tab === "progress" && <ProgressView studentId={me.id} />}
        {tab === "classes" && <Classes me={me} />}
        {tab === "parent" && <Parent />}
        {tab === "admin" && <Admin />}
      </div>
    </>
  );
}
