import streamlit as st
from supabase import create_client, Client
import json
import time
import pandas as pd

# --- CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha) ---
st.set_page_config(
    page_title="Estratégia MedClone",
    page_icon="🦉",
    layout="wide"
)

# ==============================================================================
# 🎨 ESTILIZAÇÃO VISUAL (CSS AVANÇADO)
# ==============================================================================
st.markdown("""
<style>
    /* 1. Fundo Geral e Fontes */
    .stApp {
        background-color: #fdfdfd;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 2. Barra Superior (Header) Limpa */
    header[data-testid="stHeader"] {
        background-color: #fdfdfd;
        border-bottom: 1px solid #eee;
    }

    /* 3. Card da Questão (Caixa Branca com Sombra) */
    .questao-card {
        background-color: white;
        padding: 30px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        margin-bottom: 25px;
    }

    /* 4. Títulos e Enunciados */
    .titulo-roxo {
        color: #5E35B1;
        font-weight: 800;
        font-size: 1.8rem;
        margin-bottom: 10px;
    }
    .enunciado-texto {
        font-size: 1.15rem;
        color: #2c3e50;
        line-height: 1.6;
        font-weight: 500;
        margin-bottom: 20px;
    }

    /* 5. Tags de Disciplina/Assunto */
    .tag-disciplina {
        background-color: #ede7f6; 
        color: #5E35B1;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 5px;
        text-transform: uppercase;
    }
    .tag-assunto {
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }

    /* 6. Botões Personalizados (Estilo "Estratégia") */
    .stButton > button {
        background-color: #5E35B1;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.2s ease;
        width: 100%; /* Botões ocupam largura total na coluna */
    }
    .stButton > button:hover {
        background-color: #4527a0;
        box-shadow: 0 4px 8px rgba(94, 53, 177, 0.2);
    }
    
    /* Botão Secundário (Outline) */
    .btn-outline {
        background-color: transparent !important;
        border: 1px solid #5E35B1 !important;
        color: #5E35B1 !important;
    }

    /* 7. Radio Buttons (Alternativas) */
    .stRadio > div[role="radiogroup"] {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #eee;
    }
    
    /* 8. Card de Filtros (Direita) */
    .filtro-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #eee;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    
</style>
""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO ESTADO ---
if 'supabase' not in st.session_state: st.session_state.supabase = None
if 'user' not in st.session_state: st.session_state.user = None
if 'indice_questao' not in st.session_state: st.session_state.indice_questao = 0
if 'questoes_carregadas' not in st.session_state: st.session_state.questoes_carregadas = []
if 'resposta_mostrada' not in st.session_state: st.session_state.resposta_mostrada = False

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

if not st.session_state.supabase:
    st.session_state.supabase = init_supabase()

# ==============================================================================
# TELA DE LOGIN (CLEAN)
# ==============================================================================
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><br><h1 style='text-align: center; color: #5E35B1;'>🦉 MedResidency</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Faça login para acessar o banco de questões.</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
            with tab1:
                email = st.text_input("E-mail", key="login_email")
                senha = st.text_input("Senha", type="password", key="login_pass")
                if st.button("Acessar Plataforma", use_container_width=True):
                    try:
                        res = st.session_state.supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state.user = res
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
            with tab2:
                new_email = st.text_input("E-mail", key="cad_email")
                new_senha = st.text_input("Senha", type="password", key="cad_pass")
                if st.button("Cadastrar Grátis", use_container_width=True):
                    try:
                        st.session_state.supabase.auth.sign_up({"email": new_email, "password": new_senha})
                        st.success("Conta criada! Faça login.")
                    except Exception as e:
                        st.error(f"Erro: {e}")
    st.stop()

# ==============================================================================
# HEADER SUPERIOR (MENU)
# ==============================================================================
# Usamos colunas no topo para simular um menu horizontal simples
col_logo, col_menu, col_user = st.columns([2, 6, 2])

with col_logo:
    st.markdown("<h3 style='margin:0; padding-top:10px; color:#5E35B1;'>🦉 MedResidency</h3>", unsafe_allow_html=True)

with col_menu:
    # Menu horizontal simples usando radio ou botões seria complexo, 
    # mantemos o menu na Sidebar para funcionalidade, mas aqui mostramos o título da seção atual
    pass 

with col_user:
    st.markdown(f"<div style='text-align:right; padding-top:15px; font-size:0.9rem;'>👤 {st.session_state.user.user.email}</div>", unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# SIDEBAR (NAVEGAÇÃO)
# ==============================================================================
with st.sidebar:
    st.markdown("### Navegação")
    opcoes = ["📝 Resolver Questões", "📊 Meu Desempenho"]
    if is_admin(): opcoes += ["📤 Importar JSON", "⚙️ Gerenciar"]
    
    pagina = st.radio("", opcoes)
    
    st.markdown("---")
    if st.button("Sair da Conta"):
        st.session_state.supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

# ==============================================================================
# PÁGINA: RESOLVER QUESTÕES (LAYOUT ESTILO "ESTRATÉGIA")
# ==============================================================================
if pagina == "📝 Resolver Questões":
    
    # --- LAYOUT DE 2 COLUNAS (Esquerda: Questões, Direita: Filtros) ---
    col_main, col_filters = st.columns([3, 1])

    # --- COLUNA DA DIREITA (FILTROS) ---
    with col_filters:
        st.markdown('<div class="filtro-card">', unsafe_allow_html=True)
        st.markdown("### 🔍 Filtros")
        
        # Carrega disciplinas
        if 'lista_disciplinas' not in st.session_state:
            try:
                r = st.session_state.supabase.table("banco_questoes").select("disciplina").execute()
                d = sorted(list(set([x['disciplina'] for x in r.data if x['disciplina']])))
                st.session_state.lista_disciplinas = ["Todas"] + d
            except: st.session_state.lista_disciplinas = ["Todas"]
            
        filtro_disc = st.selectbox("Matéria/Assunto", st.session_state.lista_disciplinas)
        
        st.markdown("---")
        
        # Botão de Busca destacado
        if st.button("BUSCAR QUESTÕES", use_container_width=True):
            q = st.session_state.supabase.table("banco_questoes").select("*")
            if filtro_disc != "Todas": q = q.eq("disciplina", filtro_disc)
            res = q.limit(100).execute()
            
            if res.data:
                st.session_state.questoes_carregadas = res.data
                st.session_state.indice_questao = 0
                st.session_state.resposta_mostrada = False
                st.rerun()
            else:
                st.warning("Nada encontrado.")
                
        # Status
        if st.session_state.questoes_carregadas:
            st.markdown(f"<br><div style='text-align:center; color:#666;'>Encontradas: <b>{len(st.session_state.questoes_carregadas)}</b> questões</div>", unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

    # --- COLUNA DA ESQUERDA (QUESTÃO PRINCIPAL) ---
    with col_main:
        if st.session_state.questoes_carregadas:
            qs = st.session_state.questoes_carregadas
            idx = st.session_state.indice_questao
            if idx >= len(qs): idx = 0
            q = qs[idx]
            
            # Checa histórico
            ja_respondeu = False
            resp_ant = None
            try:
                h = st.session_state.supabase.table("historico_usuario").select("*").eq("user_email", st.session_state.user.user.email).eq("questao_id", q['id']).execute()
                if h.data: ja_respondeu = True; resp_ant = h.data[0]
            except: pass

            # --- CARD DA QUESTÃO (Início) ---
            st.markdown(f"""
            <div class="questao-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                    <div>
                        <span class="tag-disciplina">{q.get('disciplina')}</span>
                        <span class="tag-assunto">{q.get('assunto')}</span>
                    </div>
                    <div style="color:#999; font-size:0.9rem;">
                        ID: {q.get('id_original') or q.get('id')} • Questão {idx+1}/{len(qs)}
                    </div>
                </div>
                <div class="enunciado-texto">
                    {q['enunciado']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- ALTERNATIVAS ---
            alts = q.get('alternativas', {})
            chaves = ordenar_alternativas(alts)
            opts = [f"{k}) {alts[k]}" for k in chaves]
            
            # Recupera resposta anterior se houver
            idx_sel = None
            if ja_respondeu and resp_ant['alternativa_marcada']:
                for i, o in enumerate(opts):
                    if o.startswith(resp_ant['alternativa_marcada'] + ")"): idx_sel = i; break
            
            escolha = st.radio("Selecione uma alternativa:", opts, index=idx_sel, disabled=ja_respondeu, label_visibility="collapsed")
            
            st.write("") # Espaço

            # --- BARRA DE AÇÕES (Botões) ---
            c_prev, c_conf, c_next = st.columns([1, 2, 1])
            
            if c_prev.button("⬅️ Anterior"):
                if idx > 0:
                    st.session_state.indice_questao -= 1
                    st.session_state.resposta_mostrada = False
                    st.rerun()

            if not ja_respondeu:
                if c_conf.button("RESPONDER", use_container_width=True):
                    if escolha:
                        letra = escolha.split(")")[0]
                        gab = q.get('gabarito', '').strip().upper()
                        acertou = (letra.upper() == gab)
                        
                        st.session_state.supabase.table("historico_usuario").insert({
                            "user_email": st.session_state.user.user.email,
                            "questao_id": q['id'],
                            "alternativa_marcada": letra, "acertou": acertou
                        }).execute()
                        st.session_state.resposta_mostrada = True
                        st.rerun()
            else:
                c_conf.info(f"Você já respondeu em {resp_ant['data_resposta'][:10]}")

            if c_next.button("Próxima ➡️"):
                if idx < len(qs)-1:
                    st.session_state.indice_questao += 1
                    st.session_state.resposta_mostrada = False
                    st.rerun()

            # --- GABARITO E COMENTÁRIOS ---
            if st.session_state.resposta_mostrada or ja_respondeu:
                gab = q.get('gabarito', '').strip().upper()
                letra_final = escolha.split(")")[0] if escolha else (resp_ant['alternativa_marcada'] if ja_respondeu else "")
                
                # Card de Feedback
                cor_fundo = "#d4edda" if letra_final.upper() == gab else "#f8d7da"
                texto_feed = "Parabéns! Você acertou! 🎉" if letra_final.upper() == gab else f"Que pena! Você errou. O gabarito é **{gab}**."
                
                st.markdown(f"""
                <div style="background-color: {cor_fundo}; padding: 15px; border-radius: 8px; margin-top: 20px; color: #333; font-weight: bold;">
                    {texto_feed}
                </div>
                """, unsafe_allow_html=True)
                
                # Comentários em Abas
                st.markdown("### 👨‍🏫 Comentários do Professor")
                ce = q.get('comentario_estruturado')
                
                if ce and isinstance(ce, dict):
                    t1, t2, t3 = st.tabs(["💡 Explicação", "❌ Por que errei?", "📚 Resumo"])
                    with t1:
                        st.write(ce.get('fundamentacao_cientifica'))
                        just = ce.get('justificativa_alternativa_correta', {})
                        st.success(f"**Alternativa {just.get('letra')}**: {just.get('explicacao')}")
                    with t2:
                        inc = ce.get('analise_das_alternativas_incorretas', {})
                        for k, v in inc.items(): st.markdown(f"**{k})** {v}")
                    with t3:
                        st.info(ce.get('raciocinio_clinico_resumido'))
                else:
                    st.info(q.get('comentario_integral') or "Sem comentário disponível.")
                    
        else:
            st.info("👈 Use o filtro à direita para buscar questões.")

# ==============================================================================
# PÁGINA: IMPORTAR (ADMIN)
# ==============================================================================
elif pagina == "📤 Importar JSON":
    if not is_admin(): st.error("Acesso restrito."); st.stop()
    st.header("Importador de Questões")
    
    with st.container(border=True):
        arq = st.file_uploader("Arraste o arquivo JSON aqui", type="json")
        if arq and st.button("Iniciar Importação", use_container_width=True):
            try:
                dados = json.load(arq)
                # ... (Lógica de tratamento igual ao anterior)
                lote = []
                for item in dados:
                    item['id_original'] = str(item.get('id', ''))
                    if 'id' in item and isinstance(item['id'], int): del item['id']
                    lote.append(item)
                st.session_state.supabase.table("banco_questoes").insert(lote).execute()
                st.success(f"{len(lote)} questões importadas com sucesso!")
            except Exception as e:
                st.error(f"Erro: {e}")

# ==============================================================================
# PÁGINA: MEU DESEMPENHO
# ==============================================================================
elif pagina == "📊 Meu Desempenho":
    st.header("Meu Desempenho")
    
    res = st.session_state.supabase.table("historico_usuario").select("*").eq("user_email", st.session_state.user.user.email).execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        total = len(df)
        acertos = len(df[df['acertou'] == True])
        perc = (acertos/total)*100
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Questões", total)
        c2.metric("Acertos", acertos)
        c3.metric("Aproveitamento", f"{perc:.1f}%")
        
        st.markdown("### Histórico")
        st.dataframe(df[['questao_id', 'alternativa_marcada', 'acertou', 'data_resposta']], use_container_width=True)
    else:
        st.info("Comece a resolver questões para ver suas estatísticas aqui.")
