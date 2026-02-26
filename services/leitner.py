from datetime import datetime, timezone, timedelta
from services.database import get_supabase

LEITNER_DAYS = [1, 2, 4, 7, 14, 30]
MAX_BOX = len(LEITNER_DAYS) - 1

def _next_review_date(box: int) -> str:
    box = max(0, min(MAX_BOX, box))
    dt = datetime.now(timezone.utc) + timedelta(days=LEITNER_DAYS[box])
    return dt.isoformat()

def update_leitner(user_id: str, question_id: str, is_correct: bool):
    client = get_supabase()
    row = client.table("user_interactions") \
        .select("leitner_box") \
        .eq("user_id", user_id) \
        .eq("question_id", question_id) \
        .maybe_single().execute()

    current_box = 0
    if row and row.data and row.data.get("leitner_box") is not None:
        current_box = int(row.data["leitner_box"])

    if is_correct:
        new_box = min(current_box + 1, MAX_BOX)
    else:
        new_box = max(current_box - 1, 0)

    payload = {
        "user_id": user_id,
        "question_id": question_id,
        "leitner_box": new_box,
        "next_review_at": _next_review_date(new_box),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    client.table("user_interactions").upsert(payload, on_conflict="user_id,question_id").execute()
