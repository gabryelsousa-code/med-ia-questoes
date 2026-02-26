# --- file: utils/components.py
import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
        .stApp { background-color: #F8F9FA; }
        .card-container {
            background-color: white; padding: 20px; border-radius: 12px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #E5E7EB;
        }
        .header-blue { color: #002855 !important; font-weight: 800; }
        .tag-pill {
            background-color: #E0F2FE; color: #002855; padding: 4px 8px;
            border-radius: 12px; font-size: 0.8rem; font-weight: 600; margin-right: 5px;
        }
        .stButton > button {
            border-radius: 8px; font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

def question_card(q, show_answer=False, user_answer=None):
    with st.container():
        st.markdown(f"""
        <div class="card-container">
            <div style="display:flex; justify-content:space-between;">
                <span class="tag-pill">{q.get('disciplina')}</span>
                <span style="color:#6B7280; font-size:0.8rem;">ID: {q.get('id_original') or 'N/A'}</span>
            </div>
            <div style="margin: 15px 0; font-size: 1.1rem; line-height:1.6;">
                {q.get('enunciado')}
            </div>
        </div>
        """, unsafe_allow_html=True)
