"""Create demo users, a class, enrolments and a parent link. Safe to run more than once."""
from app.db import SessionLocal, Base, engine
from app.models import User, Classroom, Enrollment, ParentLink
from app.auth import hash_pw

Base.metadata.create_all(engine)
db = SessionLocal()

USERS = [
    ("School Admin", "admin@gnana.com",    "Admin@123",   "admin",   "professional"),
    ("Mr. Rao",      "teacher@gnana.com",  "Teacher@123", "teacher", "professional"),
    ("Aisha Khan",   "student@gnana.com",  "Student@123", "student", "high school"),
    ("Ben Ortiz",    "student2@gnana.com", "Student@123", "student", "middle school"),
    ("Mrs. Khan",    "parent@gnana.com",   "Parent@123",  "parent",  "high school"),
]
by_email = {}
for name, email, pw, role, level in USERS:
    u = db.query(User).filter_by(email=email).first()
    if not u:
        u = User(name=name, email=email, password_hash=hash_pw(pw), role=role, level=level)
        db.add(u); db.commit()
    by_email[email] = u

t = by_email["teacher@gnana.com"]
c = db.query(Classroom).filter_by(name="Grade 9 Biology", teacher_id=t.id).first()
if not c:
    c = Classroom(name="Grade 9 Biology", teacher_id=t.id); db.add(c); db.commit()
for e in ("student@gnana.com", "student2@gnana.com"):
    s = by_email[e]
    if not db.query(Enrollment).filter_by(classroom_id=c.id, student_id=s.id).first():
        db.add(Enrollment(classroom_id=c.id, student_id=s.id))
p, s = by_email["parent@gnana.com"], by_email["student@gnana.com"]
if not db.query(ParentLink).filter_by(parent_id=p.id, student_id=s.id).first():
    db.add(ParentLink(parent_id=p.id, student_id=s.id))
db.commit()
print("Demo accounts ready.")
