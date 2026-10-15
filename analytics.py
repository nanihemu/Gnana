import datetime as dt
from collections import defaultdict
from sqlalchemy.orm import Session
from .models import Attempt, Quiz, Material


def student_stats(db: Session, student_id: int) -> dict:
    attempts = (db.query(Attempt).filter_by(student_id=student_id).order_by(Attempt.created_at).all())
    topics = defaultdict(lambda: [0.0, 0])
    daily = defaultdict(lambda: [0.0, 0.0])
    history = []
    for a in attempts:
        for r in a.results:
            t = topics[r.get("topic", "general")]
            t[0] += r["score"]
            t[1] += 1
        day = a.created_at.strftime("%Y-%m-%d")
        daily[day][0] += a.score
        daily[day][1] += a.total
        quiz = db.get(Quiz, a.quiz_id)
        history.append({"attempt_id": a.id, "quiz": quiz.title if quiz else "?", "kind": quiz.kind if quiz else "quiz",
                        "pct": round(100 * a.score / a.total) if a.total else 0,
                        "date": a.created_at.isoformat(), "seconds": a.seconds})
    topic_list = [{"topic": k, "pct": round(100 * v[0] / v[1]), "questions": v[1]} for k, v in topics.items()]
    topic_list.sort(key=lambda x: -x["pct"])
    strengths = [t for t in topic_list if t["pct"] >= 75 and t["questions"] >= 2][:4]
    weaknesses = sorted([t for t in topic_list if t["pct"] < 60], key=lambda x: x["pct"])[:4]
    series = [{"day": d, "pct": round(100 * v[0] / v[1]) if v[1] else 0} for d, v in sorted(daily.items())]
    total_s = sum(a.score for a in attempts)
    total_t = sum(a.total for a in attempts)
    avg = round(100 * total_s / total_t) if total_t else 0
    trend = "not enough data yet"
    if len(history) >= 4:
        half = len(history) // 2
        old = sum(h["pct"] for h in history[:half]) / half
        new = sum(h["pct"] for h in history[half:]) / (len(history) - half)
        trend = "improving" if new - old > 5 else "declining" if old - new > 5 else "steady"
    days = {s["day"] for s in series}
    streak, d = 0, dt.date.today()
    while d.isoformat() in days or (streak == 0 and (d - dt.timedelta(days=1)).isoformat() in days):
        if d.isoformat() in days:
            streak += 1
        d -= dt.timedelta(days=1)
    return {"attempts": len(attempts), "average": avg, "topics": topic_list, "strengths": strengths,
            "weaknesses": weaknesses, "daily": series, "history": history[-20:][::-1], "trend": trend, "streak": streak}
