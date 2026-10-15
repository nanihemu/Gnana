import React, { useEffect, useRef, useState } from "react";
import { api } from "./api.js";

const LANGS = {
  en: { label: "English → English", stt: "en-IN", tts: "en-IN", hello: "Hi! Ask me anything about your lesson. I'll explain in simple English and help fix your English too." },
  te_en: { label: "తెలుగు → English", stt: "te-IN", tts: "en-IN", hello: "నమస్కారం! Ask in Telugu or English. నేను English లో సమాధానం చెప్పి, తెలుగులో కూడా వివరిస్తాను." },
  te: { label: "తెలుగు (Telugu only)", stt: "te-IN", tts: "te-IN", hello: "నమస్కారం! మీ పాఠం గురించి తెలుగులో ఏదైనా అడగండి." },
};

const SR = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

export function Tutor({ me, initialMaterial }) {
  const [lang, setLang] = useState("te_en");
  const [mats, setMats] = useState([]);
  const [mid, setMid] = useState(initialMaterial || "");
  const [msgs, setMsgs] = useState([{ role: "assistant", content: LANGS.te_en.hello }]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [speak, setSpeak] = useState(false);
  const end = useRef();
  const rec = useRef();

  useEffect(() => { api("/materials").then(setMats).catch(() => {}); }, []);
  useEffect(() => { if (initialMaterial) setMid(String(initialMaterial)); }, [initialMaterial]);
  useEffect(() => { end.current && end.current.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const say = (t) => {
    if (!speak || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(t.replace(/[*_#`]/g, ""));
    u.lang = LANGS[lang].tts;
    window.speechSynthesis.speak(u);
  };

  const send = async (override) => {
    const message = (override ?? text).trim();
    if (!message || busy) return;
    const history = msgs.slice(1);
    setMsgs((m) => [...m, { role: "user", content: message }]);
    setText(""); setBusy(true);
    try {
      const r = await api("/tutor/chat", { method: "POST", body: { message, lang, material_id: mid ? +mid : null, history } });
      setMsgs((m) => [...m, { role: "assistant", content: r.reply }]);
      say(r.reply);
    } catch (e) {
      setMsgs((m) => [...m, { role: "assistant", content: "Sorry, something went wrong: " + e.message }]);
    }
    setBusy(false);
  };

  const mic = () => {
    if (!SR) return alert("Voice input isn't supported in this browser. Try Chrome or Edge.");
    if (listening) { rec.current && rec.current.stop(); return; }
    const r = new SR();
    r.lang = LANGS[lang].stt; r.interimResults = false;
    r.onresult = (e) => { const t = e.results[0][0].transcript; setText(t); send(t); };
    r.onend = () => setListening(false);
    r.onerror = () => setListening(false);
    rec.current = r; setListening(true); r.start();
  };

  const changeLang = (l) => { setLang(l); setMsgs([{ role: "assistant", content: LANGS[l].hello }]); };

  return (
    <div>
      <div className="card">
        <div className="row spread">
          <h2>AI Tutor</h2>
          <label className="row" style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={speak} onChange={(e) => setSpeak(e.target.checked)} /> Read replies aloud</label>
        </div>
        <div className="grid">
          <div><label>Language mode</label>
            <select value={lang} onChange={(e) => changeLang(e.target.value)}>{Object.entries(LANGS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select></div>
          <div><label>Lesson to study (optional)</label>
            <select value={mid} onChange={(e) => setMid(e.target.value)}><option value="">General help</option>
              {mats.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}</select></div>
        </div>
      </div>
      <div className="card" style={{ minHeight: 340 }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", margin: ".5rem 0" }}>
            <div style={{ maxWidth: "80%", whiteSpace: "pre-wrap", padding: ".6rem .85rem", borderRadius: 12,
              background: m.role === "user" ? "#3b5bdb" : "#eef1fb", color: m.role === "user" ? "#fff" : "#1b2559" }}>{m.content}</div>
          </div>))}
        {busy && <p className="muted">Tutor is thinking…</p>}
        <div ref={end} />
      </div>
      <div className="card row">
        <button className="btn ghost" onClick={mic} title="Speak">{listening ? "● Listening…" : "🎤 Speak"}</button>
        <input style={{ flex: 1, minWidth: 200 }} value={text} placeholder={lang === "en" ? "Type your question…" : "తెలుగులో లేదా English లో అడగండి…"}
          onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} />
        <button className="btn" disabled={busy} onClick={() => send()}>Send</button>
      </div>
      <div className="row">
        {["Explain this lesson simply", "Give me an example", "Quiz me with one question", "Help me say this in English"].map((q) => (
          <button key={q} className="btn ghost" onClick={() => send(q)}>{q}</button>))}
      </div>
    </div>
  );
}
