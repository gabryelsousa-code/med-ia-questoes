import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
        .stApp { background-color: #F0F2F6; }
        
        /* HEADER E SIDEBAR AZUL MARINHO */
        header[data-testid="stHeader"] { background-color: #002855 !important; }
        [data-testid="stSidebar"] { background-color: #002855 !important; border-right: 1px solid #001a38; }
        [data-testid="stSidebar"] * { color: #FFFFFF !important; }
        
        /* CARTÕES */
        .card-container {
            background-color: white; padding: 20px; border-radius: 12px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #E5E7EB;
        }
        
        /* TAGS */
        .tag-pill {
            background-color: #E0F2FE; color: #002855; padding: 4px 8px;
            border-radius: 12px; font-size: 0.8rem; font-weight: 600; margin-right: 5px;
        }
        
        /* BOTÕES */
        .stButton > button {
            background-color: #002855; color: white !important;
            border-radius: 8px; font-weight: 600; border: none;
        }
        .stButton > button:hover { filter: brightness(1.2); }
        
        /* TEXTO GERAL */
        h1, h2, h3 { color: #002855 !important; }
    </style>
    """, unsafe_allow_html=True)

def question_card(q):
    with st.container():
        st.markdown(f"""
        <div class="card-container">
            <div style="display:flex; justify-content:space-between;">
                <span class="tag-pill">{q.get('disciplina')}</span>
                <span style="color:#6B7280; font-size:0.8rem;">ID: {q.get('id_original') or 'N/A'}</span>
            </div>
            <div style="margin: 15px 0; font-size: 1.1rem; line-height:1.6; color: #333;">
                {q.get('enunciado')}
            </div>
        </div>
        """, unsafe_allow_html=True)
