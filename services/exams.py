from services.database import get_supabase

def create_exam(
    user_id: str,
    title: str,
    exam_type: str,          # 'lista' | 'simulado'
    category_id: str | None,
    mode: str,
    question_ids: list[str],
    is_generated: bool = False,
    description: str | None = None,
    time_limit_minutes: int | None = None,
    randomize_questions: bool = False,
    randomize_alternatives: bool = False,
):
    client = get_supabase()
    exam = client.table("exams").insert({
        "user_id": user_id,
        "title": title,
        "exam_type": exam_type,
        "category_id": category_id,
        "mode": mode,
        "is_generated": is_generated,
        "description": description,
        "time_limit_minutes": time_limit_minutes,
        "randomize_questions": randomize_questions,
        "randomize_alternatives": randomize_alternatives
    }).execute().data[0]

    rows = [{"exam_id": exam["id"], "question_id": qid, "position": i + 1} for i, qid in enumerate(question_ids)]
    if rows:
        client.table("exam_questions").insert(rows).execute()

    return exam["id"]

def get_user_exams(user_id: str, exam_type: str | None = None, category_id: str | None = None):
    client = get_supabase()
    q = client.table("exams").select("*").eq("user_id", user_id).order("created_at", desc=True)
    if exam_type:
        q = q.eq("exam_type", exam_type)
    if category_id:
        q = q.eq("category_id", category_id)
    res = q.execute()
    return res.data or []

def get_exam(exam_id: str):
    client = get_supabase()
    res = client.table("exams").select("*").eq("id", exam_id).single().execute()
    return res.data

def update_exam(exam_id: str, payload: dict):
    client = get_supabase()
    client.table("exams").update(payload).eq("id", exam_id).execute()

def get_exam_question_ids(exam_id: str):
    client = get_supabase()
    res = client.table("exam_questions").select("question_id,position").eq("exam_id", exam_id).order("position").execute()
    data = res.data or []
    return [r["question_id"] for r in data]

def delete_exam(exam_id: str):
    client = get_supabase()
    client.table("exams").delete().eq("id", exam_id).execute()
