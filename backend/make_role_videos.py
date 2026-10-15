"""Generate a 'how Gnana works' walkthrough video for each role.
Usage: python make_role_videos.py [outdir]
Narration uses gTTS when online; otherwise videos are silent with burned-in captions."""
import os
import sys
from app.video import build_video

COMMON_END = {"title": "Ready to start?", "bullets": ["Log in or create your account", "Pick your role", "Everything starts from the top menu"],
              "narration": "That's it. Log in, choose your role, and use the menu at the top to get started."}

ROLES = {
    "student": ("#3b5bdb", [
        ("Gnana for students", ["Learn from what your teacher posts", "Summaries, assessments, AI tutor, progress"],
         "Welcome to Gnana for students. Everything your teachers share is here, with an AI tutor and a communication coach."),
        ("1. Class content", ["Teacher-posted videos, notes, materials", "Watch, read or download", "Students view only; teachers upload"],
         "Open Class content to see what your teachers have posted. You can watch videos, read notes and download files."),
        ("2. Summaries", ["Click Summarise on any lesson", "Simple English, Telugu or both", "Key points to remember"],
         "Need it shorter? Summarise any lesson in simple English, in Telugu, or both."),
        ("3. AI Tutor", ["Telugu to English: ask in Telugu, learn the English", "English to English: simple explanations and corrections", "Speak to it and hear answers aloud"],
         "Ask the AI Tutor anything about the lesson. In Telugu to English mode it shows your question in English, answers simply, and explains in Telugu."),
        ("4. Communicator: daily tasks", ["3 new tasks every day: speak, write, word power", "Different for every class level", "Primary: 30s talk  |  High school: exam stress", "Postgraduate: explain your research"],
         "The Communicator gives you three new tasks every day: one speaking, one writing and one vocabulary. They match your class level, from simple talks in primary school to research explanations at postgraduate level."),
        ("5. Coach feedback", ["Speak with the mic or type", "Scores: clarity, grammar, vocabulary, structure, fluency", "Fixes, a stronger version and a tip", "Build your streak and XP"],
         "Speak or type your answer and get instant coach feedback: scores, what you did well, what to fix, a stronger version of your own words, and a tip for tomorrow."),
        ("6. Role-play practice", ["Real situations for your level", "Interview, debate, client meeting…", "AI partner stays in character", "Coach note after every reply"],
         "Practise real conversations such as a college interview. The AI partner stays in character and a coach note after each reply shows one thing to improve."),
        ("7. Assessments", ["Quizzes your teacher posted", "Instant marks and explanations", "Short answers graded by AI"],
         "Take the assessments your teacher shares. You get instant marks and an explanation for every mistake."),
        ("8. My progress", ["Daily score chart and streak", "Strong topics in green", "Topics to practise in red", "Feedback from AI and teachers"],
         "Check My progress every day to see your scores, strengths, and exactly where to practise next."),
    ]),
    "teacher": ("#0b7285", [
        ("Gnana for teachers", ["Create content fast", "Know where each student stands"],
         "Welcome to Gnana for teachers. Build lessons and assessments in minutes, and see exactly who needs help."),
        ("1. Create a class", ["Open Classes", "Name it and click Create", "Add students by their email"],
         "Start by creating a class and adding your students using the email they registered with."),
        ("2. Upload lesson material", ["Any file type or pasted text", "Choose the learner level", "Share with a class or keep private"],
         "Upload your lesson in any format. Choose the level and share it with a class so students see it instantly."),
        ("3. Generate quizzes and assessments", ["Pick quiz or assessment", "Choose number of questions", "Review answers before sharing"],
         "From any material, generate a quiz or a full assessment. You can see the answer key and explanations before students take it."),
        ("4. Monitor the class", ["Average score per student", "Trend: improving, steady or declining", "Strong and weak topics at a glance"],
         "The class table shows each student's average, trend, and which topics they've mastered or struggle with."),
        ("5. Give feedback", ["Open a student's details", "Generate AI feedback", "Or write your own note"],
         "Open any student to see daily performance and attempts. Generate AI feedback, or write a personal note that parents also see."),
    ]),
    "parent": ("#e8590c", [
        ("Gnana for parents", ["See your child's learning, day by day", "Read-only and private"],
         "Welcome to Gnana for parents. Follow your child's progress without needing to be a subject expert."),
        ("1. Get linked", ["School admin or teacher links your account", "Use the email you registered with", "Several children supported"],
         "After you register, the school links your account to your child's. If you have several children, you can switch between them."),
        ("2. Daily overview", ["Average score and number of attempts", "Day streak", "Trend over time"],
         "Your dashboard shows your child's average score, how often they practise, and whether they're improving."),
        ("3. Strengths and gaps", ["Green: topics they're good at", "Red: topics needing practice", "Based on real quiz answers"],
         "See which topics your child has mastered and which need more practice, based on their actual quiz results."),
        ("4. Feedback", ["Teacher notes", "AI tutor summaries with next steps", "Recent quiz history"],
         "Read feedback from teachers and the AI tutor, with concrete suggestions you can support at home."),
    ]),
    "admin": ("#7048e8", [
        ("Gnana for administrators", ["Set up your school", "Keep control of users and data"],
         "Welcome to Gnana for administrators. You manage who is on the platform and how it's being used."),
        ("1. Platform overview", ["Users by role", "Materials, quizzes, attempts", "Average score across the platform", "AI engine status"],
         "The Admin page shows how many students, teachers and parents you have, how much content exists, and whether the AI engine is connected."),
        ("2. Manage users", ["Create students, teachers, parents, admins", "Delete accounts", "Only admins can create admins"],
         "Create accounts for any role, or remove them. Only an existing admin can create another admin."),
        ("3. Link parents to students", ["Enter parent email and student email", "Parent gets read-only access", "Link as many children as needed"],
         "Link each parent to their child. Parents can then see that child's progress and nothing else."),
        ("4. Review any student", ["Open a student's progress from the user list", "Write feedback if needed", "Oversee classes and materials"],
         "Open any student's progress, oversee classes, and review materials across the whole school."),
    ]),
}


def main(out="role_videos"):
    os.makedirs(out, exist_ok=True)
    for role, (accent, steps) in ROLES.items():
        slides = [{"title": t, "bullets": b, "narration": n, "accent": accent, "caption": True} for t, b, n in steps]
        slides.append({**COMMON_END, "accent": accent, "caption": True})
        path = os.path.join(out, f"how_it_works_{role}.mp4")
        build_video(slides, path)
        with open(os.path.join(out, f"how_it_works_{role}_script.txt"), "w") as f:
            f.write("\n\n".join(f"[{s['title']}]\n{s['narration']}" for s in slides))
        print("built", path)


if __name__ == "__main__":
    main(*sys.argv[1:2])
