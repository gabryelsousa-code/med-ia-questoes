import streamlit as st
from supabase import create_client, Client
import json
import time
import pandas as pd

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Estratégia MedClone",
    page_icon="🦉",
    layout="wide"
)

# --- INICIALIZAÇÃO DO ESTADO ---
if 'supabase' not in st.session_state: st.session_state.supabase = None
if 'user' not in st.session_state: st.session_state.user = None
# Navegação
if 'indice_questao' not in st.session_state: st.session_state.indice_questao = 0
if 'questoes_carregadas' not in st.session_state: st.session_state.questoes_carregadas = []
if 'resposta_mostrada' not in st.session_state: st.session_state.resposta_mostrada = False
if 'tema_atual' not in st.session_state: st.session_state.tema_atual = "🌞 Claro"
if 'cesta_simulado' not in st.session_state: st.session_state.cesta_simulado = []

# --- FUNÇÕES ---
def init_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except:
        return None

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

# Funções de TAGS
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
# 🎨 LÓGICA DE TEMAS (VISIBILIDADE & AZUL MARINHO)
# ==============================================================================

temas = {
    "🌞 Claro": {
        # Fundos limpos
        "bg_app": "#F8F9FA", "bg_card": "#FFFFFF", "bg_sidebar": "#F0F2F5",
        # Textos com alto contraste (quase preto)
        "text_main": "#1A1A1A", "text_sec": "#555555", "border": "#DEE2E6",
        # Azul Marinho Profundo
        "primary": "#002855", "primary_hover": "#003F87",
        # Tags amarelas com texto preto
        "tag_bg": "#FFD700", "tag_txt": "#000000",
        # Feedback (Fundos pastéis com texto escuro)
        "success_bg": "#D4EDDA", "success_txt": "#155724",
        "error_bg": "#F8D7DA", "error_txt": "#721c24"
    },
    "🌙 Escuro": {
        # Fundos escuros profundos para evitar fadiga
        "bg_app": "#121212", "bg_card": "#1E1E1E", "bg_sidebar": "#2C2C2C",
        # Textos brancos ou cinza claro para leitura fácil
        "text_main": "#FFFFFF", "text_sec": "#CCCCCC", "border": "#404040",
        # Azul Brilhante para contraste no escuro (Marinho não aparece)
        "primary": "#4C9BFF", "primary_hover": "#3A86E8",
        # Tags douradas mais escuras
        "tag_bg": "#CFAE00", "tag_txt": "#000000",
        # Feedback (Fundos escuros com texto BRANCO)
        "success_bg": "#0A3622", "success_txt": "#FFFFFF",
        "error_bg": "#58151C", "error_txt": "#FFFFFF"
    }
}

# Controle na Sidebar (Antes de carregar CSS)
with st.sidebar:
    st.markdown("### Aparência")
    escolha_tema = st.radio("Tema", ["🌞 Claro", "🌙 Escuro"], label_visibility="collapsed")
    paleta = temas[escolha_tema]

