# --- file: services/database.py
import streamlit as st
from supabase import create_client

@st.cache_resource
def get_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.error(f"Erro ao conectar Supabase: {e}")
        return None

def run_query(table, select="*", filters=None, order=None, limit=None, single=False):
    """Helper genérico para queries"""
    client = get_supabase()
    query = client.table(table).select(select, count='exact')
    
    if filters:
        for key, value in filters.items():
            if value is not None:
                # Tratamento simples para listas (in_) e valores únicos (eq)
                if isinstance(value, list): query = query.in_(key, value)
                else: query = query.eq(key, value)
    
    if order:
        col, direction = order # ex: ('created_at', 'desc')
        query = query.order(col, desc=(direction=='desc'))
        
    if limit:
        query = query.limit(limit)
        
    try:
        if single:
            result = query.limit(1).single().execute()
            return result.data
        result = query.execute()
        return result.data, result.count
    except Exception as e:
        return None, 0
