import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATA_DIR = os.environ.get("GNANA_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
DATA_DIR = os.path.abspath(DATA_DIR)
os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "videos"), exist_ok=True)

engine = create_engine(f"sqlite:///{os.path.join(DATA_DIR, 'gnana.db')}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