# CSS DINÂMICO (Injetando as cores escolhidas)
st.markdown(f"""
<style>
    .stApp {{ background-color: {paleta['bg_app']}; color: {paleta['text_main']}; }}
    
    [data-testid="stSidebar"] {{ background-color: {paleta['bg_sidebar']}; border-right: 1px solid {paleta['border']}; }}
    
    .questao-card {{
        background-color: {paleta['bg_card']}; padding: 30px; border-radius: 12px;
        border: 1px solid {paleta['border']}; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 25px;
    }}
    
    .user-tag {{
        background-color: {paleta['tag_bg']}; color: {paleta['tag_txt']}; padding: 2px 8px;
        border-radius: 10px; font-size: 0.75rem; margin-right: 4px; font-weight: bold;
    }}

    /* Botões Azul Marinho/Brilhante */
    .stButton > button {{
        background-color: {paleta['primary']}; color: white !important; border-radius: 8px; border: none; font-weight: 600;
    }}
    .stButton > button:hover {{ background-color: {paleta['primary_hover']}; }}
    
    /* Textos e Títulos com a cor principal do tema */
    h1, h2, h3 {{ color: {paleta['primary']} !important; font-weight: 800; }}
    p, div, span, label, h4, h5, h6 {{ color: {paleta['text_main']}; }}
    .texto-secundario {{ color: {paleta['text_sec']} !important; }}
    
    /* Radio e Checkbox */
    .stRadio > div[role="radiogroup"] {{ background-color: {paleta['bg_app']}; border: 1px solid {paleta['border']}; border-radius: 8px; padding: 10px; }}
    .stCheckbox label {{ color: {paleta['text_main']}; }}
    
    /* Ajuste de Inputs */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {{
         color: {paleta['text_main']};
         background-color: {paleta['bg_card']};
         border-color: {paleta['border']};
    }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# TELA DE LOGIN
# ==============================================================================
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        # Título usa a cor primária (azul)
        st.markdown(f"<br><br><h1 style='text-align: center;'>🦉 MedResidency</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
            with tab1:
                email = st.text_input("E-mail", key="log_e")
                senha = st.text_input("Senha", type="password", key="log_p")
                if st.button("Entrar", use_container_width=True):
                    try:
                        res = st.session_state.supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state.user = res
                        st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
            with tab2:
                ne = st.text_input("E-mail", key="cad_e")
                ns = st.text_input("Senha", type="password", key="cad_p")
                if st.button("Cadastrar", use_container_width=True):
                    try:
                        st.session_state.supabase.auth.sign_up({"email": ne, "password": ns})
                        st.success("Cadastrado! Faça login.")
                    except Exception as e: st.error(f"Erro: {e}")
    st.stop()

# ==============================================================================
# SIDEBAR (MENU E LOGOUT)
# ==============================================================================
with st.sidebar:
    st.markdown("---")
    st.write(f"👤 {st.session_state.user.user.email}")
    
    st.markdown("### Menu")
    opcoes = ["🔍 Navegador", "📝 Resolver (Simulado)", "📊 Desempenho"]
    if is_admin(): opcoes += ["📤 Importar (Admin)", "⚙️ Gerenciar"]
    
    pagina = st.radio("", opcoes)
    
    st.markdown("---")
    if st.button("Sair da Conta", use_container_width=True):
        st.session_state.supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    if st.session_state.cesta_simulado:
        st.markdown("---")
        st.success(f"🎒 **{len(st.session_state.cesta_simulado)}** na cesta")
        if st.button("Limpar Cesta"):
            st.session_state.cesta_simulado = []
            st.rerun()

# ==============================================================================
# PÁGINA: NAVEGADOR (COM TAGS E SELEÇÃO)
# ==============================================================================
if pagina == "🔍 Navegador":
    st.header("Navegador de Questões")
    
    # Filtros
    c1, c2, c3 = st.columns([2, 2, 2])
    
    try:
        r = st.session_state.supabase.table("banco_questoes").select("disciplina").execute()
        d_list = sorted(list(set([x['disciplina'] for x in r.data if x['disciplina']])))
        d_list.insert(0, "Todas")
    except: d_list = ["Todas"]
    f_disc = c1.selectbox("Disciplina", d_list)
    
    tags_base = ["Cirurgia", "Clínica", "GO", "Pediatria", "Preventiva", "Difícil", "Revisar", "Favorita"]
    try:
        r_t = st.session_state.supabase.table("user_tags").select("tag").eq("user_email", st.session_state.user.user.email).execute()
        t_user = list(set([x['tag'] for x in r_t.data]))
        all_tags = sorted(list(set(tags_base + t_user)))
    except: all_tags = tags_base
    f_tags = c2.multiselect("Filtrar Tags", all_tags)
    
    f_txt = c3.text_input("Buscar Texto")
    
    q = st.session_state.supabase.table("banco_questoes").select("id, disciplina, assunto, enunciado")
    if f_disc != "Todas": q = q.eq("disciplina", f_disc)
    if f_txt: q = q.ilike("enunciado", f"%{f_txt}%")
    res = q.limit(100).execute()
    lista = res.data
    
    if f_tags and lista:
        ids_iniciais = [x['id'] for x in lista]
        r_tm = st.session_state.supabase.table("user_tags").select("questao_id").eq("user_email", st.session_state.user.user.email).in_("tag", f_tags).in_("questao_id", ids_iniciais).execute()
        ids_validos = [x['questao_id'] for x in r_tm.data]
        lista = [x for x in lista if x['id'] in ids_validos]

    st.markdown("---")
    
    if lista:
        cm, cb = st.columns([3, 1])
        cm.write(f"**{len(lista)}** questões encontradas.")
        if cb.button("Adicionar TODAS à Cesta"):
            novos = set(st.session_state.cesta_simulado) | set([x['id'] for x in lista])
            st.session_state.cesta_simulado = list(novos)
            st.rerun()
            
        for q in lista:
            cc, ct = st.columns([0.5, 9])
            sel = q['id'] in st.session_state.cesta_simulado
            if cc.checkbox("", value=sel, key=f"n_{q['id']}"):
                if not sel: st.session_state.cesta_simulado.append(q['id']); st.rerun()
            else:
                if sel: st.session_state.cesta_simulado.remove(q['id']); st.rerun()
            
            u_tags = get_user_tags(q['id'])
            html_tags = "".join([f"<span class='user-tag'>{t}</span>" for t in u_tags])
            
            ct.markdown(f"""
            <div class="questao-card" style="padding:15px; margin-bottom:10px;">
                <small style="color:{paleta['primary']}; font-weight:bold;">{q['disciplina']} | {q.get('assunto')}</small><br>
                {q['enunciado'][:120]}...<br>
                {html_tags}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nada encontrado.")

# ==============================================================================
# PÁGINA: RESOLVER (SIMULADO + CARD BONITO)
# ==============================================================================
elif pagina == "📝 Resolver (Simulado)":
    
    c_main, c_tool = st.columns([3, 1])
    
    with c_tool:
        st.markdown(f'<div class="questao-card" style="padding:15px;">', unsafe_allow_html=True)
        st.markdown("### 🏷️ Tags")
        if st.session_state.questoes_carregadas:
            qid = st.session_state.questoes_carregadas[st.session_state.indice_questao]['id']
            t_atuais = get_user_tags(qid)
            opt_tags = sorted(list(set(["Difícil", "Revisar", "Dúvida"] + t_atuais)))
            
            novas = st.multiselect("Editar:", opt_tags, default=t_atuais, key=f"editor_{qid}")
            
            if set(novas) != set(t_atuais):
                for t in novas: 
                    if t not in t_atuais: add_remove_tag(qid, t, "add")
                for t in t_atuais:
                    if t not in novas: add_remove_tag(qid, t, "remove")
                st.rerun()
                
            nova_txt = st.text_input("Nova Tag:")
            if st.button("Criar"):
                if nova_txt: add_remove_tag(qid, nova_txt, "add"); st.rerun()
        else:
            st.caption("Carregue questões.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("### 🕹️ Controle")
        if st.session_state.cesta_simulado:
            st.success(f"Modo Cesta ({len(st.session_state.cesta_simulado)})")
            if st.button("CARREGAR CESTA", use_container_width=True):
                r = st.session_state.supabase.table("banco_questoes").select("*").in_("id", st.session_state.cesta_simulado).execute()
                st.session_state.questoes_carregadas = r.data
                st.session_state.indice_questao = 0
                st.session_state.resposta_mostrada = False
                st.rerun()
        else:
            if st.button("Carregar 50 Aleatórias", use_container_width=True):
                r = st.session_state.supabase.table("banco_questoes").select("*").limit(50).execute()
                st.session_state.questoes_carregadas = r.data
                st.session_state.indice_questao = 0
                st.session_state.resposta_mostrada = False
                st.rerun()

    with c_main:
        if st.session_state.questoes_carregadas:
            qs = st.session_state.questoes_carregadas
            idx = st.session_state.indice_questao
            if idx >= len(qs): idx = 0
            q = qs[idx]
            
            ja_resp = False
            r_ant = None
            try:
                h = st.session_state.supabase.table("historico_usuario").select("*").eq("user_email", st.session_state.user.user.email).eq("questao_id", q['id']).execute()
                if h.data: ja_resp = True; r_ant = h.data[0]
            except: pass
            
            t_html = "".join([f"<span class='user-tag'>{t}</span>" for t in get_user_tags(q['id'])])
            
            st.markdown(f"""
            <div class="questao-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <div style="color:{paleta['primary']}; font-weight:bold; font-size: 1.1rem;">
                        {q['disciplina']} <span class="texto-secundario">|</span> {q.get('assunto')}
                    </div>
                    <div class="texto-secundario">ID: {q.get('id_original') or q['id']} • {idx+1}/{len(qs)}</div>
                </div>
                <div style="margin-bottom:15px;">{t_html}</div>
                <div style="font-size:1.15rem; line-height:1.6; font-weight: 500;">{q['enunciado']}</div>
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
            if cp.button("⬅️ Ant"):
                if idx > 0: st.session_state.indice_questao -= 1; st.session_state.resposta_mostrada = False; st.rerun()
            
            if not ja_resp:
                if cc.button("RESPONDER", use_container_width=True):
                    if escolha:
                        l = escolha.split(")")[0]
                        gab = q.get('gabarito', '').strip().upper()
                        ac = (l.upper() == gab)
                        st.session_state.supabase.table("historico_usuario").insert({"user_email": st.session_state.user.user.email, "questao_id": q['id'], "alternativa_marcada": l, "acertou": ac}).execute()
                        st.session_state.resposta_mostrada = True; st.rerun()
            else:
                cc.info(f"Respondida em {r_ant['data_resposta'][:10]}")
                
            if cn.button("Prox ➡️"):
                if idx < len(qs)-1: st.session_state.indice_questao += 1; st.session_state.resposta_mostrada = False; st.rerun()
            
            if st.session_state.resposta_mostrada or ja_resp:
                gab = q.get('gabarito', '').strip().upper()
                letra_f = escolha.split(")")[0] if escolha else (r_ant['alternativa_marcada'] if ja_resp else "")
                
                bg = paleta['success_bg'] if letra_f.upper() == gab else paleta['error_bg']
                txt_color = paleta['success_txt'] if letra_f.upper() == gab else paleta['error_txt']
                msg = "Acertou! 🎉" if letra_f.upper() == gab else f"Errou! Gabarito: **{gab}**"
                
                st.markdown(f"<div style='background:{bg}; color:{txt_color}; padding:15px; border-radius:8px; font-weight:bold; margin-top:15px;'>{msg}</div>", unsafe_allow_html=True)
                
                ce = q.get('comentario_estruturado')
                if ce and isinstance(ce, dict):
                    t1, t2 = st.tabs(["💡 Explicação", "❌ Incorretas"])
                    with t1:
                        st.write(ce.get('fundamentacao_cientifica'))
                        st.success(ce.get('justificativa_alternativa_correta', {}).get('explicacao'))
                    with t2:
                        inc = ce.get('analise_das_alternativas_incorretas', {})
                        for k, v in inc.items(): st.markdown(f"**{k})** {v}")
                else:
                    st.info(q.get('comentario_integral') or "Sem comentário.")
        else:
            st.info("👈 Use o controle à direita para carregar.")

# ==============================================================================
# PÁGINA: DESEMPENHO
# ==============================================================================
elif pagina == "📊 Desempenho":
    st.header("Dashboard")
    r = st.session_state.supabase.table("historico_usuario").select("*").eq("user_email", st.session_state.user.user.email).execute()
    df = pd.DataFrame(r.data)
    if not df.empty:
        ok = len(df[df['acertou']==True])
        st.metric("Acertos", f"{ok}/{len(df)}")
        st.dataframe(df[['questao_id', 'alternativa_marcada', 'acertou', 'data_resposta']])
    else: st.info("Sem dados.")

# ==============================================================================
# PÁGINA: ADMIN IMPORTS
# ==============================================================================
elif pagina == "📤 Importar (Admin)":
    if is_admin():
        st.header("Importar JSON")
        f = st.file_uploader("JSON")
        if f and st.button("Enviar"):
             d = json.load(f)
             l = []
             for i in d:
                 i['id_original'] = str(i.get('id', ''))
                 if 'id' in i and isinstance(i['id'], int): del i['id']
                 l.append(i)
             st.session_state.supabase.table("banco_questoes").insert(l).execute()
             st.success("Feito!")
    else: st.error("Acesso Negado")
