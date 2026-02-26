import streamlit as st
from supabase import create_client, Client
import json
import time
import math
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
if 'cesta_simulado' not in st.session_state: st.session_state.cesta_simulado = []
# Estados de Admin (Gestão)
if 'admin_pagina_atual' not in st.session_state: st.session_state.admin_pagina_atual = 1
if 'admin_editando_id' not in st.session_state: st.session_state.admin_editando_id = None
if 'ids_pagina_atual' not in st.session_state: st.session_state.ids_pagina_atual = []

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

def callback_selecionar_tudo_admin():
    estado = st.session_state.chk_master_admin
    if 'ids_pagina_atual' in st.session_state:
        for q_id in st.session_state.ids_pagina_atual:
            st.session_state[f"adm_sel_{q_id}"] = estado

if not st.session_state.supabase:
    st.session_state.supabase = init_supabase()

# ==============================================================================
# 🎨 PALETA DE CORES
# ==============================================================================

temas = {
    "🌞 Claro": {
        "bg_app": "#F0F2F6", "bg_card": "#FFFFFF",
        "text_main": "#1F2937", "text_sec": "#6B7280",
        "primary": "#002855", "border": "#E5E7EB",
        "input_bg": "#FFFFFF", "input_text": "#000000",
        "tag_bg": "#E0F2FE", "tag_txt": "#0369A1",
        "success": "#DEF7EC", "success_txt": "#03543F", "error": "#FDE8E8", "error_txt": "#9B1C1C"
    },
    "🌙 Escuro": {
        "bg_app": "#0F172A", "bg_card": "#1E293B",
        "text_main": "#F9FAFB", "text_sec": "#9CA3AF",
        "primary": "#4C9BFF", "border": "#374151",
        "input_bg": "#374151", "input_text": "#FFFFFF",
        "tag_bg": "#172554", "tag_txt": "#93C5FD",
        "success": "#064E3B", "success_txt": "#A7F3D0", "error": "#7F1D1D", "error_txt": "#FECACA"
    }
}

with st.sidebar:
    st.markdown("### 🎨 Aparência")
    escolha_tema = st.radio("Tema", ["🌞 Claro", "🌙 Escuro"], label_visibility="collapsed")
    p = temas[escolha_tema]

