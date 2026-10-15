"""Render screen-recording style demo videos (cursor, typing, clicks, captions) for each Gnana role.
Usage: python make_demo_videos.py [outdir] [role ...]
Needs: pillow, ffmpeg. Adds narration with gTTS if internet is available (pip install gTTS)."""
import os
import subprocess
import sys
from PIL import ImageDraw
import ui

FPS = 15


def ease(t):
    return t * t * (3 - 2 * t)


def draw_cursor(img, x, y, ripple):
    d = ImageDraw.Draw(img, "RGBA")
    if ripple:
        r = 8 + ripple * 5
        d.ellipse([x - r, y - r, x + r, y + r], outline=(59, 91, 219, max(40, 255 - ripple * 40)), width=3)
    pts = [(x, y), (x, y + 22), (x + 6, y + 17), (x + 11, y + 28), (x + 15, y + 26), (x + 10, y + 16), (x + 17, y + 16)]
    d.polygon([(px + 1, py + 2) for px, py in pts], fill=(0, 0, 0, 70))
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(20, 20, 20, 255))


class Recorder:
    def __init__(self, path, initial):
        self.s = dict(initial, t=0)
        self.pos = (950.0, 520.0)
        self.ripple = 0
        self.frames = 0
        self.log = []  # (frame_index, caption)
        self.p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ui.W}x{ui.H}",
                                   "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", path],
                                  stdin=subprocess.PIPE)

    def frame(self):
        self.s["t"] = self.frames
        c = ui.render(self.s)
        draw_cursor(c.img, self.pos[0], self.pos[1], self.ripple)
        self.p.stdin.write(c.img.tobytes())
        self.frames += 1
        if self.ripple:
            self.ripple = (self.ripple + 1) % 7
        return c

    def hold(self, n):
        for _ in range(n):
            self.frame()

    def hotspot(self, name):
        return ui.render(self.s).hs[name]

    def move(self, name, n=18):
        tx, ty = self.hotspot(name)
        sx, sy = self.pos
        for i in range(1, n + 1):
            k = ease(i / n)
            self.pos = (sx + (tx - sx) * k, sy + (ty - sy) * k)
            self.frame()

    def click(self):
        self.ripple = 1
        self.hold(7)

    def typ(self, key, text, per=1.6):
        self.s["focus"] = key
        buf, i = "", 0.0
        while len(buf) < len(text):
            i += per
            buf = text[: int(i)]
            self.s[key] = buf
            self.frame()
        self.s[key] = text
        self.hold(5)

    def apply(self, d):
        d = dict(d)
        adds = {k: d.pop(k + "_add") for k in ("chat", "cchat") if k + "_add" in d}
        self.s.update(d)
        for k, v in adds.items():
            self.s[k] = list(self.s.get(k, [])) + [v]

    def run(self, steps):
        for st in steps:
            k = st[0]
            if k == "cap":
                self.s["cap"], self.s["step"] = st[1], st[2] if len(st) > 2 else self.s.get("step", "")
                self.log.append((self.frames, st[1]))
            elif k == "set":
                self.apply(st[1])
            elif k == "hold":
                self.hold(st[1])
            elif k == "move":
                self.move(st[1], st[2] if len(st) > 2 else 18)
            elif k == "click":
                self.click()
            elif k == "type":
                self.typ(st[1], st[2], st[3] if len(st) > 3 else 1.6)
            elif k == "clk":  # move + click + optional state change
                self.s.pop("focus", None)
                self.move(st[1])
                self.click()
                if len(st) > 2:
                    self.apply(st[2])
                self.hold(4)
            elif k == "wait":  # hold N seconds
                self.hold(int(st[1] * FPS))

    def close(self):
        self.p.stdin.close()
        self.p.wait()


# ------------------------------------------------------------------ scenarios
def login_steps(email, role, step="1"):
    return [
        ("cap", "Access: open the app in any browser at http://localhost:5173 (your school's URL in production).", step),
        ("clk", "url", {"focus": "url"}), ("type", "url", "localhost:5173", 1.0), ("set", {"focus": None}), ("wait", 1),
        ("cap", "Enter the email and password you registered with. First time? Click 'Create an account' and pick your role.", step),
        ("clk", "email", {"focus": "email"}), ("type", "email", email), ("clk", "password", {"focus": "password"}),
        ("type", "password", "••••••••".replace("•", "x")), ("clk", "login", {"focus": None, "screen": "__home__"}), ("wait", 1),
    ]


