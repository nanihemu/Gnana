import os
import datetime as dt
import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, Classroom, Enrollment, ParentLink

SECRET = os.environ.get("GNANA_SECRET", "dev-secret-change-me")
bearer = HTTPBearer(auto_error=False)


def hash_pw(p: str) -> str:
    return bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt()).decode()


def check_pw(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode()[:72], h.encode())


def make_token(user: User) -> str:
    payload = {"sub": str(user.id), "exp": dt.datetime.utcnow() + dt.timedelta(days=7)}
    return jwt.encode(payload, SECRET, algorithm="HS256")


def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not cred:
        raise HTTPException(401, "Not authenticated")
    try:
        data = jwt.decode(cred.credentials, SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    user = db.get(User, int(data["sub"]))
    if not user:
        raise HTTPException(401, "User not found")
    return user


def require(*roles):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Forbidden for role " + user.role)
        return user
    return dep


def can_view_student(db: Session, viewer: User, student_id: int) -> bool:
    if viewer.role == "admin" or viewer.id == student_id:
        return True
    if viewer.role == "parent":
        return db.query(ParentLink).filter_by(parent_id=viewer.id, student_id=student_id).first() is not None
    if viewer.role == "teacher":
        q = (db.query(Enrollment).join(Classroom, Classroom.id == Enrollment.classroom_id)
             .filter(Classroom.teacher_id == viewer.id, Enrollment.student_id == student_id))
        return q.first() is not None
    return False
