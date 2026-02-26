import json
from datetime import datetime, timezone
from services.database import get_supabase

REQUIRED_FIELDS = ["disciplina", "enunciado", "alternativas", "gabarito"]

def validate_question_dict(q: dict) -> list[str]:
    errs = []
    for f in REQUIRED_FIELDS:
        if f not in q or q[f] in (None, "", {}):
            errs.append(f"Campo obrigatório ausente: {f}")
    alts = q.get("alternativas")
    if alts is not None and not isinstance(alts, dict):
        errs.append("alternativas deve ser um objeto JSON (dict)")
    gab = (q.get("gabarito") or "").strip().upper()
    if gab and isinstance(alts, dict) and gab not in {k.upper() for k in alts.keys()}:
        errs.append("gabarito não está entre as alternativas")
    return errs

def insert_question(payload: dict):
    client = get_supabase()
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = client.table("questions").insert(payload).execute()
    return (res.data or [{}])[0]

def update_question(question_id: str, payload: dict):
    client = get_supabase()
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    client.table("questions").update(payload).eq("id", question_id).execute()

def get_question(question_id: str):
    client = get_supabase()
    return client.table("questions").select("*").eq("id", question_id).single().execute().data

def search_questions_admin(text: str, limit: int = 40):
    client = get_supabase()
    q = client.table("questions").select("id,id_original,disciplina,assunto,banca,ano,ativo,enunciado").order("created_at", desc=True).limit(limit)
    if text:
        text = text.strip()
        q = q.or_(f"id_original.ilike.%{text}%,enunciado.ilike.%{text}%")
    return q.execute().data or []

def upsert_questions_bulk(items: list[dict], chunk_size: int = 200):
    client = get_supabase()
    ok, fail = 0, 0
    errors = []

    with_id = [x for x in items if (x.get("id_original") or "").strip() != ""]
    no_id  = [x for x in items if (x.get("id_original") or "").strip() == ""]

    for i in range(0, len(with_id), chunk_size):
        chunk = with_id[i:i+chunk_size]
        try:
            client.table("questions").upsert(chunk, on_conflict="id_original").execute()
            ok += len(chunk)
        except Exception as e:
            fail += len(chunk)
            errors.append(str(e))

    for i in range(0, len(no_id), chunk_size):
        chunk = no_id[i:i+chunk_size]
        try:
            client.table("questions").insert(chunk).execute()
            ok += len(chunk)
        except Exception as e:
            fail += len(chunk)
            errors.append(str(e))

    return ok, fail, errors