def student():
    init = {"screen": "login", "role": "student", "tab": "Class content", "slang": "Simple English", "tlang": "Telugu -> English",
            "tmat": "Photosynthesis basics", "chat": [("bot", "Hi! Ask in Telugu or English. I answer in English and explain the key idea in Telugu too.")]}
    steps = login_steps("aisha@school.org", "student")
    steps[-2] = ("clk", "login", {"focus": None, "screen": "s_content"})

    def ask(text, reply, think=3):
        return [("clk", "tmsg", {"focus": "tmsg"}), ("type", "tmsg", text, 1.3),
                ("clk", "send", {"focus": None, "tmsg": "", "thinking": True, "chat_add": ("me", text)}), ("wait", think),
                ("set", {"thinking": False, "chat_add": ("bot", reply)}), ("wait", 5)]
    steps += [
        ("cap", "Student home: you only see content your teachers posted to your class: videos, notes, materials and assessments.", "2"), ("wait", 4),
        ("cap", "Students cannot upload or create content. Teachers do that; you learn, practise and track your progress.", "2"), ("wait", 4),
        ("cap", "Open any item to watch the teacher's video, read the notes or download the file.", "3"),
        ("clk", "item:0", {"screen": "s_detail"}), ("wait", 4),
        ("cap", "Need it shorter or in your language? Choose Simple English, Telugu or English + Telugu and click Summarise.", "3"),
        ("clk", "slang", {"focus": "slang"}), ("clk", "summarise", {"focus": None, "sum": "Plants make food from sunlight. Chlorophyll in leaves absorbs light. "
         "With water and CO2 the plant makes glucose and gives out oxygen."}), ("wait", 5),
        ("cap", "Stuck? Click 'Ask the tutor about this' to talk about this exact lesson.", "4"),
        ("clk", "asktutor", {"screen": "tutor", "tab": "AI Tutor"}), ("wait", 2),
        ("cap", "AI Tutor mode 'Telugu to English': ask in Telugu (or Telugu typed in English letters). It shows your question in English, answers simply, and explains in Telugu.", "4"),
        *ask("chlorophyll ante enti?", "In English: What is chlorophyll?\nChlorophyll is the green pigment in leaves. It absorbs sunlight so the plant can make its food.\nTelugu explanation follows in the app. Quick check: which colour do leaves reflect?"),
        ("cap", "Switch to 'English to English' to practise: the tutor explains simply and corrects your English.", "4"),
        ("clk", "tlang", {"focus": "tlang", "tlang": "English -> English", "chat": [("bot", "Hi! Ask me anything about your lesson. I'll explain in simple English and help fix your English too.")]}),
        *ask("Plants makes food from sun", "Better: Plants make food from sunlight.\nYes! Plants use sunlight, water and carbon dioxide to make glucose. Which gas do plants give out?"),
        ("cap", "Use the Speak button to talk to the tutor and tick 'Read replies aloud' to hear answers (Chrome or Edge).", "4"), ("clk", "mic", {"listening": True}), ("wait", 3), ("set", {"listening": False}),
        ("cap", "Communicator: build speaking and writing skills with 3 new tasks every day, matched to your class level.", "5"),
        ("clk", "tab:Communicator", {"screen": "comm_today", "tab": "Communicator", "focus": None, "cdone": 0}), ("wait", 4),
        ("cap", "Primary students get short, simple talks; high school gets exam-stress talks and formal emails; postgraduates explain their research.", "5"), ("wait", 5),
        ("clk", "task:0", {"screen": "comm_task"}),
        ("cap", "Press Speak and talk naturally (or type). Your words appear on screen and are checked for length, filler words and pace.", "5"),
        ("clk", "cmic", {"clisten": True, "csecs": 0, "focus": "ctext"}),
        ("type", "ctext", "Exam stress is common. I manage it by planning early, taking short breaks and sleeping well. For example, last term I made a timetable.", 1.8),
        ("set", {"clisten": False, "csecs": 58}),
        ("clk", "cfb", {"cfeed": True, "focus": None, "cdone": 1, "cxp": 278}),
        ("cap", "Instant coach feedback: scores for clarity, grammar, vocabulary, structure and fluency, what you did well, fixes, a stronger version and a tip for tomorrow.", "5"), ("wait", 9),
        ("clk", "back", {"screen": "comm_today"}), ("wait", 2),
        ("cap", "Practice conversation: role-play real situations for your level, like a college interview. The AI partner stays in character and a coach note follows each reply.", "5"),
        ("clk", "ctab:practice", {"screen": "comm_chat", "cscen": "College admission interview", "cchat": []}),
        ("clk", "cstart", {"cchat_add": ("bot", "Welcome! Please take a seat. Why would you like to join our college?")}), ("wait", 3),
        ("clk", "cmsg", {"focus": "cmsg"}), ("type", "cmsg", "I want join because it have good science course", 1.4),
        ("clk", "csend", {"focus": None, "cmsg": "", "cchat_add": ("me", "I want join because it have good science course")}), ("wait", 2),
        ("set", {"cchat_add": ("bot", "Great reason! Which subject interests you most?\nCoach: Say 'I want to join because it has a good science course.'")}), ("wait", 8),
        ("cap", "Assessments: take the quizzes your teacher posted. You get instant marks and explanations.", "5"),
        ("clk", "tab:Assessments", {"screen": "quiz", "tab": "Assessments", "focus": None}), ("wait", 2),
        ("clk", "q0:Chlorophyll", {"q0": "Chlorophyll"}), ("clk", "q1:False", {"q1": "False"}), ("clk", "submit", {"screen": "result"}), ("wait", 4),
        ("clk", "done", {"screen": "progress", "tab": "My progress"}),
        ("cap", "My progress: scores, daily trend, streak, strong topics (green) and topics to practise (red). Check it every day.", "6"), ("wait", 7),
    ]
    return init, steps


