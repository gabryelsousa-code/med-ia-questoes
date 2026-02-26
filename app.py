import streamlit as st
from supabase import create_client, Client
import json
import time
import pandas as pd

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedResidency Pro",
    page_icon="🧬",
    layout="wide"
)

# --- INICIALIZAÇÃO DO ESTADO ---
if 'supabase' not in st.session_state: st.session_state.supabase = None
if 'user' not in st.session_state: st.session_state.user = None
if 'indice_questao' not in st.session_state: st.session_state.indice_questao = 0
if 'questoes_carregadas' not in st.session_state: st.session_state.questoes_carregadas = []
if 'resposta_mostrada' not in st.session_state: st.session_state.resposta_mostrada = False
if 'tema_atual' not in st.session_state: st.session_state.tema_atual = "🌞 Claro"
if 'cesta_criacao' not in st.session_state: st.session_state.cesta_criacao = [] # IDs para criar novo simulado
if 'simulado_ativo_id' not in st.session_state: st.session_state.simulado_ativo_id = None # ID do simulado que estou respondendo agora

# --- FUNÇÕES ---
def init_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except: return None

def is_admin():
    if st.session_state.user:
        return st.session_state.user.user.email == st.secrets["admin"]["email"]
    return False

def ordenar_alternativas(alternativas):
    if not alternativas: return []
    chaves = list(alternativas.keys())
    chaves_upper = [k.upper() for k in chaves]
    if set(chaves_upper) == {'C', 'E'}:
        return sorted(chaves, key=lambda x: 0 if x.upper() == 'C' else 1)
    if set(chaves_upper) == {'V', 'F'}:
         return sorted(chaves, key=lambda x: 0 if x.upper() == 'V' else 1)
    return sorted(chaves)

def get_user_tags(q_id):
    try:
        res = st.session_state.supabase.table("user_tags").select("tag").eq("user_email", st.session_state.user.user.email).eq("questao_id", q_id).execute()
        return [r['tag'] for r in res.data]
    except: return []

def add_remove_tag(q_id, tag, action="add"):
    email = st.session_state.user.user.email
    try:
        if action == "add":
            st.session_state.supabase.table("user_tags").insert({"user_email": email, "questao_id": q_id, "tag": tag}).execute()
        elif action == "remove":
            st.session_state.supabase.table("user_tags").delete().eq("user_email", email).eq("questao_id", q_id).eq("tag", tag).execute()
    except: pass

if not st.session_state.supabase:
    st.session_state.supabase = init_supabase()

# ==============================================================================
# 🎨 PALETA DE CORES (MODO DARK/LIGHT + AZUL MARINHO)
# ==============================================================================
temas = {
    "🌞 Claro": {
        "bg_app": "#F0F2F6", "bg_card": "#FFFFFF", "text_main": "#1F2937", "text_sec": "#6B7280",
        "primary": "#002855", "border": "#E5E7EB", "input_bg": "#FFFFFF", "input_text": "#000000",
        "tag_bg": "#E0F2FE", "tag_txt": "#0369A1", "success": "#DEF7EC", "success_txt": "#03543F", "error": "#FDE8E8", "error_txt": "#9B1C1C"
    },
    "🌙 Escuro": {
        "bg_app": "#0F172A", "bg_card": "#1E293B", "text_main": "#F9FAFB", "text_sec": "#9CA3AF",
        "primary": "#4C9BFF", "border": "#374151", "input_bg": "#374151", "input_text": "#FFFFFF",
        "tag_bg": "#172554", "tag_txt": "#93C5FD", "success": "#064E3B", "success_txt": "#A7F3D0", "error": "#7F1D1D", "error_txt": "#FECACA"
    }
}

with st.sidebar:
    st.markdown("### 🎨 Aparência")
    escolha_tema = st.radio("Tema", ["🌞 Claro", "🌙 Escuro"], label_visibility="collapsed")
    p = temas[escolha_tema]

