import streamlit as st
from supabase import create_client

def get_supabase():
    if "supabase_client" not in st.session_state:
        try:
            st.session_state.supabase_client = create_client(
                st.secrets["supabase"]["url"],
                st.secrets["supabase"]["key"],  # anon
            )
        except Exception:
            st.session_state.supabase_client = None
    return st.session_state.supabase_client

def run_query(table, select="*", filters=None, order=None, limit=None, single=False, range_from=None, range_to=None):
    client = get_supabase()
    if not client:
        return (None, 0) if not single else None

    q = client.table(table).select(select, count="exact")

    if filters:
        for k, v in filters.items():
            if v is None or v == "" or v == []:
                continue
            if k.endswith("__ilike"):
                q = q.ilike(k.replace("__ilike", ""), v)
            elif k.endswith("__gte"):
                q = q.gte(k.replace("__gte", ""), v)
            elif k.endswith("__lte"):
                q = q.lte(k.replace("__lte", ""), v)
            else:
                if isinstance(v, list):
                    q = q.in_(k, v)
                else:
                    q = q.eq(k, v)

    if order:
        col, direction = order
        q = q.order(col, desc=(direction == "desc"))

    if range_from is not None and range_to is not None:
        q = q.range(range_from, range_to)
    elif limit:
        q = q.limit(limit)

    try:
        if single:
            res = q.limit(1).single().execute()
            return res.data
        res = q.execute()
        return res.data, res.count
    except Exception:
        return (None, 0) if not single else None