def teacher():
    init = {"screen": "login", "role": "teacher", "tab": "Classes", "level": "high school", "share": "Grade 9 Biology", "kind": "Assessment",
            "count": "10", "classes": [("Chemistry 10A", 22)], "nrows": 0, "lib": []}
    steps = login_steps("rao@school.org", "teacher")
    steps[-2] = ("clk", "login", {"focus": None, "screen": "classes"})
    steps += [
        ("cap", "Teacher home: Classes, Materials and Quizzes are in the top menu.", "2"), ("wait", 3),
        ("cap", "Create a class: type a name and click Create.", "2"),
        ("clk", "cname", {"focus": "cname"}), ("type", "cname", "Grade 9 Biology"),
        ("clk", "create", {"classes": [("Chemistry 10A", 22), ("Grade 9 Biology", 0)], "focus": None, "cname": ""}), ("wait", 2),
        ("clk", "open:1", {"screen": "classdetail", "nrows": 0}),
        ("cap", "Add students by the email they registered with. They see the class and its materials immediately.", "2"),
        ("clk", "semail", {"focus": "semail"}), ("type", "semail", "aisha@school.org"), ("clk", "addstu", {"nrows": 1, "semail": ""}),
        ("clk", "semail", {"focus": "semail"}), ("type", "semail", "ben@school.org"), ("clk", "addstu", {"nrows": 2, "semail": ""}),
        ("clk", "semail", {"focus": "semail"}), ("type", "semail", "chloe@school.org"), ("clk", "addstu", {"nrows": 3, "semail": "", "focus": None}),
        ("wait", 2),
        ("clk", "tab:Materials", {"screen": "library", "tab": "Materials", "focus": None}),
        ("cap", "Add lesson material: any file or pasted text, choose the level, and share it with a class.", "3"),
        ("clk", "title", {"focus": "title"}), ("type", "title", "Photosynthesis lesson"),
        ("clk", "share", {"focus": "share"}), ("set", {"share": "Grade 9 Biology"}),
        ("clk", "file", {"focus": "file", "file": "lesson_slides.pptx"}),
        ("clk", "analyse", {"busy": True, "focus": None}), ("wait", 3), ("set", {"busy": False, "screen": "detail", "mtitle": "Photosynthesis lesson"}),
        ("cap", "Create an assessment: pick Assessment, set the question count and click Generate. You can review answers before sharing.", "4"),
        ("clk", "kind", {"focus": "kind"}), ("clk", "genquiz", {"quizlist": ["Assessment: Photosynthesis lesson"], "focus": None}), ("wait", 3),
        ("clk", "tab:Classes", {"screen": "classdetail", "tab": "Classes", "nrows": 3}),
        ("cap", "Monitor the class: average score, trend, strong topics (green) and weak topics (red) for every student.", "5"), ("wait", 6),
        ("clk", "details:0", {"screen": "progress_fb"}),
        ("cap", "Open a student for details. Generate AI feedback or write your own note — parents see it too.", "6"),
        ("clk", "aifb", {"fb_ai": True}), ("wait", 3),
        ("clk", "note", {"focus": "note"}), ("type", "note", "Great progress, Aisha. Focus on genetics this week.", 1.4),
        ("clk", "post", {"focus": None}), ("wait", 3),
    ]
    return init, steps


