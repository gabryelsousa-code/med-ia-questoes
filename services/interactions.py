from services.database import get_supabase

def get_interactions_map(user_id: str, question_ids: list[str]) -> dict:
    if not question_ids:
        return {}
    client = get_supabase()
    res = client.table("user_interactions").select("*").eq("user_id", user_id).in_("question_id", question_ids).execute()
    data = res.data or []
    return {r["question_id"]: r for r in data}

def set_favorite(user_id: str, question_id: str, value: bool):
    client = get_supabase()
    payload = {"user_id": user_id, "question_id": question_id, "is_favorite": value}
    client.table("user_interactions").upsert(payload, on_conflict="user_id,question_id").execute()
