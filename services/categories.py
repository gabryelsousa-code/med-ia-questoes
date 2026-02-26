from services.database import get_supabase

def list_categories(user_id: str):
    client = get_supabase()
    res = client.table("exam_categories").select("*").eq("user_id", user_id).order("name").execute()
    return res.data or []

def ensure_default_category(user_id: str) -> str | None:
    cats = list_categories(user_id)
    for c in cats:
        if (c.get("name") or "").strip().lower() == "geral":
            return c["id"]
    if cats:
        return cats[0]["id"]
    client = get_supabase()
    res = client.table("exam_categories").insert({"user_id": user_id, "name": "Geral", "icon": "📁"}).execute()
    return (res.data or [{}])[0].get("id")

def ensure_category(user_id: str, name: str, icon: str = "📁") -> str | None:
    client = get_supabase()
    res = client.table("exam_categories").select("*").eq("user_id", user_id).eq("name", name).maybe_single().execute()
    if res and res.data:
        return res.data["id"]
    created = client.table("exam_categories").insert({"user_id": user_id, "name": name, "icon": icon}).execute().data
    return (created or [{}])[0].get("id")

def create_category(user_id: str, name: str, icon: str | None = None):
    client = get_supabase()
    payload = {"user_id": user_id, "name": name.strip()}
    if icon:
        payload["icon"] = icon.strip()
    res = client.table("exam_categories").insert(payload).execute()
    return (res.data or [{}])[0].get("id")

def delete_category(category_id: str):
    client = get_supabase()
    client.table("exam_categories").delete().eq("id", category_id).execute()

def rename_category(category_id: str, new_name: str):
    client = get_supabase()
    client.table("exam_categories").update({"name": new_name.strip()}).eq("id", category_id).execute()
