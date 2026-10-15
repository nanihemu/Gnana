# Gnana

Upload anything (PDF, Word, PowerPoint, text, image, audio, video) and get a level-appropriate summary, an explainer video, quizzes and assessments, plus day-to-day performance tracking with feedback. Four roles: student, teacher, parent, admin.

## Run it

Needs Python 3.10+, Node 18+, and `ffmpeg` on PATH (video generation, audio extraction).

```bash
# Backend
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # optional but strongly recommended (Windows: set ANTHROPIC_API_KEY=...)
export GNANA_SECRET=change-me              # JWT signing key
uvicorn app.main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev                              # http://localhost:5173 (proxies /api to :8000)
```

Production: `npm run build` in `frontend`, then the backend serves `frontend/dist` itself at http://localhost:8000.

The first account registered may choose "Admin". After that, admins create other admins; everyone else self-registers.

## Roles

| Role | Can do |
|---|---|
| Student | **View-only** access to what their teachers post to their class (videos, notes, materials, assessments); summarise lessons (English/Telugu); take assessments; see own scores, performance and feedback; use the AI Tutor. Cannot upload or create content. |
| Teacher | Create classes, enrol students, upload/post materials (original video, notes, files are playable by students), generate videos and assessments, see class progress, write feedback |
| Parent | See linked children's daily progress, strengths, weaknesses, feedback (read-only) |
| Admin | Manage users, link parents to students, platform stats, view any student |

## AI Tutor (teaching and conversation agent)

Students (and teachers) get an AI Tutor tab with three modes: **Telugu → English** (ask in Telugu, Telugu typed in English letters, or English; it restates the question in English, answers in simple English and explains the key idea in Telugu), **English → English** (simple explanations plus gentle corrections of the student's English), and **Telugu only**. It can be anchored to a teacher-posted lesson and knows the student's weak topics. Voice: the browser mic (te-IN / en-IN) for input and speech synthesis for reading replies aloud (Chrome/Edge; Telugu voice availability depends on the device). Telugu needs `ANTHROPIC_API_KEY`; without it only a basic English lookup in the lesson works.

## AI Communicator (communication-skills coach)

A **Communicator** tab for students with three parts:

- **Daily tasks (3 per day, different for every class level):** one speaking, one writing, one vocabulary task, chosen from level-specific banks in `backend/app/comm.py` (primary, middle school, high school, undergraduate, postgraduate, professional). Targets scale with level, e.g. 30s/25 words for primary up to 120s/200 words for postgraduate. A student's level comes from their profile.
- **AI feedback on every task:** scores (1–5) for clarity, grammar, vocabulary, structure (plus fluency for speaking), strengths, specific fixes, a stronger rewrite of their own text, a tip for tomorrow, optional Telugu explanation. Speaking uses the browser mic to transcribe; filler words and pace (words/min) are measured. Pronunciation and tone of voice are not assessed since only the transcript is analysed.
- **Role-play practice:** level-appropriate scenarios (e.g. meet a friend, school council Q&A, internship interview, conference Q&A, client negotiation). The AI partner stays in character and adds a "Coach:" note after every reply.

Streak, XP, per-skill and per-criterion averages are tracked and shown to the student, and also on the progress view that teachers and parents see. Teachers can assign their own communication task to a whole class (Classes → open class → "Assign a communication task"). Without `ANTHROPIC_API_KEY` you only get basic metric-based feedback.

## How it works

- `extract.py`: file to text. PDF/DOCX/PPTX/text parsed locally; images via Claude vision (OCR fallback); audio/video via faster-whisper (optional `pip install faster-whisper`).
- `ai.py`: summary, key points, topics, questions (MCQ, true/false, short answer), short-answer grading, video script, feedback. Uses Claude when `ANTHROPIC_API_KEY` is set; otherwise a basic offline fallback so you can demo without a key (quality is much lower).
- `video.py`: slides drawn with Pillow, narration via gTTS (needs internet; silent if unavailable), stitched with ffmpeg.
- `analytics.py`: per-topic accuracy, daily series, trend, streak, strengths (75%+) and weak areas (<60%).

## Known limits (prototype)

- SQLite, JWT in localStorage, no rate limiting, no email verification or password reset.
- Video generation runs in a background thread, not a job queue.
- Deleting a user leaves their materials/quizzes orphaned.
- Student/child data is sensitive: add consent flows, data retention rules and HTTPS before real use with minors.

## Ideas for next steps

Adaptive difficulty from weak topics, spaced-repetition reminders, LMS/Google Classroom import, YouTube URL ingestion, multilingual output, proctoring-free integrity checks, mobile app.

## Troubleshooting and tests

- **Check a deployment:** open `http://SERVER:8000/api/health`. It shows whether the AI key works (`ai.working`, reason in `ai.error`), whether ffmpeg exists and whether the data folder is writable.
- **Changing `.env`:** run `docker compose up -d --force-recreate` (a plain `restart` does not reload it). No quotes or spaces around the key.
- **Automated tests (28):** role-by-endpoint permission matrix, class sharing, uploads, quizzes, progress, video, communicator, admin:

```bash
docker compose exec -T gnana sh -c "pip install --user -q pytest httpx && python -m pytest tests -q"
```
