import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        .stApp { background-color: #F4F6F9; }
        header[data-testid="stHeader"] { background-color: #0B1C2D !important; }
        [data-testid="stSidebar"] { background-color: #0B1C2D !important; border-right: 1px solid #162C46; }
        [data-testid="stSidebar"] * { color: #FFFFFF !important; }

        .card-container {
          background-color: #FFFFFF;
          padding: 25px;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.05);
          margin-bottom: 20px;
          border: 1px solid #EAECEF;
          transition: transform 0.2s;
        }
        .card-container:hover { transform: translateY(-2px); }

        .tag-pill {
          background-color: #E8F0FE;
          color: #0B1C2D;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 700;
          margin-right: 5px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .stButton > button {
          background-color: #1252A3;
          color: white !important;
          border-radius: 6px;
          font-weight: 600;
          border: none;
          padding: 0.5rem 1rem;
        }
        .stButton > button:hover { background-color: #0E4285; }

        h1, h2, h3 { color: #0B1C2D !important; font-weight: 800; }

        .enunciado { font-size: 1.15rem; line-height: 1.7; color: #202124; margin: 15px 0; }
        [data-testid="stMetricValue"] { color: #1252A3 !important; font-size: 2rem !important; }

        /* Extras: toolbar e chips */
        .toolbar {
          background-color: #FFFFFF;
          padding: 14px 16px;
          border-radius: 12px;
          border: 1px solid #EAECEF;
          box-shadow: 0 4px 12px rgba(0,0,0,0.05);
          margin-bottom: 14px;
        }
        .chip {
          display: inline-block;
          padding: 6px 10px;
          border-radius: 999px;
          border: 1px solid #EAECEF;
          background: #F7F9FC;
          color:#0B1C2D;
          font-size: .82rem;
          font-weight: 800;
          margin-right: 6px;
        }
        .small-muted { color:#5F6368; font-weight:650; font-size:.85rem; }
    </style>
    """, unsafe_allow_html=True)

def question_card(q):
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
            <div class="enunciado">{enunciado_curto}</div>
        </div>
        """, unsafe_allow_html=True)