st.markdown(f"""
<style>
    .stApp {{ background-color: {p['bg_app']}; color: {p['text_main']}; }}
    header[data-testid="stHeader"], [data-testid="stSidebar"] {{ background-color: #002855 !important; }}
    [data-testid="stSidebar"] * {{ color: #FFFFFF !important; }}
    
    .questao-card {{
        background-color: {p['bg_card']}; padding: 25px; border-radius: 16px;
        border: 1px solid {p['border']}; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 20px;
    }}
    .simulado-card {{
        background-color: {p['bg_card']}; padding: 15px; border-radius: 12px;
        border-left: 5px solid {p['primary']}; border-right: 1px solid {p['border']}; 
        border-top: 1px solid {p['border']}; border-bottom: 1px solid {p['border']};
        margin-bottom: 15px; cursor: pointer; transition: transform 0.2s;
    }}
    .simulado-card:hover {{ transform: scale(1.01); }}

    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {{
        background-color: {p['input_bg']} !important; color: {p['input_text']} !important; border-color: {p['border']} !important;
    }}
    .stSelectbox svg, .stMultiSelect svg {{ fill: {p['text_sec']} !important; }}
    
    .stButton > button {{
        background-color: {p['primary']}; color: white !important; border-radius: 10px; border: none; font-weight: 600; padding: 0.6rem 1.2rem;
    }}
    .stButton > button:hover {{ filter: brightness(1.2); }}
    
    .tag-visual {{ background-color: {p['tag_bg']}; color: {p['tag_txt']}; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; margin-right: 5px; }}
    h1, h2, h3 {{ color: {p['primary']} !important; }}
    p, div, span, label {{ color: {p['text_main']}; }}
    .texto-sec {{ color: {p['text_sec']} !important; font-size: 0.9rem; }}
    .stRadio > div[role="radiogroup"] {{ background-color: {p['bg_app']}; padding: 10px; border-radius: 10px; border: 1px solid {p['border']}; }}
    .stRadio label {{ color: {p['text_main']} !important; }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# LOGIN
# ==============================================================================
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown(f"<div style='text-align:center; padding:40px 0;'><h1 style='font-size:3rem;'>🧬 MedResidency</h1></div>", unsafe_allow_html=True)
        with st.container(border=True):
            tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
            with tab1:
                e = st.text_input("Email", key="l_e")
                s = st.text_input("Senha", type="password", key="l_p")
                if st.button("ENTRAR", use_container_width=True):
                    try:
                        res = st.session_state.supabase.auth.sign_in_with_password({"email": e, "password": s})
                        st.session_state.user = res; st.rerun()
                    except Exception as err: st.error(f"Erro: {err}")
            with tab2:
                ne = st.text_input("Email", key="c_e")
                ns = st.text_input("Senha", type="password", key="c_p")
                if st.button("CRIAR CONTA", use_container_width=True):
                    try:
                        st.session_state.supabase.auth.sign_up({"email": ne, "password": ns})
                        st.success("Criado! Faça login.")
                    except Exception as err: st.error(f"Erro: {err}")
    st.stop()

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("---")
    st.markdown(f"<div style='padding:10px; background:rgba(255,255,255,0.1); border-radius:8px;'>👤 {st.session_state.user.user.email}</div>", unsafe_allow_html=True)
    
    # MENU ATUALIZADO
    pagina = st.radio("Menu", ["📂 Meus Simulados", "📝 Criar Simulado", "📊 Desempenho Global", "⚙️ Admin"])
    
    st.markdown("---")
    if st.button("SAIR", use_container_width=True):
        st.session_state.supabase.auth.sign_out(); st.session_state.user = None; st.rerun()

# ==============================================================================
# PÁGINA 1: CRIADOR DE SIMULADOS (ESTILO MARKETPLACE)
# ==============================================================================
if pagina == "📝 Criar Simulado":
    st.header("Criar Novo Simulado")
    
    # --- ÁREA DE SELEÇÃO E FILTROS ---
    c_main, c_cart = st.columns([3, 1])
    
    with c_main:
        st.markdown(f'<div class="questao-card" style="padding: 20px;">', unsafe_allow_html=True)
        f1, f2, f3 = st.columns([2, 2, 2])
        
        # Filtros
        try:
            r = st.session_state.supabase.table("banco_questoes").select("disciplina").execute()
            d_list = sorted(list(set([x['disciplina'] for x in r.data if x['disciplina']])))
            d_list.insert(0, "Todas")
        except: d_list = ["Todas"]
        
        filtro_disc = f1.selectbox("Disciplina", d_list)
        
        tags_base = ["Cirurgia", "Clínica", "GO", "Pediatria", "Preventiva", "Difícil", "Revisar", "Favorita"]
        try:
            r_t = st.session_state.supabase.table("user_tags").select("tag").eq("user_email", st.session_state.user.user.email).execute()
            all_tags = sorted(list(set(tags_base + [x['tag'] for x in r_t.data])))
        except: all_tags = tags_base
        
        filtro_tag = f2.multiselect("Tags", all_tags)
        filtro_txt = f3.text_input("Palavra-Chave")
        st.markdown('</div>', unsafe_allow_html=True)

        # Buscar
        q = st.session_state.supabase.table("banco_questoes").select("id, disciplina, assunto, enunciado")
        if filtro_disc != "Todas": q = q.eq("disciplina", filtro_disc)
        if filtro_txt: q = q.ilike("enunciado", f"%{filtro_txt}%")
        res = q.limit(50).execute()
        lista = res.data
        
        # Filtro de Tag no Python
        if filtro_tag and lista:
            ids_in = [x['id'] for x in lista]
            r_tm = st.session_state.supabase.table("user_tags").select("questao_id").eq("user_email", st.session_state.user.user.email).in_("tag", filtro_tag).in_("questao_id", ids_in).execute()
            ids_v = [x['questao_id'] for x in r_tm.data]
            lista = [x for x in lista if x['id'] in ids_v]

        # Lista de Seleção
        if lista:
            st.write(f"**{len(lista)}** resultados.")
            # Botão adicionar tudo
            if st.button("➕ Adicionar TODOS desta lista"):
                 novos = set(st.session_state.cesta_criacao) | set([x['id'] for x in lista])
                 st.session_state.cesta_criacao = list(novos); st.rerun()

            for q in lista:
                cc, ct = st.columns([0.5, 9.5])
                sel = q['id'] in st.session_state.cesta_criacao
                if cc.checkbox("", value=sel, key=f"c_{q['id']}"):
                    if not sel: st.session_state.cesta_criacao.append(q['id']); st.rerun()
                else:
                    if sel: st.session_state.cesta_criacao.remove(q['id']); st.rerun()
                
                u_tags = get_user_tags(q['id'])
                h_tags = "".join([f"<span class='tag-visual'>{t}</span>" for t in u_tags])
                
                ct.markdown(f"""
                <div class="questao-card" style="padding:15px; margin-bottom:10px;">
                    <div style="font-weight:bold; color:{p['primary']};">{q['disciplina']} <span class="texto-sec">| {q.get('assunto')}</span></div>
                    <div style="margin:5px 0;">{q['enunciado'][:120]}...</div>
                    <div>{h_tags}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nenhuma questão encontrada.")

    # --- BARRA LATERAL: CESTA E SALVAR ---
    with c_cart:
        st.markdown(f'<div class="questao-card">', unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;'>🎒 Cesta</h3>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center; font-size:2rem; font-weight:bold; color:{p['primary']}'>{len(st.session_state.cesta_criacao)}</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center;'>questões selecionadas</div><br>", unsafe_allow_html=True)
        
        nome_simulado = st.text_input("Nome do Simulado", placeholder="Ex: Cardio - Semana 1")
        
        if st.button("💾 SALVAR SIMULADO", use_container_width=True, type="primary"):
            if not nome_simulado: st.error("Digite um nome!"); st.stop()
            if not st.session_state.cesta_criacao: st.error("Selecione questões!"); st.stop()
            
            try:
                # 1. Cria Simulado
                r1 = st.session_state.supabase.table("simulados").insert({
                    "user_email": st.session_state.user.user.email,
                    "nome": nome_simulado
                }).execute()
                simulado_id = r1.data[0]['id']
                
                # 2. Insere Itens
                itens = [{"simulado_id": simulado_id, "questao_id": qid} for qid in st.session_state.cesta_criacao]
                st.session_state.supabase.table("simulado_itens").insert(itens).execute()
                
                st.session_state.cesta_criacao = [] # Limpa
                st.success("Simulado Criado!"); time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Erro ao salvar: {e}")
            
        if st.button("Limpar Seleção", use_container_width=True):
            st.session_state.cesta_criacao = []; st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)


# ==============================================================================
# PÁGINA 2: MEUS SIMULADOS (PASTAS) & RESOLUÇÃO
# ==============================================================================
elif pagina == "📂 Meus Simulados":
    
    # MODO: LISTAGEM DE PASTAS
    if st.session_state.simulado_ativo_id is None:
        st.header("Meus Simulados")
        
        # Busca simulados do usuário
        res_s = st.session_state.supabase.table("simulados").select("*").eq("user_email", st.session_state.user.user.email).order("criado_em", desc=True).execute()
        simulados = res_s.data
        
        if simulados:
            col1, col2 = st.columns([3, 1])
            with col1:
                for sim in simulados:
                    # Busca estatísticas desse simulado específico
                    # (Total questões)
                    r_qtd = st.session_state.supabase.table("simulado_itens").select("id", count='exact').eq("simulado_id", sim['id']).execute()
                    qtd_total = r_qtd.count
                    
                    # (Total respondidas/acertos neste simulado)
                    # Precisamos filtrar historico pelo simulado_id
                    try:
                        r_hist = st.session_state.supabase.table("historico_usuario").select("*").eq("simulado_id", sim['id']).execute()
                        respondidas = len(r_hist.data)
                        acertos = len([h for h in r_hist.data if h['acertou']])
                        perc = (acertos/respondidas)*100 if respondidas > 0 else 0
                    except: respondidas=0; acertos=0; perc=0
                    
                    # CARD DO SIMULADO
                    with st.container():
                        c_info, c_play, c_del = st.columns([8, 1.5, 0.5])
                        
                        # Info Visual
                        c_info.markdown(f"""
                        <div class="simulado-card">
                            <div style="font-size:1.2rem; font-weight:bold; color:{p['primary']}">{sim['nome']}</div>
                            <div class="texto-sec">Criado em: {sim['criado_em'][:10]}</div>
                            <div style="margin-top:10px; font-weight:500;">
                                Questões: {qtd_total} | Feitas: {respondidas} | Acertos: <span style="color:{p['success_txt']}">{acertos} ({perc:.0f}%)</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Botão Play (Carrega o simulado)
                        if c_play.button("▶️ ABRIR", key=f"play_{sim['id']}", use_container_width=True):
                            # Carrega questões deste simulado
                            r_itens = st.session_state.supabase.table("simulado_itens").select("questao_id").eq("simulado_id", sim['id']).execute()
                            ids = [x['questao_id'] for x in r_itens.data]
                            
                            # Busca os dados completos das questões
                            if ids:
                                r_q = st.session_state.supabase.table("banco_questoes").select("*").in_("id", ids).execute()
                                st.session_state.questoes_carregadas = r_q.data
                                st.session_state.indice_questao = 0
                                st.session_state.resposta_mostrada = False
                                st.session_state.simulado_ativo_id = sim['id'] # ATIVA O MODO RESOLUÇÃO
                                st.rerun()
                            else: st.warning("Simulado vazio.")
                        
                        # Botão Delete
                        if c_del.button("🗑️", key=f"del_s_{sim['id']}"):
                            st.session_state.supabase.table("simulados").delete().eq("id", sim['id']).execute()
                            st.rerun()
        else:
            st.info("Você ainda não criou nenhum simulado. Vá em 'Criar Simulado' para começar.")

    # MODO: RESOLUÇÃO (DENTRO DO SIMULADO)
    else:
        # Busca nome do simulado atual
        try:
            r_name = st.session_state.supabase.table("simulados").select("nome").eq("id", st.session_state.simulado_ativo_id).execute()
            nome_atual = r_name.data[0]['nome']
        except: nome_atual = "Simulado"

        # Header com botão voltar
        c_back, c_title = st.columns([1, 8])
        if c_back.button("🔙 Sair"):
            st.session_state.simulado_ativo_id = None; st.session_state.questoes_carregadas = []; st.rerun()
        c_title.markdown(f"## 📝 Resolvendo: {nome_atual}")
        
        # --- INTERFACE DE RESOLUÇÃO (Igual à anterior, mas salva com simulado_id) ---
        if st.session_state.questoes_carregadas:
            qs = st.session_state.questoes_carregadas
            idx = st.session_state.indice_questao
            if idx >= len(qs): idx = 0
            q = qs[idx]
            
            # Verifica se já respondeu NESTE simulado
            ja_resp = False; r_ant = None
            try:
                h = st.session_state.supabase.table("historico_usuario").select("*")\
                    .eq("simulado_id", st.session_state.simulado_ativo_id)\
                    .eq("questao_id", q['id']).execute()
                if h.data: ja_resp = True; r_ant = h.data[0]
            except: pass
            
            # Layout da Questão
            st.markdown(f"""
            <div class="questao-card">
                <div style="font-weight:bold; color:{p['primary']}; margin-bottom:10px;">
                    {q['disciplina']} | {q.get('assunto')} <span class="texto-sec" style="float:right;">{idx+1}/{len(qs)}</span>
                </div>
                <div style="font-size:1.15rem; line-height:1.6;">{q['enunciado']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            alts = q.get('alternativas', {})
            ch = ordenar_alternativas(alts)
            opts = [f"{k}) {alts[k]}" for k in ch]
            
            sel_idx = None
            if ja_resp and r_ant['alternativa_marcada']:
                for i, o in enumerate(opts):
                    if o.startswith(r_ant['alternativa_marcada'] + ")"): sel_idx = i
            
            escolha = st.radio("Alternativas:", opts, index=sel_idx, disabled=ja_resp, label_visibility="collapsed")
            st.write("")
            
            cp, cc, cn = st.columns([1, 2, 1])
            if cp.button("⬅️ Anterior"):
                if idx > 0: st.session_state.indice_questao -= 1; st.session_state.resposta_mostrada = False; st.rerun()
            
            if not ja_resp:
                if cc.button("✅ CONFIRMAR", use_container_width=True):
                    if escolha:
                        l = escolha.split(")")[0]; gab = q.get('gabarito', '').strip().upper(); ac = (l.upper() == gab)
                        # SALVA COM O ID DO SIMULADO
                        st.session_state.supabase.table("historico_usuario").insert({
                            "user_email": st.session_state.user.user.email, 
                            "questao_id": q['id'], 
                            "alternativa_marcada": l, 
                            "acertou": ac,
                            "simulado_id": st.session_state.simulado_ativo_id
                        }).execute()
                        st.session_state.resposta_mostrada = True; st.rerun()
            else: cc.info(f"Respondida!")
            
            if cn.button("Próxima ➡️"):
                if idx < len(qs)-1: st.session_state.indice_questao += 1; st.session_state.resposta_mostrada = False; st.rerun()
            
            # Feedback e Comentários (Igual)
            if st.session_state.resposta_mostrada or ja_resp:
                gab = q.get('gabarito', '').strip().upper()
                letra_f = escolha.split(")")[0] if escolha else (r_ant['alternativa_marcada'] if ja_resp else "")
                bg = p['success'] if letra_f.upper() == gab else p['error']
                msg = "Acertou! 🎉" if letra_f.upper() == gab else f"Errou! Gabarito: **{gab}**"
                st.markdown(f"<div style='background:{bg}; padding:15px; border-radius:10px; font-weight:bold; margin-top:15px; text-align:center; color:{p['text_main']}'>{msg}</div>", unsafe_allow_html=True)
                
                ce = q.get('comentario_estruturado')
                if ce and isinstance(ce, dict):
                    with st.expander("Ver Comentários", expanded=True):
                        st.write(ce.get('fundamentacao_cientifica'))
                        st.success(ce.get('justificativa_alternativa_correta', {}).get('explicacao'))

# ==============================================================================
# PÁGINA: DESEMPENHO GLOBAL
# ==============================================================================
elif pagina == "📊 Desempenho Global":
    st.header("Estatísticas Gerais")
    r = st.session_state.supabase.table("historico_usuario").select("*").eq("user_email", st.session_state.user.user.email).execute()
    df = pd.DataFrame(r.data)
    if not df.empty:
        c1, c2 = st.columns(2)
        c1.metric("Questões Totais", len(df))
        ac = len(df[df['acertou']==True])
        c2.metric("Acertos Totais", f"{ac} ({(ac/len(df))*100:.1f}%)")
        st.dataframe(df, use_container_width=True)
    else: st.info("Sem dados.")

# ==============================================================================
# ADMIN
# ==============================================================================
elif pagina == "⚙️ Admin":
    if is_admin():
        st.header("Admin Import")
        f = st.file_uploader("JSON")
        if f and st.button("Enviar"):
             d = json.load(f)
             l = []
             for i in d:
                 i['id_original'] = str(i.get('id', ''))
                 if 'id' in i and isinstance(i['id'], int): del i['id']
                 l.append(i)
             st.session_state.supabase.table("banco_questoes").insert(l).execute()
             st.success("OK")
    else: st.error("Negado")