# ==============================================================================
# CSS BLINDADO (CORRIGE CORES E FORCE AZUL MARINHO)
# ==============================================================================
st.markdown(f"""
<style>
    /* 1. FUNDOS GERAIS */
    .stApp {{ background-color: {p['bg_app']}; color: {p['text_main']}; }}
    
    /* 2. HEADER E SIDEBAR (AZUL MARINHO FIXO) */
    header[data-testid="stHeader"] {{
        background-color: #002855 !important;
    }}
    [data-testid="stSidebar"] {{
        background-color: #002855 !important;
        border-right: 1px solid #001a38;
    }}
    
    /* Forçar texto branco na Sidebar e Header para contraste */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div {{
        color: #FFFFFF !important;
    }}
    
    /* Ícones do Menu Hambúrguer (Topo Direito) Brancos */
    header .st-emotion-cache-145kmo2, header button {{ color: white !important; fill: white !important; }}

    /* 3. CARDS */
    .questao-card {{
        background-color: {p['bg_card']}; padding: 25px; border-radius: 16px;
        border: 1px solid {p['border']}; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }}
    
    /* 4. INPUTS CORRIGIDOS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div, .stTextArea textarea {{
        background-color: {p['input_bg']} !important; color: {p['input_text']} !important;
        border-color: {p['border']} !important;
    }}
    .stSelectbox svg, .stMultiSelect svg {{ fill: {p['text_sec']} !important; }}
    
    /* 5. BOTÕES */
    .stButton > button {{
        background-color: {p['primary']}; color: white !important; border: none;
        border-radius: 10px; font-weight: 600; padding: 0.6rem 1.2rem;
    }}
    .stButton > button:hover {{ filter: brightness(1.2); }}

    /* 6. TAGS VISUAIS */
    .tag-visual {{
        background-color: {p['tag_bg']}; color: {p['tag_txt']}; padding: 4px 10px;
        border-radius: 20px; font-size: 0.75rem; font-weight: 800; margin-right: 5px;
    }}
    
    /* 7. TIPOGRAFIA */
    h1, h2, h3 {{ color: {p['primary']} !important; }}
    p, li, div {{ color: {p['text_main']}; }}
    .texto-sec {{ color: {p['text_sec']} !important; font-size: 0.9rem; }}
    
    /* 8. Radio Buttons */
    .stRadio > div[role="radiogroup"] {{ background-color: {p['bg_app']}; padding: 10px; border-radius: 10px; border: 1px solid {p['border']}; }}
    .stRadio label {{ color: {p['text_main']} !important; }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# LOGIN
# ==============================================================================
if not st.session_state.user:
    col_l, col_c, col_r = st.columns([1, 1.5, 1])
    with col_c:
        st.markdown(f"<div style='text-align: center; padding: 40px 0;'><h1 style='font-size: 3rem;'>🧬 MedResidency</h1></div>", unsafe_allow_html=True)
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
    
    opcoes = ["🔍 Navegador", "📝 Resolver (Simulado)", "📊 Desempenho"]
    if is_admin(): opcoes += ["📤 Admin: Importar", "⚙️ Admin: Gestão"]
    
    pagina = st.radio("Menu", opcoes)
    
    st.markdown("---")
    if st.button("SAIR", use_container_width=True):
        st.session_state.supabase.auth.sign_out(); st.session_state.user = None; st.rerun()
        
    if st.session_state.cesta_simulado:
        st.markdown("---")
        st.success(f"🎒 **{len(st.session_state.cesta_simulado)}** na cesta")
        if st.button("Limpar Cesta"): st.session_state.cesta_simulado = []; st.rerun()

# ==============================================================================
# PÁGINA: NAVEGADOR
# ==============================================================================
if pagina == "🔍 Navegador":
    st.header("🔍 Navegador de Questões")
    
    st.markdown(f'<div class="questao-card" style="padding: 20px;">', unsafe_allow_html=True)
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
    f_tags = c2.multiselect("Tags", all_tags)
    f_txt = c3.text_input("Buscar Texto", placeholder="Ex: Dengue...")
    st.markdown('</div>', unsafe_allow_html=True)
    
    q = st.session_state.supabase.table("banco_questoes").select("id, disciplina, assunto, enunciado")
    if f_disc != "Todas": q = q.eq("disciplina", f_disc)
    if f_txt: q = q.ilike("enunciado", f"%{f_txt}%")
    res = q.limit(100).execute()
    lista = res.data
    
    if f_tags and lista:
        ids_in = [x['id'] for x in lista]
        r_tm = st.session_state.supabase.table("user_tags").select("questao_id").eq("user_email", st.session_state.user.user.email).in_("tag", f_tags).in_("questao_id", ids_in).execute()
        ids_v = [x['questao_id'] for x in r_tm.data]
        lista = [x for x in lista if x['id'] in ids_v]

    if lista:
        cm, cb = st.columns([3, 1])
        cm.write(f"**{len(lista)}** encontradas")
        if cb.button("➕ Adicionar TODAS à Cesta"):
            novos = set(st.session_state.cesta_simulado) | set([x['id'] for x in lista])
            st.session_state.cesta_simulado = list(novos); st.rerun()
            
        for q in lista:
            cc, ct = st.columns([0.5, 9.5])
            sel = q['id'] in st.session_state.cesta_simulado
            if cc.checkbox("", value=sel, key=f"n_{q['id']}"):
                if not sel: st.session_state.cesta_simulado.append(q['id']); st.rerun()
            else:
                if sel: st.session_state.cesta_simulado.remove(q['id']); st.rerun()
            
            u_tags = get_user_tags(q['id'])
            html_tags = "".join([f"<span class='tag-visual'>{t}</span>" for t in u_tags])
            
            ct.markdown(f"""
            <div class="questao-card" style="padding:15px; margin-bottom:10px; border-left: 5px solid {p['primary']};">
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:{p['primary']}; font-weight:bold;">{q['disciplina']} <span class="texto-sec">| {q.get('assunto')}</span></span>
                    <span class="texto-sec">ID: {q.get('id')}</span>
                </div>
                <div style="margin: 8px 0;">{q['enunciado'][:140]}...</div>
                <div>{html_tags}</div>
            </div>
            """, unsafe_allow_html=True)
    else: st.info("Nada encontrado.")

# ==============================================================================
# PÁGINA: RESOLVER
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
            nt = st.text_input("Nova Tag:")
            if st.button("Criar"):
                if nt: add_remove_tag(qid, nt, "add"); st.rerun()
        else: st.caption("Carregue uma questão.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="questao-card" style="padding:15px;">', unsafe_allow_html=True)
        st.markdown("### 🕹️ Controle")
        if st.session_state.cesta_simulado:
            st.success(f"Cesta: {len(st.session_state.cesta_simulado)}")
            if st.button("▶️ INICIAR CESTA", use_container_width=True):
                r = st.session_state.supabase.table("banco_questoes").select("*").in_("id", st.session_state.cesta_simulado).execute()
                st.session_state.questoes_carregadas = r.data
                st.session_state.indice_questao = 0; st.session_state.resposta_mostrada = False; st.rerun()
        else:
            if st.button("🎲 50 Aleatórias", use_container_width=True):
                r = st.session_state.supabase.table("banco_questoes").select("*").limit(50).execute()
                st.session_state.questoes_carregadas = r.data
                st.session_state.indice_questao = 0; st.session_state.resposta_mostrada = False; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with c_main:
        if st.session_state.questoes_carregadas:
            qs = st.session_state.questoes_carregadas
            idx = st.session_state.indice_questao
            if idx >= len(qs): idx = 0
            q = qs[idx]
            ja_resp = False; r_ant = None
            try:
                h = st.session_state.supabase.table("historico_usuario").select("*").eq("user_email", st.session_state.user.user.email).eq("questao_id", q['id']).execute()
                if h.data: ja_resp = True; r_ant = h.data[0]
            except: pass
            
            t_html = "".join([f"<span class='tag-visual'>{t}</span>" for t in get_user_tags(q['id'])])
            st.markdown(f"""
            <div class="questao-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:15px; border-bottom:1px solid {p['border']}; padding-bottom:10px;">
                    <div><span style="font-size:1.2rem; font-weight:bold; color:{p['primary']};">{q['disciplina']}</span><span class="texto-sec"> | {q.get('assunto')}</span></div>
                    <div class="texto-sec">ID: {q.get('id_original') or q['id']} • {idx+1}/{len(qs)}</div>
                </div>
                <div style="margin-bottom:15px;">{t_html}</div>
                <div style="font-size:1.15rem; line-height:1.6; font-weight:500;">{q['enunciado']}</div>
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
                if cc.button("✅ RESPONDER", use_container_width=True):
                    if escolha:
                        l = escolha.split(")")[0]; gab = q.get('gabarito', '').strip().upper(); ac = (l.upper() == gab)
                        st.session_state.supabase.table("historico_usuario").insert({"user_email": st.session_state.user.user.email, "questao_id": q['id'], "alternativa_marcada": l, "acertou": ac}).execute()
                        st.session_state.resposta_mostrada = True; st.rerun()
            else: cc.info(f"Respondida em {r_ant['data_resposta'][:10]}")
            if cn.button("Próxima ➡️"):
                if idx < len(qs)-1: st.session_state.indice_questao += 1; st.session_state.resposta_mostrada = False; st.rerun()
            
            if st.session_state.resposta_mostrada or ja_resp:
                gab = q.get('gabarito', '').strip().upper()
                letra_f = escolha.split(")")[0] if escolha else (r_ant['alternativa_marcada'] if ja_resp else "")
                bg = p['success'] if letra_f.upper() == gab else p['error']
                color = p['success_txt'] if letra_f.upper() == gab else p['error_txt']
                msg = "Correto! 🎉" if letra_f.upper() == gab else f"Incorreto. Gabarito: **{gab}**"
                st.markdown(f"<div style='background:{bg}; color:{color}; padding:15px; border-radius:10px; font-weight:bold; margin-top:20px; text-align:center;'>{msg}</div>", unsafe_allow_html=True)
                ce = q.get('comentario_estruturado')
                if ce and isinstance(ce, dict):
                    t1, t2, t3 = st.tabs(["💡 Explicação", "❌ Incorretas", "📚 Resumo"])
                    with t1: st.write(ce.get('fundamentacao_cientifica')); st.success(ce.get('justificativa_alternativa_correta', {}).get('explicacao'))
                    with t2: 
                        inc = ce.get('analise_das_alternativas_incorretas', {})
                        for k, v in inc.items(): st.markdown(f"**{k})** {v}")
                    with t3: st.info(ce.get('raciocinio_clinico_resumido'))
                else: st.info(q.get('comentario_integral') or "Sem comentário.")
        else: st.info("👈 Carregue questões.")

# ==============================================================================
# PÁGINA: DESEMPENHO
# ==============================================================================
elif pagina == "📊 Desempenho":
    st.header("Seu Desempenho")
    r = st.session_state.supabase.table("historico_usuario").select("*").eq("user_email", st.session_state.user.user.email).execute()
    df = pd.DataFrame(r.data)
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Questões", len(df))
        ac = len(df[df['acertou']==True])
        c2.metric("Acertos", ac)
        c3.metric("Taxa", f"{(ac/len(df))*100:.1f}%")
        st.dataframe(df[['questao_id', 'alternativa_marcada', 'acertou', 'data_resposta']], use_container_width=True)
    else: st.info("Sem dados.")

# ==============================================================================
# PÁGINA: GESTÃO (ADMIN) - CORRIGIDA E RESTAURADA
# ==============================================================================
elif pagina == "⚙️ Admin: Gestão":
    if is_admin():
        st.header("Gestão de Questões")
        
        # MODO EDIÇÃO
        if st.session_state.admin_editando_id:
            res_edit = st.session_state.supabase.table("banco_questoes").select("*").eq("id", st.session_state.admin_editando_id).execute()
            if res_edit.data:
                q_ed = res_edit.data[0]
                st.info(f"Editando ID: {q_ed['id']}")
                with st.form("edit_form"):
                    col_a, col_b = st.columns(2)
                    nd = col_a.text_input("Disciplina", q_ed.get('disciplina'))
                    na = col_b.text_input("Assunto", q_ed.get('assunto'))
                    ne = st.text_area("Enunciado", q_ed.get('enunciado'), height=150)
                    
                    c_opt, c_com = st.columns(2)
                    alt_str = json.dumps(q_ed.get('alternativas', {}), indent=2, ensure_ascii=False)
                    nalt = c_opt.text_area("Alternativas (JSON)", alt_str, height=200)
                    com_str = json.dumps(q_ed.get('comentario_estruturado', {}), indent=2, ensure_ascii=False)
                    ncom = c_com.text_area("Comentário Estruturado (JSON)", com_str, height=200)
                    
                    ngab = st.text_input("Gabarito", q_ed.get('gabarito'))
                    
                    b1, b2, b3 = st.columns([1,1,1])
                    if b1.form_submit_button("💾 SALVAR"):
                        try:
                            upd = {"disciplina": nd, "assunto": na, "enunciado": ne, "gabarito": ngab, 
                                   "alternativas": json.loads(nalt), "comentario_estruturado": json.loads(ncom)}
                            st.session_state.supabase.table("banco_questoes").update(upd).eq("id", q_ed['id']).execute()
                            st.success("Salvo!"); st.session_state.admin_editando_id = None; time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"Erro JSON: {e}")
                    
                    if b2.form_submit_button("CANCELAR"):
                        st.session_state.admin_editando_id = None; st.rerun()
                        
                    if b3.form_submit_button("🗑️ DELETAR", type="primary"):
                        st.session_state.supabase.table("banco_questoes").delete().eq("id", q_ed['id']).execute()
                        st.session_state.admin_editando_id = None; st.rerun()
        
        # MODO LISTA
        else:
            c_ord, c_nav = st.columns([1, 2])
            ordem = c_ord.selectbox("Ordenar", ["Recentes", "Antigas"])
            
            ITENS_PAG = 50
            try:
                cnt = st.session_state.supabase.table("banco_questoes").select("id", count='exact').execute()
                tot_p = math.ceil(cnt.count / ITENS_PAG)
            except: tot_p = 1
            
            cn1, cn2, cn3 = c_nav.columns([1,2,1])
            if cn1.button("⬅️") and st.session_state.admin_pagina_atual > 1: st.session_state.admin_pagina_atual -= 1; st.rerun()
            cn2.write(f"<center>{st.session_state.admin_pagina_atual} / {tot_p}</center>", unsafe_allow_html=True)
            if cn3.button("➡️") and st.session_state.admin_pagina_atual < tot_p: st.session_state.admin_pagina_atual += 1; st.rerun()
            
            off = (st.session_state.admin_pagina_atual - 1) * ITENS_PAG
            qry = st.session_state.supabase.table("banco_questoes").select("id, disciplina, assunto, enunciado")
            if "Recentes" in ordem: qry = qry.order("id", desc=True)
            else: qry = qry.order("id", desc=False)
            lista = qry.range(off, off + ITENS_PAG - 1).execute().data
            
            st.session_state.ids_pagina_atual = [x['id'] for x in lista] if lista else []
            
            st.markdown("---")
            # AÇÃO EM MASSA
            cont_topo = st.container()
            st.checkbox("Selecionar Tudo da Página", key="chk_master_admin", on_change=callback_selecionar_tudo_admin)
            
            ids_sel = []
            if lista:
                for item in lista:
                    cc, ct, ce, cd = st.columns([0.5, 9, 0.5, 0.5])
                    chk_key = f"adm_sel_{item['id']}"
                    if chk_key not in st.session_state: st.session_state[chk_key] = False
                    
                    if cc.checkbox("", key=chk_key): ids_sel.append(item['id'])
                    
                    ct.markdown(f"**[{item['id']}]** {item['disciplina']} - {item['enunciado'][:80]}...")
                    if ce.button("✏️", key=f"e_{item['id']}"): st.session_state.admin_editando_id = item['id']; st.rerun()
                    if cd.button("🗑️", key=f"d_{item['id']}"): 
                        st.session_state.supabase.table("banco_questoes").delete().eq("id", item['id']).execute(); st.rerun()
                    st.divider()
            
            if ids_sel:
                with cont_topo:
                    st.error(f"{len(ids_sel)} SELECIONADOS")
                    if st.button("🗑️ DELETAR SELECIONADOS", type="primary"):
                        st.session_state.supabase.table("banco_questoes").delete().in_("id", ids_sel).execute(); st.rerun()
            
    else: st.error("Acesso Negado")

elif pagina == "📤 Admin: Importar":
    if is_admin():
        st.header("Importar JSON")
        f = st.file_uploader("Arquivo JSON")
        if f and st.button("Processar"):
             d = json.load(f)
             l = []
             for i in d:
                 i['id_original'] = str(i.get('id', ''))
                 if 'id' in i and isinstance(i['id'], int): del i['id']
                 l.append(i)
             st.session_state.supabase.table("banco_questoes").insert(l).execute()
             st.success("Importado!")
    else: st.error("Acesso Negado")
