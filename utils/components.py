# --- file: utils/components.py
import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
        /* 1. ESCONDER MENU PADRÃO DO STREAMLIT (Adeus aba 'app' e 'dashboard') */
        [data-testid="stSidebarNav"] { display: none !important; }
        
        /* 2. CORES GERAIS E FUNDO (Estilo Estratégia MED) */
        .stApp { background-color: #F4F6F9; }
        
        header[data-testid="stHeader"] { background-color: #0B1C2D !important; }
        [data-testid="stSidebar"] {
            background-color: #0B1C2D !important;
            border-right: 1px solid #162C46;
        }
        [data-testid="stSidebar"] * { color: #FFFFFF !important; }
        
        /* 3. CARTÕES DE QUESTÃO E DASHBOARD */
        .card-container {
            background-color: #FFFFFF; padding: 25px; border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; 
            border: 1px solid #EAECEF; transition: transform 0.2s;
        }
        .card-container:hover { transform: translateY(-2px); }
        
        /* 4. TAGS MÉDICAS */
        .tag-pill {
            background-color: #E8F0FE; color: #0B1C2D; padding: 4px 10px;
            border-radius: 12px; font-size: 0.8rem; font-weight: 700; margin-right: 5px;
            text-transform: uppercase; letter-spacing: 0.5px;
        }
        .tag-dif { background-color: #FEECEB; color: #B31412; }
        .tag-rev { background-color: #FEF5E8; color: #B36B00; }
        
        /* 5. BOTÕES PROFISSIONAIS */
        .stButton > button {
            background-color: #1252A3; color: white !important;
            border-radius: 6px; font-weight: 600; border: none; padding: 0.5rem 1rem;
        }
        .stButton > button:hover { background-color: #0E4285; }
        
        /* Textos Gerais */
        h1, h2, h3 { color: #0B1C2D !important; font-weight: 800; font-family: 'Helvetica Neue', sans-serif; }
        p, span, div { color: #333333; }
        .enunciado { font-size: 1.15rem; line-height: 1.7; color: #202124; margin: 15px 0; }
        
        /* Métricas do Dashboard */
        [data-testid="stMetricValue"] { color: #1252A3 !important; font-size: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

def question_card(q):
    """Renderiza a miniatura da questão no navegador"""
    enunciado_curto = q.get('enunciado', '')[:150] + "..."
    with st.container():
        st.markdown(f"""
        <div class="card-container">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="tag-pill">🩺 {q.get('disciplina')}</span>
                    <span style="color:#5F6368; font-size:0.85rem; font-weight:600;">{q.get('assunto', '')}</span>
                </div>
                <span style="color:#9AA0A6; font-size:0.8rem;">ID: {q.get('id_original') or 'N/A'}</span>
            </div>
            <div class="enunciado">
                {enunciado_curto}
            </div>
        </div>
        """, unsafe_allow_html=True)