def parent():
    init = {"screen": "login", "role": "parent", "tab": "My child"}
    steps = login_steps("khan.parent@mail.com", "parent")
    steps[-2] = ("clk", "login", {"focus": None, "screen": "progress"})
    steps += [
        ("cap", "Parent home: 'My child' shows your linked child. The school links your account to your child's — you can only view, never edit.", "2"),
        ("wait", 4),
        ("cap", "See the average score, number of attempts, trend and day streak at a glance.", "3"), ("wait", 4),
        ("cap", "The daily chart shows how scores change over time.", "3"), ("wait", 5),
        ("set", {"screen": "progress_fb", "fb_ai": True}),
        ("cap", "Strengths in green, topics needing practice in red — based on your child's real quiz answers.", "4"), ("wait", 6),
        ("cap", "Read feedback from teachers and the AI tutor, with suggestions you can support at home.", "5"), ("wait", 6),
    ]
    return init, steps


def admin():
    init = {"screen": "login", "role": "admin", "tab": "Admin", "urole": "teacher", "newuser": ""}
    steps = login_steps("admin@school.org", "admin")
    steps[-2] = ("clk", "login", {"focus": None, "screen": "admin"})
    steps += [
        ("cap", "Admin home: platform totals — users by role, materials, quizzes and average score.", "2"), ("wait", 4),
        ("cap", "Create a user: enter name, email, password and choose a role, then click Create.", "3"),
        ("clk", "uname", {"focus": "uname"}), ("type", "uname", "Meera Nair"), ("clk", "uemail", {"focus": "uemail"}),
        ("type", "uemail", "meera@school.org"), ("clk", "urole", {"focus": "urole"}), ("clk", "upass", {"focus": "upass"}),
        ("type", "upass", "xxxxxxxx"), ("clk", "createuser", {"focus": None, "msg1": "User created", "newuser": "Meera Nair"}), ("wait", 3),
        ("cap", "Link a parent to a student: enter both emails and click Link. The parent then sees that child's progress.", "4"),
        ("clk", "pemail", {"focus": "pemail"}), ("type", "pemail", "khan.parent@mail.com"), ("clk", "lemail", {"focus": "lemail"}),
        ("type", "lemail", "aisha@school.org"), ("clk", "link", {"focus": None, "msg2": "Linked."}), ("wait", 3),
        ("cap", "Review any student: open Progress from the user list to see performance and add feedback.", "5"),
        ("clk", "userprog", {"screen": "progress_fb", "fb_ai": True}), ("wait", 5),
    ]
    return init, steps


SCENARIOS = {"student": student, "teacher": teacher, "parent": parent, "admin": admin}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "../app_demo_videos"
    roles = sys.argv[2:] or list(SCENARIOS)
    os.makedirs(out, exist_ok=True)
    for r in roles:
        init, steps = SCENARIOS[r]()
        path = os.path.join(out, f"demo_{r}.mp4")
        rec = Recorder(path, init)
        rec.run(steps)
        rec.hold(20)
        rec.close()
        with open(os.path.join(out, f"demo_{r}_script.txt"), "w") as f:
            f.write("\n".join(f"{t / FPS:5.1f}s  {c}" for t, c in rec.log))
        print("built", path, round(rec.frames / FPS), "s")


if __name__ == "__main__":
    main()
