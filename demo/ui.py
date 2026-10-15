"""Tiny Pillow UI toolkit that redraws the Gnana screens (same layout/colours as the React app) for demo videos."""
import textwrap
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
BG, CARD, INK, MUTE, BRAND, OK, BAD, WARN, LINE = "#f4f6fb", "#ffffff", "#1b2559", "#6b7699", "#3b5bdb", "#2f9e44", "#e03131", "#f08c00", "#e3e8f4"
SOFT = "#e8edff"


@lru_cache(None)
def font(size, bold=False):
    for n in (["DejaVuSans-Bold.ttf", "arialbd.ttf"] if bold else ["DejaVuSans.ttf", "arial.ttf"]):
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            pass
    return ImageFont.load_default()


class C:
    """Draw context: image, state, hotspots."""
    def __init__(self, s):
        self.img = Image.new("RGB", (W, H), BG)
        self.d = ImageDraw.Draw(self.img)
        self.s = s
        self.hs = {}

    def text(self, x, y, t, size=15, fill=INK, bold=False):
        self.d.text((x, y), t, font=font(size, bold), fill=fill)

    def wrap(self, x, y, t, width, size=15, fill=INK, lh=22, maxl=6):
        for i, ln in enumerate(textwrap.wrap(t, width)[:maxl]):
            self.text(x, y + i * lh, ln, size, fill)

    def box(self, x, y, w, h, fill=CARD, outline=LINE, r=12):
        self.d.rounded_rectangle([x, y, x + w, y + h], r, fill=fill, outline=outline)

    def pill(self, x, y, t, fill="#eef1fb", ink=MUTE):
        w = self.d.textlength(t, font=font(12)) + 18
        self.d.rounded_rectangle([x, y, x + w, y + 20], 10, fill=fill)
        self.text(x + 9, y + 3, t, 12, ink)
        return x + w + 6

    def button(self, name, x, y, w, label, kind="primary", h=36, disabled=False):
        bg, fg = {"primary": (BRAND, "#fff"), "ghost": (SOFT, BRAND), "danger": ("#ffe3e3", BAD)}[kind]
        if disabled:
            bg = "#a5b4f0"
        self.d.rounded_rectangle([x, y, x + w, y + h], 8, fill=bg)
        tw = self.d.textlength(label, font=font(14, True))
        self.text(x + (w - tw) / 2, y + (h - 17) / 2, label, 14, fg, True)
        self.hs[name] = (x + w / 2, y + h / 2)

    def field(self, name, x, y, w, label, h=36, kind="input", mask=False, ph=""):
        s = self.s
        self.text(x, y, label, 12, MUTE, True)
        by = y + 18
        focus = s.get("focus") == name
        self.d.rounded_rectangle([x, by, x + w, by + h], 8, fill="#fff", outline=BRAND if focus else LINE, width=2 if focus else 1)
        v = s.get(name, "")
        shown = "•" * len(v) if mask else v
        if kind == "file" and not v:
            shown, col = "Choose file…  no file selected", MUTE
        elif not v and ph:
            shown, col = ph, "#a0a8c4"
        else:
            col = INK
        if kind == "textarea":
            self.wrap(x + 10, by + 8, shown, int(w / 8.4), 14, col, 20, 2)
        else:
            self.text(x + 10, by + (h - 17) / 2, shown, 14, col)
        if focus and (s.get("t", 0) // 7) % 2 == 0 and kind != "select":
            cx = x + 10 + self.d.textlength(shown, font=font(14))
            self.d.line([cx + 1, by + 8, cx + 1, by + h - 8], fill=INK, width=2)
        if kind == "select":
            self.text(x + w - 22, by + (h - 17) / 2, "▾", 14, MUTE)
        self.hs[name] = (x + w / 2 if w < 400 else x + 160, by + h / 2)

    def bar(self, x, y, w, pct, color=None):
        color = color or (OK if pct >= 75 else WARN if pct >= 60 else BAD)
        self.d.rounded_rectangle([x, y, x + w, y + 9], 4, fill="#eef1fb")
        self.d.rounded_rectangle([x, y, x + max(8, w * pct / 100), y + 9], 4, fill=color)


TABS = {"student": ["Class content", "Assessments", "My progress", "AI Tutor", "Communicator"], "teacher": ["Classes", "Materials", "Quizzes"],
        "parent": ["My child"], "admin": ["Admin", "Classes", "Materials"]}
NAMES = {"student": "Aisha Khan", "teacher": "Mr. Rao", "parent": "Mrs. Khan", "admin": "School Admin"}


def browser(c):
    c.d.rectangle([0, 0, W, 36], fill="#dde3f3")
    for i, col in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        c.d.ellipse([14 + i * 22, 12, 26 + i * 22, 24], fill=col)
    c.d.rounded_rectangle([110, 6, 900, 30], 12, fill="#fff")
    url = c.s.get("url", "")
    c.text(126, 9, ("http://" if url else "") + url, 14, INK)
    if c.s.get("focus") == "url" and (c.s.get("t", 0) // 7) % 2 == 0:
        x = 126 + c.d.textlength(("http://" if url else "") + url, font=font(14))
        c.d.line([x, 10, x, 26], fill=INK, width=2)
    c.hs["url"] = (500, 18)


def topbar(c):
    s = c.s
    c.d.rectangle([0, 36, W, 90], fill=CARD)
    c.d.line([0, 90, W, 90], fill=LINE)
    c.text(24, 52, "Gnana", 22, BRAND, True)
    x = 120
    for t in TABS[s["role"]]:
        w = c.d.textlength(t, font=font(14, True)) + 28
        if s.get("tab") == t:
            c.d.rounded_rectangle([x, 47, x + w, 79], 8, fill=SOFT)
        c.text(x + 14, 55, t, 14, BRAND if s.get("tab") == t else MUTE, True)
        c.hs["tab:" + t] = (x + w / 2, 63)
        x += w + 6
    c.text(930, 55, NAMES[s["role"]], 14)
    c.pill(1040, 53, s["role"], SOFT, BRAND)
    c.button("logout", 1120, 48, 120, "Log out", "ghost", 32)


def caption(c):
    cap = c.s.get("cap", "")
    if not cap:
        return
    c.d.rectangle([0, H - 78, W, H], fill=INK)
    step = c.s.get("step", "")
    if step:
        c.d.rounded_rectangle([30, H - 62, 30 + 44, H - 20], 10, fill=BRAND)
        c.text(30 + 22 - c.d.textlength(step, font=font(22, True)) / 2, H - 55, step, 22, "#fff", True)
    for i, ln in enumerate(textwrap.wrap(cap, 98)[:2]):
        c.text(96, H - 66 + i * 28, ln, 20, "#fff")


# ---------------- screens ----------------
def login(c):
    s = c.s
    c.box(440, 100, 400, 470)
    c.text(470, 125, "Gnana", 30, BRAND, True)
    c.text(470, 170, "Learn from anything. Upload it, understand it,", 12, MUTE)
    c.text(470, 188, "test yourself, track progress.", 12, MUTE)
    c.field("email", 470, 225, 340, "Email", ph="you@school.org")
    c.field("password", 470, 295, 340, "Password", mask=True)
    c.button("login", 470, 380, 340, "Log in", h=40)
    c.text(520, 440, "New here? Create an account", 14, MUTE)
    c.hs["register"] = (640, 449)
    if s.get("hint"):
        c.box(470, 480, 340, 60, "#fff8e1", "#ffe08a", 8)
        c.wrap(484, 490, s["hint"], 42, 13, "#7a5b00", 19, 2)


def library(c):
    s = c.s
    teacher = s["role"] != "student"
    c.box(40, 104, 1200, 322)
    c.text(60, 118, "Add learning material", 20, INK, True)
    c.field("title", 60, 156, 320, "Title (optional)", ph="e.g. Photosynthesis")
    c.field("level", 400, 156, 230, "Learner level", kind="select")
    if teacher:
        c.field("share", 650, 156, 260, "Share with class", kind="select")
    c.field("file", 60, 226, 1140, "File: PDF, Word, PowerPoint, text, image, audio or video", kind="file")
    c.field("text", 60, 296, 1140, "…or paste text", h=40, kind="textarea")
    c.button("analyse", 60, 372, 220, "Analysing…" if s.get("busy") else "Analyse & summarise", disabled=bool(s.get("busy")))
    c.text(60, 442, "Your library", 20, INK, True)
    for i, (t, k, tags, sm) in enumerate(s.get("lib", [])[:3]):
        x = 40 + i * 405
        c.box(x, 480, 390, 140)
        c.text(x + 16, 494, t, 16, INK, True)
        c.pill(x + 310, 494, k)
        c.wrap(x + 16, 524, sm, 46, 13, MUTE, 19, 2)
        px = x + 16
        for tg in tags[:3]:
            px = c.pill(px, 584, tg)
        c.hs[f"lib:{i}"] = (x + 195, 550)


def detail(c):
    s = c.s
    c.button("back", 40, 100, 90, "← Back", "ghost", 32)
    c.box(40, 142, 1200, 236)
    c.text(60, 154, s.get("mtitle", "Photosynthesis basics"), 21, INK, True)
    c.pill(1100, 156, "document · high school")
    c.text(60, 190, "Summary", 15, INK, True)
    c.wrap(60, 212, "Photosynthesis is how green plants turn light energy into chemical energy. Chlorophyll in the chloroplasts absorbs sunlight, "
           "and the plant uses carbon dioxide and water to make glucose, releasing oxygen as a by-product.", 138, 14, INK, 20, 3)
    c.text(60, 282, "Key points", 15, INK, True)
    for i, k in enumerate(["Chlorophyll absorbs sunlight in the chloroplasts", "CO₂ + water → glucose + oxygen",
                           "Light-dependent reactions happen in the thylakoids"]):
        c.text(70, 304 + i * 22, "• " + k, 14, INK)
    vs = s.get("video", "none")
    c.box(40, 392, 590, 236)
    c.text(60, 406, "Explainer video", 17, INK, True)
    if vs == "none":
        c.button("genvideo", 60, 444, 170, "Generate video")
    elif vs == "processing":
        c.text(60, 450, "Rendering your video… this takes a minute.", 14, MUTE)
        c.bar(60, 480, 300, 45, BRAND)
    else:
        c.d.rounded_rectangle([60, 440, 610, 612], 10, fill="#0d1330")
        c.d.polygon([(310, 500), (310, 552), (354, 526)], fill="#fff")
    c.box(650, 392, 590, 236)
    c.text(670, 406, "Questions", 17, INK, True)
    c.field("kind", 670, 442, 160, "Type", kind="select")
    c.field("count", 850, 442, 90, "How many")
    c.button("genquiz", 960, 460, 150, "Generate")
    for i, q in enumerate(s.get("quizlist", [])):
        c.text(670, 540 + i * 26, q, 14, INK)
        c.button(f"openquiz:{i}", 1130, 534 + i * 26, 90, "Open", "ghost", 26)


def quiz(c):
    s = c.s
    c.button("back", 40, 100, 90, "← Back", "ghost", 32)
    c.box(40, 142, 1200, 486)
    c.text(60, 156, s.get("qtitle", "Quiz: Photosynthesis basics"), 21, INK, True)
    qs = [("1. Which pigment absorbs sunlight in plants?", "Topic: chlorophyll", ["Chlorophyll", "Haemoglobin", "Keratin", "Melanin"]),
          ("2. True or false: Plants release oxygen as a by-product.", "Topic: photosynthesis", ["True", "False"])]
    y = 200
    for qi, (q, tp, opts) in enumerate(qs):
        c.text(60, y, q, 16, INK, True)
        c.pill(1100, y + 2, tp.replace("Topic: ", ""))
        y += 32
        for oi, o in enumerate(opts):
            sel = s.get(f"q{qi}") == o
            c.d.rounded_rectangle([60, y, 700, y + 34], 8, fill="#eef2ff" if sel else "#fff", outline=BRAND if sel else LINE)
            c.d.ellipse([74, y + 10, 88, y + 24], outline=BRAND if sel else MUTE, width=2, fill=BRAND if sel else "#fff")
            c.text(104, y + 8, o, 14, INK)
            c.hs[f"q{qi}:{o}"] = (380, y + 17)
            y += 40
        y += 14
    c.button("submit", 60, 560, 140, "Submit")


def result(c):
    c.box(40, 104, 1200, 100)
    c.text(60, 118, "Result: 50%", 26, INK, True)
    c.text(60, 160, "1.0 / 2   —   review your answers below", 14, MUTE)
    c.button("done", 1080, 130, 140, "Done")
    c.box(40, 220, 1200, 130)
    c.d.rectangle([40, 232, 44, 338], fill=OK)
    c.text(64, 234, "1. Which pigment absorbs sunlight in plants?", 15, INK, True)
    c.text(64, 262, "Your answer: Chlorophyll", 14, INK)
    c.text(64, 290, "✓ Correct", 14, OK, True)
    c.box(40, 366, 1200, 190)
    c.d.rectangle([40, 378, 44, 544], fill=BAD)
    c.text(64, 380, "2. True or false: Plants release oxygen as a by-product.", 15, INK, True)
    c.text(64, 408, "Your answer: False", 14, INK)
    c.text(64, 436, "Correct answer: True", 14, INK, True)
    c.text(64, 466, "Explanation: Oxygen is released when water is split in the light reactions.", 13, MUTE)


def _stats(c, y=104, h=76):
    st = [("Average score", "72%"), ("Attempts", "14"), ("Trend", "improving"), ("Day streak", "5")]
    for i, (a, b) in enumerate(st):
        x = 40 + i * 303
        c.box(x, y, 290, h)
        c.text(x + 16, y + 10, a, 12, MUTE)
        c.text(x + 16, y + 30, b, 26 if i != 2 else 20, INK, True)


def _sw(c, y, h):
    c.box(40, y, 590, h)
    c.text(60, y + 12, "Where they're strong", 17, INK, True)
    for i, (t, p) in enumerate([("Photosynthesis", 92), ("Cell structure", 81)]):
        c.text(60, y + 46 + i * 44, t, 14, INK, True)
        c.text(520, y + 46 + i * 44, f"{p}%", 13, MUTE)
        c.bar(60, y + 70 + i * 44, 540, p)
    c.box(650, y, 590, h)
    c.text(670, y + 12, "Where they need work", 17, INK, True)
    for i, (t, p) in enumerate([("Genetics", 42), ("Cell division", 55)]):
        c.text(670, y + 46 + i * 44, t, 14, INK, True)
        c.text(1130, y + 46 + i * 44, f"{p}%", 13, MUTE)
        c.bar(670, y + 70 + i * 44, 540, p)


def progress(c):
    c.text(40, 100, "Aisha Khan", 22, INK, True)
    c.pill(190, 106, "high school", SOFT, BRAND)
    _stats(c, 136, 70)
    c.box(40, 218, 1200, 190)
    c.text(60, 228, "Daily performance", 17, INK, True)
    data = [48, 55, 52, 63, 70, 68, 76]
    pts = [(80 + i * 180, 392 - d * 1.35) for i, d in enumerate(data)]
    for g in (0, 50, 100):
        yy = 392 - g * 1.35
        c.d.line([60, yy, 1220, yy], fill=LINE)
    c.d.line(pts, fill=BRAND, width=3)
    for i, (x, y) in enumerate(pts):
        c.d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=BRAND)
        c.text(x - 16, 396, f"Oct {9 + i}", 10, MUTE)
    _sw(c, 424, 200)


def progress_fb(c):
    s = c.s
    c.text(40, 100, "Aisha Khan", 22, INK, True)
    c.pill(190, 106, "high school", SOFT, BRAND)
    if s["role"] in ("teacher", "admin"):
        c.button("back", 1130, 98, 110, "← Back", "ghost", 30)
    _stats(c, 136, 66)
    _sw(c, 214, 140)
    c.box(40, 368, 1200, 262)
    c.text(60, 380, "Feedback", 17, INK, True)
    c.button("aifb", 1030, 376, 190, "Generate AI feedback", "ghost", 32)
    if s.get("fb_ai"):
        c.d.rounded_rectangle([60, 420, 1220, 500], 10, fill="#f8faff", outline=LINE)
        c.text(74, 428, "AI tutor · just now", 12, MUTE)
        c.wrap(74, 448, "Aisha averages 72% and is improving. Strong in photosynthesis and cell structure. Needs practice in genetics: "
               "revisit the summary and retake the quiz on inheritance and Punnett squares.", 135, 14, INK, 20, 2)
    if s["role"] in ("teacher", "admin"):
        c.field("note", 60, 508, 1000, "Your feedback", h=40, kind="textarea", ph="Write your own feedback…")
        c.button("post", 1080, 526, 140, "Post feedback")
    elif s.get("fb_ai") is None:
        c.text(60, 430, "No feedback yet.", 14, MUTE)


def classes(c):
    s = c.s
    c.box(40, 104, 1200, 110)
    c.text(60, 116, "Create a class", 20, INK, True)
    c.field("cname", 60, 150, 400, "", ph="e.g. Grade 9 Biology")
    c.button("create", 480, 168, 120, "Create")
    for i, (n, k) in enumerate(s.get("classes", [])):
        x = 40 + i * 405
        c.box(x, 236, 390, 120)
        c.text(x + 16, 250, n, 17, INK, True)
        c.text(x + 16, 280, f"{k} students", 14, MUTE)
        c.button(f"open:{i}", x + 16, 308, 90, "Open", "primary", 32)


def classdetail(c):
    s = c.s
    c.button("back", 40, 100, 100, "← Classes", "ghost", 32)
    c.box(40, 144, 1200, 100)
    c.text(60, 154, "Add student by email", 17, INK, True)
    c.field("semail", 60, 178, 420, "", ph="student@school.org")
    c.button("addstu", 500, 196, 90, "Add")
    c.box(40, 260, 1200, 360)
    c.text(60, 272, "Class progress — Grade 9 Biology", 17, INK, True)
    for i, h in enumerate(["Student", "Avg", "Attempts", "Trend", "Strong", "Needs work"]):
        c.text([60, 270, 400, 500, 640, 840][i], 308, h, 13, MUTE, True)
    rows = [("Aisha Khan", 72, 14, "improving", "photosynthesis", "genetics"), ("Ben Ortiz", 85, 11, "steady", "cell structure", "—"),
            ("Chloe Lin", 54, 6, "declining", "—", "photosynthesis")]
    for i, r in enumerate(rows[: s.get("nrows", 0)]):
        y = 340 + i * 56
        c.d.line([60, y - 8, 1220, y - 8], fill=LINE)
        c.text(60, y + 6, r[0], 14, INK)
        c.bar(270, y + 12, 100, r[1])
        c.text(380 - 4 + 0, y + 6, "", 13)
        c.text(400, y + 6, str(r[2]), 14, INK)
        c.text(500, y + 6, r[3], 14, INK)
        c.pill(640, y + 6, r[4], "#e6f6ea" if r[4] != "—" else "#eef1fb", OK if r[4] != "—" else MUTE)
        c.pill(840, y + 6, r[5], "#ffe9e9" if r[5] != "—" else "#eef1fb", BAD if r[5] != "—" else MUTE)
        c.button(f"details:{i}", 1100, y, 100, "Details", "ghost", 30)


def admin(c):
    s = c.s
    for i, (a, b) in enumerate([("Students", "24"), ("Teachers", "3"), ("Parents", "18"), ("Materials", "41"), ("Quizzes", "77"), ("Platform avg", "71%")]):
        x = 40 + i * 202
        c.box(x, 104, 190, 66)
        c.text(x + 14, 112, a, 12, MUTE)
        c.text(x + 14, 130, b, 24, INK, True)
    c.box(40, 184, 590, 262)
    c.text(60, 196, "Create user", 18, INK, True)
    c.field("uname", 60, 228, 260, "Name")
    c.field("uemail", 340, 228, 270, "Email")
    c.field("urole", 60, 298, 260, "Role", kind="select")
    c.field("upass", 340, 298, 270, "Password", mask=True)
    c.button("createuser", 60, 380, 140, "Create")
    if s.get("msg1"):
        c.text(220, 390, s["msg1"], 14, OK, True)
    c.box(650, 184, 590, 262)
    c.text(670, 196, "Link parent to student", 18, INK, True)
    c.field("pemail", 670, 228, 550, "Parent email")
    c.field("lemail", 670, 298, 550, "Student email")
    c.button("link", 670, 380, 140, "Link")
    if s.get("msg2"):
        c.text(830, 390, s["msg2"], 14, OK, True)
    c.box(40, 460, 1200, 166)
    c.text(60, 470, "All users", 17, INK, True)
    rows = [("Aisha Khan", "aisha@school.org", "student"), ("Mr. Rao", "rao@school.org", "teacher")]
    if s.get("newuser"):
        rows.append((s["newuser"], "meera@school.org", "teacher"))
    for i, (n, e, r) in enumerate(rows[:3]):
        y = 500 + i * 40
        c.d.line([60, y - 4, 1220, y - 4], fill=LINE)
        c.text(60, y + 6, n, 14, INK)
        c.text(330, y + 6, e, 14, INK)
        c.pill(620, y + 8, r, SOFT, BRAND)
        if r == "student":
            c.button("userprog", 1000, y, 100, "Progress", "ghost", 28)
        c.button(f"del:{i}", 1110, y, 90, "Delete", "danger", 28)


def s_content(c):
    c.text(40, 104, "Class content from your teachers", 22, INK, True)
    items = [("Photosynthesis basics", "video", ["photosynthesis"], "Mr. Rao", "Green plants turn light into chemical energy."),
             ("Cell structure notes", "pdf", ["cells"], "Mr. Rao", "Organelles and their functions in animal cells."),
             ("Genetics worksheet", "document", ["genetics"], "Ms. Devi", "Inheritance, alleles and Punnett squares.")]
    for i, (t, k, tags, by, sm) in enumerate(items):
        x = 40 + i * 405
        c.box(x, 150, 390, 150)
        c.text(x + 16, 164, t, 16, INK, True)
        c.pill(x + 320, 164, k)
        c.text(x + 16, 192, "Posted by " + by, 13, MUTE)
        c.wrap(x + 16, 218, sm, 46, 13, MUTE, 19, 2)
        c.pill(x + 16, 264, tags[0])
        c.hs[f"item:{i}"] = (x + 195, 230)
    c.box(40, 330, 1200, 80, "#fff8e1", "#ffe08a", 12)
    c.text(60, 346, "Students can view, summarise and take assessments here.", 15, "#7a5b00", True)
    c.text(60, 372, "Only teachers can upload or create content.", 14, "#7a5b00")


def s_detail(c):
    s = c.s
    c.button("back", 40, 100, 90, "← Back", "ghost", 32)
    c.box(40, 142, 1200, 200)
    c.text(60, 154, "Photosynthesis basics", 21, INK, True)
    c.pill(1100, 156, "video · posted by Mr. Rao")
    c.d.rounded_rectangle([60, 192, 420, 328], 8, fill="#0d1330")
    c.d.polygon([(215, 238), (215, 282), (253, 260)], fill="#fff")
    c.text(440, 196, "Summary", 15, INK, True)
    c.wrap(440, 218, "Plants turn light energy into chemical energy. Chlorophyll absorbs sunlight and the plant makes glucose from CO₂ and water, releasing oxygen.", 95, 14, INK, 20, 3)
    c.box(40, 356, 1200, 140)
    c.text(60, 368, "Summarise this for me", 17, INK, True)
    c.field("slang", 60, 394, 280, "", kind="select")
    c.button("summarise", 360, 412, 150, "Summarise")
    if s.get("sum"):
        c.wrap(540, 400, s["sum"], 78, 14, INK, 21, 3)
    c.box(40, 510, 590, 118)
    c.text(60, 522, "Learn with the AI tutor", 17, INK, True)
    c.button("asktutor", 60, 560, 230, "Ask the tutor about this")
    c.box(650, 510, 590, 118)
    c.text(670, 522, "Assessments", 17, INK, True)
    c.text(670, 556, "Assessment: Photosynthesis basics (10 q)", 14, INK)
    c.button("startquiz", 1120, 550, 100, "Start", "ghost", 30)


def tutor(c):
    s = c.s
    c.box(40, 100, 1200, 78)
    c.text(60, 108, "AI Tutor", 20, INK, True)
    c.field("tlang", 300, 106, 300, "Language mode", h=34, kind="select")
    c.field("tmat", 620, 106, 360, "Lesson to study", h=34, kind="select")
    c.text(1010, 130, "[ ] Read replies aloud", 13, MUTE)
    c.box(40, 190, 1200, 380)
    y = 204
    for who, t in s.get("chat", []):
        lines = textwrap.wrap(t, 88)[:5]
        h = 20 * len(lines) + 20
        w = 700
        x = 1220 - w if who == "me" else 60
        c.d.rounded_rectangle([x, y, x + w, y + h], 12, fill=BRAND if who == "me" else "#eef1fb")
        for i, ln in enumerate(lines):
            c.text(x + 14, y + 10 + i * 20, ln, 14, "#fff" if who == "me" else INK)
        y += h + 10
    if s.get("thinking"):
        c.text(60, y, "Tutor is thinking…", 13, MUTE)
    c.box(40, 580, 1200, 54)
    c.button("mic", 52, 590, 110, "Speak" if not s.get("listening") else "● Listening", "ghost", 34)
    c.field("tmsg", 176, 580, 960, "", h=34, ph="Ask in Telugu, English, or Telugu typed in English letters…")
    c.button("send", 1150, 590, 80, "Send", h=34)


def _comm_head(c, active):
    s = c.s
    for i, (a, b) in enumerate([("Level", "high school"), ("Day streak", str(s.get("cstreak", 5))),
                                ("Today", f"{s.get('cdone', 0)}/3"), ("XP", str(s.get("cxp", 240)))]):
        x = 40 + i * 303
        c.box(x, 100, 290, 62)
        c.text(x + 14, 106, a, 12, MUTE)
        c.text(x + 14, 124, b, 22 if i else 17, INK, True)
    for i, (k, l) in enumerate([("ctab:today", "Today's tasks"), ("ctab:practice", "Practice conversation"), ("ctab:skills", "My skills")]):
        w = c.d.textlength(l, font=font(14, True)) + 36
        x = 40 + sum(c.d.textlength(t, font=font(14, True)) + 46 for t in ["Today's tasks", "Practice conversation", "My skills"][:i])
        c.d.rounded_rectangle([x, 174, x + w, 208], 8, fill=BRAND if active == i else SOFT)
        c.text(x + 18, 183, l, 14, "#fff" if active == i else BRAND, True)
        c.hs[k] = (x + w / 2, 191)


def comm_today(c):
    s = c.s
    _comm_head(c, 0)
    tasks = [("Speak: how to manage exam stress", "Speaking", "Speak for about 60 seconds. Open clearly, give one example, finish with a closing sentence."),
             ("Write", "Writing", "Write a formal email to your principal requesting a new club. Aim for at least 100 words."),
             ("Word power", "Vocabulary", "Use each word in a sentence, then join them in a short paragraph: persuade, resilient, evidence.")]
    done = s.get("cdone", 0)
    for i, (t, k, p) in enumerate(tasks):
        x = 40 + i * 405
        c.box(x, 226, 390, 220)
        c.text(x + 16, 240, t, 16, INK, True)
        c.pill(x + 16, 270, "done · +38 XP" if i < done else k, "#e6f6ea" if i < done else "#eef1fb", OK if i < done else MUTE)
        c.wrap(x + 16, 302, p, 44, 13, MUTE, 19, 4)
        c.button(f"task:{i}", x + 16, 396, 120, "See feedback" if i < done else "Start", "ghost" if i < done else "primary", 34)
    c.box(40, 462, 1200, 150, "#eef2ff", "#c9d4ff", 12)
    c.text(60, 476, "Tasks change with your class level", 16, BRAND, True)
    c.text(60, 506, "Primary: 30-second talk about your favourite animal   |   High school: 60-second talk on exam stress", 14, INK)
    c.text(60, 532, "Undergraduate: 90-second internship pitch   |   Postgraduate: explain your thesis to a non-expert", 14, INK)
    c.text(60, 558, "Professional: 60-second status update to a client", 14, INK)


def comm_task(c):
    s = c.s
    c.button("back", 40, 100, 90, "← Back", "ghost", 32)
    big = not s.get("cfeed")
    c.box(40, 142, 1200, 250 if big else 130)
    c.text(60, 154, "Speak: how to manage exam stress", 20, INK, True)
    c.pill(1120, 158, "Speaking")
    c.text(60, 188, "Speak for about 60 seconds. Open clearly, give one example, finish with a closing sentence.", 14, INK)
    if big:
        c.button("cmic", 60, 220, 150, "● Stop (%ds)" % s.get("csecs", 0) if s.get("clisten") else "Speak", "primary", 34)
        c.field("ctext", 60, 262, 1140, "", h=70, kind="textarea", ph="Your speech appears here (or type it)…")
        c.text(60, 346, f"{len((s.get('ctext') or '').split())}/100 words", 13, MUTE)
        c.text(780, 346, "[x] Explain feedback in Telugu too", 13, MUTE)
        c.button("cfb", 1070, 338, 150, "Get feedback", "primary", 34)
    else:
        c.wrap(60, 214, "Exam stress is common. I manage it by planning early, taking short breaks and sleeping well. For example, last term I made a timetable...", 130, 13, MUTE, 19, 2)
        c.box(40, 286, 1200, 344)
        c.text(60, 298, "Your feedback · +38 XP", 18, INK, True)
        for i, (k, v) in enumerate([("clarity", 4), ("grammar", 3), ("vocabulary", 4), ("structure", 4), ("fluency", 3)]):
            y = 332 + i * 26
            c.text(60, y, k.capitalize(), 13, INK)
            c.bar(160, y + 5, 300, v * 20)
            c.text(472, y, f"{v}/5", 12, MUTE)
        c.pill(60, 466, "104 words"); c.pill(150, 466, "128 words/min", "#eef1fb"); c.pill(280, 466, "2 fillers", "#e6f6ea", OK)
        c.text(540, 298, "What you did well", 15, INK, True)
        c.text(540, 324, "• Clear opening and a real example", 13, INK)
        c.text(540, 346, "• Good pace (128 words per minute)", 13, INK)
        c.text(540, 380, "Improve next", 15, INK, True)
        c.text(540, 406, "• 'I am agree' → 'I agree'", 13, INK)
        c.text(540, 428, "• Replace 'like' / 'um' with a short pause", 13, INK)
        c.text(540, 462, "Tip for tomorrow", 15, INK, True)
        c.text(540, 488, "End with one clear closing sentence.", 13, INK)
        c.text(60, 510, "A stronger version", 15, INK, True)
        c.wrap(60, 536, "I manage exam stress by planning early, taking short breaks and sleeping well. For example, last term I made a timetable and finished revising two days early.", 150, 13, INK, 19, 2)


def comm_chat(c):
    s = c.s
    _comm_head(c, 1)
    c.field("cscen", 40, 220, 360, "", h=34, kind="select")
    c.button("cstart", 420, 238, 170, "Start role-play", "primary", 34)
    c.box(40, 280, 1200, 280)
    y = 292
    for who, t in s.get("cchat", []):
        say, _, coach = t.partition("\nCoach:")
        lines = textwrap.wrap(say, 82)[:3]
        h = 20 * len(lines) + 16 + (30 if coach else 0)
        w = 680
        x = 1220 - w if who == "me" else 60
        c.d.rounded_rectangle([x, y, x + w, y + h], 12, fill=BRAND if who == "me" else "#eef1fb")
        for i, ln in enumerate(lines):
            c.text(x + 14, y + 8 + i * 20, ln, 14, "#fff" if who == "me" else INK)
        if coach:
            cy = y + 12 + 20 * len(lines)
            c.d.rounded_rectangle([x + 10, cy, x + w - 10, cy + 26], 6, fill="#fff8e1")
            c.text(x + 18, cy + 5, "Coach: " + coach.strip()[:92], 12, "#7a5b00")
        y += h + 8
    c.box(40, 574, 1200, 54)
    c.button("cmic2", 52, 584, 110, "Speak", "ghost", 34)
    c.field("cmsg", 176, 574, 960, "", h=34, ph="Say or type your reply…")
    c.button("csend", 1150, 584, 80, "Send", h=34)


SCREENS = {"comm_today": comm_today, "comm_task": comm_task, "comm_chat": comm_chat, "s_content": s_content, "s_detail": s_detail, "tutor": tutor, "login": login, "library": library, "detail": detail, "quiz": quiz, "result": result, "progress": progress,
           "progress_fb": progress_fb, "classes": classes, "classdetail": classdetail, "admin": admin}


def render(s):
    c = C(s)
    browser(c)
    if s["screen"] != "login":
        topbar(c)
    SCREENS[s["screen"]](c)
    # field "level"/"kind"/etc. need their values
    caption(c)
    return c
