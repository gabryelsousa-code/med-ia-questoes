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
if 'modo_simulado' not in st.session_state: st.session_state.modo_simulado = False # Novo
if 'cesta_simulado' not in st.session_state: st.session_state.cesta_simulado = [] # Novo: Lista de IDs selecionados

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

# Função para Gerenciar Tags
def get_user_tags(q_id):
    """Busca as tags que o usuário atual deu para essa questão"""
    try:
        res = st.session_state.supabase.table("user_tags")\
            .select("tag")\
            .eq("user_email", st.session_state.user.user.email)\
            .eq("questao_id", q_id).execute()
        return [r['tag'] for r in res.data]
    except: return []

def add_remove_tag(q_id, tag, action="add"):
    """Adiciona ou remove tag no banco"""
    email = st.session_state.user.user.email
    try:
        if action == "add":
            st.session_state.supabase.table("user_tags").insert({"user_email": email, "questao_id": q_id, "tag": tag}).execute()
        elif action == "remove":
            st.session_state.supabase.table("user_tags").delete()\
                .eq("user_email", email).eq("questao_id", q_id).eq("tag", tag).execute()
    except: pass

if not st.session_state.supabase:
    st.session_state.supabase = init_supabase()

# ==============================================================================
# 🎨 CSS PERSONALIZADO (ROXO & TAGS)
# ==============================================================================
st.markdown("""
<style>
    .stApp { background-color: #fdfdfd; color: #2c3e50; }
    
    /* Tags Personalizadas */
    .user-tag {
        background-color: #ffeb3b;
        color: #333;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
        border: 1px solid #fbc02d;
        margin-right: 4px;
        font-weight: bold;
    }
    
    /* Card da Questão */
    .questao-card {
        background-color: white; padding: 30px; border-radius: 12px;
        border: 1px solid #e0e0e0; box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 25px;
    }
    
    /* Botões */
    .stButton > button {
        background-color: #5E35B1; color: white !important; border-radius: 8px; border: none; font-weight: 600;
    }
    .stButton > button:hover { background-color: #4527a0; }
    
    /* Checkbox Grande para o Navegador */
    .stCheckbox { padding-top: 10px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# LOGIN
# ==============================================================================
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown(f"<br><h1 style='text-align: center; color: #5E35B1;'>🦉 MedResidency</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar", use_container_width=True):
                try:
                    res = st.session_state.supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user = res
                    st.rerun()
                except Exception as e: st.error(f"Erro: {e}")
    st.stop()

# HEADER
col_logo, col_user = st.columns([8, 2])
with col_logo: st.markdown(f"<h3 style='margin:0; padding-top:10px; color:#5E35B1;'>🦉 MedResidency</h3>", unsafe_allow_html=True)
with col_user: st.markdown(f"<div style='text-align:right; padding-top:15px; font-size:0.9rem;'>👤 {st.session_state.user.user.email}</div>", unsafe_allow_html=True)
st.markdown("---")

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("### Menu")
    # Menu reorganizado
    pagina = st.radio("", ["🔍 Navegador de Questões", "📝 Resolver (Simulado)", "📊 Meu Desempenho", "📤 Importar (Admin)"])
    
    st.markdown("---")
    
    # Exibe Status da Cesta de Simulado
    if st.session_state.cesta_simulado:
        st.success(f"🎒 **{len(st.session_state.cesta_simulado)}** questões na cesta")
        if st.button("Limpar Cesta"):
            st.session_state.cesta_simulado = []
            st.rerun()
    else:
        st.caption("Sua cesta de simulado está vazia.")

# ==============================================================================
# PÁGINA: NAVEGADOR DE QUESTÕES (NOVA!)
# ==============================================================================
if pagina == "🔍 Navegador de Questões":
    st.header("Navegador & Filtros")
    
    # --- FILTROS ---
    c_filtro1, c_filtro2, c_filtro3 = st.columns([2, 2, 2])
    
    # 1. Filtro Disciplina
    try:
        r = st.session_state.supabase.table("banco_questoes").select("disciplina").execute()
        disc_list = sorted(list(set([x['disciplina'] for x in r.data if x['disciplina']])))
        disc_list.insert(0, "Todas")
    except: disc_list = ["Todas"]
    filtro_disc = c_filtro1.selectbox("Disciplina", disc_list)
    
    # 2. Filtro por TAGS (Inclusão das Grandes Áreas + Personalizadas)
    tags_padrao = ["Cirurgia", "Clínica Médica", "Ginecologia", "Obstetrícia", "Pediatria", "Preventiva", "Difícil", "Revisar", "Favorita"]
    
    # Busca tags que o usuário já usou no banco para adicionar à lista
    try:
        r_tags = st.session_state.supabase.table("user_tags").select("tag").eq("user_email", st.session_state.user.user.email).execute()
        tags_usuario = list(set([x['tag'] for x in r_tags.data]))
        todas_tags = sorted(list(set(tags_padrao + tags_usuario)))
    except: todas_tags = tags_padrao
    
    filtro_tags = c_filtro2.multiselect("Filtrar por Tags", todas_tags)
    
    # 3. Busca Texto
    busca_texto = c_filtro3.text_input("Buscar no enunciado", placeholder="Ex: Dengue, HAS...")

    # --- QUERY ---
    # Monta a query base
    query = st.session_state.supabase.table("banco_questoes").select("id, disciplina, assunto, enunciado")
    
    if filtro_disc != "Todas":
        query = query.eq("disciplina", filtro_disc)
        
    if busca_texto:
        query = query.ilike("enunciado", f"%{busca_texto}%")
        
    # Executa a query inicial (limite para performance)
    res_questoes = query.limit(100).execute()
    lista_questoes = res_questoes.data
    
    # --- FILTRAGEM DE TAGS (PÓS-PROCESSAMENTO) ---
    # Como tags estão em outra tabela, é mais performático filtrar IDs aqui se houver tag selecionada
    if filtro_tags and lista_questoes:
        ids_iniciais = [q['id'] for q in lista_questoes]
        # Busca quais desses IDs possuem as tags selecionadas
        r_tag_match = st.session_state.supabase.table("user_tags")\
            .select("questao_id")\
            .eq("user_email", st.session_state.user.user.email)\
            .in_("tag", filtro_tags)\
            .in_("questao_id", ids_iniciais)\
            .execute()
        
        ids_com_tag = [r['questao_id'] for r in r_tag_match.data]
        # Filtra a lista principal
        lista_questoes = [q for q in lista_questoes if q['id'] in ids_com_tag]

    st.markdown("---")
    
    # --- LISTAGEM E SELEÇÃO ---
    if lista_questoes:
        # Container de Ação em Massa
        col_msg, col_btn = st.columns([3, 1])
        col_msg.markdown(f"**{len(lista_questoes)}** questões encontradas. Selecione para criar um simulado.")
        
        # Botão para adicionar TUDO da lista atual
        if col_btn.button("Adicionar TODAS à Cesta"):
             ids_tela = [q['id'] for q in lista_questoes]
             # Adiciona sem duplicar
             novos = set(st.session_state.cesta_simulado) | set(ids_tela)
             st.session_state.cesta_simulado = list(novos)
             st.rerun()

        # Tabela Customizada
        for q in lista_questoes:
            # Layout: Checkbox | Texto
            c_check, c_txt = st.columns([0.5, 9])
            
            # Verifica se já está na cesta
            is_selected = q['id'] in st.session_state.cesta_simulado
            
            # Checkbox controla a cesta
            if c_check.checkbox("", value=is_selected, key=f"nav_{q['id']}"):
                if q['id'] not in st.session_state.cesta_simulado:
                    st.session_state.cesta_simulado.append(q['id'])
                    st.rerun()
            else:
                if q['id'] in st.session_state.cesta_simulado:
                    st.session_state.cesta_simulado.remove(q['id'])
                    st.rerun()
            
            # Texto com Tags Visuais
            # Busca tags dessa questão específica para exibir (opcional, pode pesar se muitos itens)
            # Para performance, vamos exibir tags apenas se o usuário pedir ou simplificar
            tags_q = get_user_tags(q['id'])
            html_tags = "".join([f"<span class='user-tag'>{t}</span>" for t in tags_q])
            
            c_txt.markdown(f"""
                <div style="background:white; padding:10px; border-radius:8px; border:1px solid #eee;">
                    <small style="color:#5E35B1; font-weight:bold;">{q['disciplina']} | {q.get('assunto','Geral')}</small><br>
                    {q['enunciado'][:120]}...<br>
                    {html_tags}
                </div>
            """, unsafe_allow_html=True)
            
    else:
        st.info("Nenhuma questão encontrada com esses filtros.")

# ==============================================================================
# PÁGINA: RESOLVER (SIMULADO)
# ==============================================================================
elif pagina == "📝 Resolver (Simulado)":
    
    col_main, col_tools = st.columns([3, 1])
    
    # --- BARRA LATERAL DIREITA (TAGS E INFO) ---
    with col_tools:
        st.markdown('<div class="questao-card" style="padding:15px;">', unsafe_allow_html=True)
        st.markdown("### 🏷️ Tags da Questão")
        
        # Só mostra se tiver questão carregada
        if st.session_state.questoes_carregadas:
            q_atual_id = st.session_state.questoes_carregadas[st.session_state.indice_questao]['id']
            
            # Carrega tags atuais
            tags_atuais = get_user_tags(q_atual_id)
            
            # Opções de tags (padrão + atuais)
            opcoes_tags = sorted(list(set(["Difícil", "Revisar", "Dúvida", "Favorita"] + tags_atuais)))
            
            # Widget Multiselect
            novas_tags = st.multiselect("Gerenciar Tags:", options=opcoes_tags, default=tags_atuais, key=f"tag_editor_{q_atual_id}")
            
            # Lógica de salvar/remover tags ao mudar
            # (Comparar novas_tags com tags_atuais e atualizar banco)
            if set(novas_tags) != set(tags_atuais):
                # Adicionar novas
                for t in novas_tags:
                    if t not in tags_atuais: add_remove_tag(q_atual_id, t, "add")
                # Remover antigas
                for t in tags_atuais:
                    if t not in novas_tags: add_remove_tag(q_atual_id, t, "remove")
                st.toast("Tags atualizadas!")
                time.sleep(0.5)
                st.rerun()
                
            # Adicionar Tag Personalizada (Nova)
            nova_tag_txt = st.text_input("Criar nova tag:", placeholder="Ex: Cirurgia Pediátrica")
            if st.button("Criar Tag"):
                if nova_tag_txt:
                    add_remove_tag(q_atual_id, nova_tag_txt, "add")
                    st.rerun()
                    
        else:
            st.caption("Carregue questões para gerenciar tags.")
        st.markdown('</div>', unsafe_allow_html=True)

        # Controle do Simulado
        st.markdown("### 🕹️ Controle")
        if st.session_state.cesta_simulado:
            st.info(f"Modo: Simulado Personalizado ({len(st.session_state.cesta_simulado)} questões)")
            if st.button("CARREGAR CESTA"):
                res = st.session_state.supabase.table("banco_questoes").select("*").in_("id", st.session_state.cesta_simulado).execute()
                st.session_state.questoes_carregadas = res.data
                st.session_state.indice_questao = 0
                st.session_state.resposta_mostrada = False
                st.rerun()
        else:
            st.info("Modo: Aleatório / Filtro Rápido")
            if st.button("Carregar 50 Aleatórias"):
                res = st.session_state.supabase.table("banco_questoes").select("*").limit(50).execute()
                st.session_state.questoes_carregadas = res.data
                st.session_state.indice_questao = 0
                st.session_state.resposta_mostrada = False
                st.rerun()

    # --- ÁREA DA QUESTÃO ---
    with col_main:
        if st.session_state.questoes_carregadas:
            qs = st.session_state.questoes_carregadas
            idx = st.session_state.indice_questao
            if idx >= len(qs): idx = 0
            q = qs[idx]
            
            # Lógica de Histórico
            ja_respondeu = False
            resp_ant = None
            try:
                h = st.session_state.supabase.table("historico_usuario").select("*").eq("user_email", st.session_state.user.user.email).eq("questao_id", q['id']).execute()
                if h.data: ja_respondeu = True; resp_ant = h.data[0]
            except: pass

            # Exibe Tags no Topo da Questão
            minhas_tags = get_user_tags(q['id'])
            tags_html = "".join([f"<span class='user-tag'>{t}</span>" for t in minhas_tags])

            st.markdown(f"""
            <div class="questao-card">
                <div style="color:#5E35B1; font-weight:bold; margin-bottom:5px;">
                    {q.get('disciplina')} <span style="color:#ccc">|</span> {q.get('assunto')}
                </div>
                <div>{tags_html}</div>
                <div class="enunciado-texto" style="margin-top:15px;">
                    {q['enunciado']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Alternativas
            alts = q.get('alternativas', {})
            chaves = ordenar_alternativas(alts)
            opts = [f"{k}) {alts[k]}" for k in chaves]
            
            sel_idx = None
            if ja_respondeu and resp_ant['alternativa_marcada']:
                for i, o in enumerate(opts):
                    if o.startswith(resp_ant['alternativa_marcada'] + ")"): sel_idx = i
            
            escolha = st.radio("Alternativas:", opts, index=sel_idx, disabled=ja_respondeu, label_visibility="collapsed")
            
            st.write("")
            c1, c2, c3 = st.columns([1, 2, 1])
            if c1.button("⬅️ Ant"):
                if idx > 0: st.session_state.indice_questao -= 1; st.session_state.resposta_mostrada = False; st.rerun()
            
            if not ja_respondeu:
                if c2.button("CONFIRMAR", use_container_width=True):
                    if escolha:
                        letra = escolha.split(")")[0]
                        gab = q.get('gabarito', '').strip().upper()
                        acertou = (letra.upper() == gab)
                        st.session_state.supabase.table("historico_usuario").insert({"user_email": st.session_state.user.user.email, "questao_id": q['id'], "alternativa_marcada": letra, "acertou": acertou}).execute()
                        st.session_state.resposta_mostrada = True; st.rerun()
            else:
                c2.info("Respondida")

            if c3.button("Prox ➡️"):
                if idx < len(qs)-1: st.session_state.indice_questao += 1; st.session_state.resposta_mostrada = False; st.rerun()
            
            # Gabarito
            if st.session_state.resposta_mostrada or ja_respondeu:
                gab = q.get('gabarito', '').strip().upper()
                letra_fin = escolha.split(")")[0] if escolha else (resp_ant['alternativa_marcada'] if ja_respondeu else "")
                cor = "#d4edda" if letra_fin.upper() == gab else "#f8d7da"
                st.markdown(f"<div style='background:{cor}; padding:15px; border-radius:8px; margin-top:10px;'>Gabarito: <b>{gab}</b></div>", unsafe_allow_html=True)
                
                ce = q.get('comentario_estruturado')
                if ce and isinstance(ce, dict):
                     with st.expander("Ver Comentários", expanded=True):
                        st.write(ce.get('fundamentacao_cientifica'))
                        st.success(ce.get('justificativa_alternativa_correta', {}).get('explicacao'))
                else:
                    st.info(q.get('comentario_integral'))
        else:
            st.warning("Cesta vazia ou sem questões carregadas. Use o Navegador ou os filtros à direita.")

# ==============================================================================
# PÁGINA: DESEMPENHO
# ==============================================================================
elif pagina == "📊 Meu Desempenho":
    st.header("Dashboard")
    res = st.session_state.supabase.table("historico_usuario").select("*").eq("user_email", st.session_state.user.user.email).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        acc = len(df[df['acertou']==True])
        st.metric("Acertos", f"{acc}/{len(df)}")
    else: st.info("Sem dados.")

# ==============================================================================
# PÁGINA: IMPORTAR (ADMIN)
# ==============================================================================
elif pagina == "📤 Importar (Admin)":
    if is_admin():
        st.header("Importar")
        f = st.file_uploader("JSON")
        if f and st.button("Enviar"):
             d = json.load(f)
             lote = []
             for i in d:
                 if 'id' in i and isinstance(i['id'], int): del i['id']
                 lote.append(i)
             st.session_state.supabase.table("banco_questoes").insert(lote).execute()
             st.success("Ok!")
    else: st.error("Acesso Negado")
