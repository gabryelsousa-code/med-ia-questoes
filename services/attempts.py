from datetime import datetime, timezone
from services.database import get_supabase

def start_attempt(user_id: str, exam_id: str | None, question_order: list[str]):
    client = get_supabase()
    res = client.table("attempts").insert({
        "user_id": user_id,
        "exam_id": exam_id,
        "status": "in_progress",
        "question_order": question_order,
        "current_index": 0
    }).execute()
    return res.data[0]["id"]

def get_attempt(attempt_id: str):
    client = get_supabase()
    res = client.table("attempts").select("*").eq("id", attempt_id).single().execute()
    return res.data

def set_current_index(attempt_id: str, idx: int):
    client = get_supabase()
    client.table("attempts").update({"current_index": idx}).eq("id", attempt_id).execute()

def finish_attempt(attempt_id: str):
    client = get_supabase()
    client.table("attempts").update({
        "status": "finished",
        "finished_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", attempt_id).execute()

def upsert_answer(user_id: str, attempt_id: str, question_id: str, user_answer: str | None, is_correct: bool | None, time_spent_seconds: int | None):
    client = get_supabase()
    payload = {
        "user_id": user_id,
        "attempt_id": attempt_id,
        "question_id": question_id,
        "user_answer": user_answer,
        "is_correct": is_correct,
        "time_spent_seconds": time_spent_seconds
    }
    client.table("attempt_answers").upsert(payload, on_conflict="attempt_id,question_id").execute()

def get_attempt_answers(attempt_id: str):
    client = get_supabase()
    res = client.table("attempt_answers").select("question_id,user_answer,is_correct,time_spent_seconds,answered_at").eq("attempt_id", attempt_id).execute()
    return res.data or []
