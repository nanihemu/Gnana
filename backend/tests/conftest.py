"""Test setup: fresh temp database, AI disabled (offline fallback paths), narration off. Run from backend/: python -m pytest tests -q"""
import os
import tempfile

os.environ["GNANA_DATA_DIR"] = tempfile.mkdtemp(prefix="gnana_test_")
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["GNANA_TTS"] = "off"
os.environ["GNANA_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

SAMPLE = (
    "Photosynthesis is the process by which green plants convert light energy into chemical energy. "
    "Chlorophyll in the chloroplasts absorbs sunlight to drive the reaction. "
    "Plants take in carbon dioxide and water and release oxygen as a byproduct. "
    "The glucose produced is used for growth and energy storage in the plant. "
    "The light-dependent reactions occur in the thylakoid membranes of the chloroplast. "
    "The Calvin cycle uses energy from the light reactions to build sugar molecules from carbon dioxide. "
    "Stomata are tiny pores on leaves that let carbon dioxide enter and oxygen leave the plant. "
    "Without sunlight plants cannot make enough glucose to survive for long."
)


def H(tok):
    return {"Authorization": "Bearer " + tok}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def w(client):
    """A small school: admin, 2 teachers, 3 students (s1 high school, s2 primary, s3 not enrolled), 1 parent linked to s1."""
    r = client.post("/api/auth/register", json={"name": "Admin", "email": "admin@t.com", "password": "pw123456", "role": "admin"})
    assert r.status_code == 200, r.text
    tok = {"admin": r.json()["token"]}
    people = [("t1", "Teacher One", "teacher", "professional"), ("t2", "Teacher Two", "teacher", "professional"),
              ("s1", "Student One", "student", "high school"), ("s2", "Student Two", "student", "primary"),
              ("s3", "Student Three", "student", "high school"), ("p1", "Parent One", "parent", "high school")]
    for key, name, role, level in people:
        r = client.post("/api/admin/users", headers=H(tok["admin"]),
                        json={"name": name, "email": f"{key}@t.com", "password": "pw123456", "role": role, "level": level})
        assert r.status_code == 200, r.text
        tok[key] = client.post("/api/auth/login", json={"email": f"{key}@t.com", "password": "pw123456"}).json()["token"]
    ids = {k: client.get("/api/me", headers=H(t)).json()["id"] for k, t in tok.items()}
    h = {k: H(t) for k, t in tok.items()}
    cid = client.post("/api/classrooms", headers=h["t1"], json={"name": "Biology 9"}).json()["id"]
    cid2 = client.post("/api/classrooms", headers=h["t2"], json={"name": "Other class"}).json()["id"]
    for s in ("s1", "s2"):
        assert client.post(f"/api/classrooms/{cid}/students", headers=h["t1"], json={"student_email": f"{s}@t.com"}).status_code == 200
    r = client.post("/api/admin/parent-links", headers=h["admin"], json={"parent_email": "p1@t.com", "student_email": "s1@t.com"})
    assert r.status_code == 200, r.text
    return {"tok": tok, "h": h, "id": ids, "cid": cid, "cid2": cid2}


def upload(client, w, who="t1", title="", text="", filename=None, data=b"", ctype="text/plain", classroom_id=None):
    form = {"title": title, "text": text}
    if classroom_id:
        form["classroom_id"] = str(classroom_id)
    files = {"file": (filename, data, ctype)} if filename else None
    return client.post("/api/materials", headers=w["h"][who], data=form, files=files)


@pytest.fixture(scope="session")
def shared_mat(client, w):
    """Teacher's text lesson shared with the class."""
    r = upload(client, w, title="Photosynthesis", text=SAMPLE, classroom_id=w["cid"])
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="session")
def quiz(client, w, shared_mat):
    r = client.post(f"/api/materials/{shared_mat}/quizzes", headers=w["h"]["t1"],
                    json={"count": 5, "kind": "quiz", "types": ["mcq", "tf"]})
    assert r.status_code == 200, r.text
    return r.json()
