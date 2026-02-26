import streamlit as st
from supabase import create_client, Client
import json
import time
import math
import pandas as pd # Necessário para gráficos de desempenho

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedResidency Pro",
    page_icon="🏥",
    layout="wide"
)

# --- ESTADO DA SESSÃO ---
if 'supabase' not in st.session_state: st.session_state.supabase = None
if 'user' not in st.session_state: st.session_state.user = None
# Navegação
if 'indice_questao' not in st.session_state: st.session_state.indice_questao = 0
if 'questoes_carregadas' not in st.session_state: st.session_state.questoes_carregadas = []
if 'resposta_mostrada' not in st.session_state: st.session_state.resposta_mostrada = False
# Admin
if 'admin_pagina_atual' not in st.session_state: st.session_state.admin_pagina_atual = 1
if 'admin_editando_id' not in st.session_state: st.session_state.admin_editando_id = None

# --- FUNÇÕES ---
def init_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except:
        return None

def is_admin():
    """Verifica se o usuário logado é o admin definido nos secrets"""
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

# --- INICIALIZAÇÃO ---
if not st.session_state.supabase:
    st.session_state.supabase = init_supabase()

# ==============================================================================
# TELA DE LOGIN (BLOQUEIA O RESTO SE NÃO TIVER LOGADO)
# ==============================================================================
if not st.session_state.user:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏥 MedResidency Login")
        st.info("Faça login para salvar seu progresso.")
        
        tab_login, tab_cadastro = st.tabs(["Entrar", "Criar Conta"])
        
        with tab_login:
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                try:
                    res = st.session_state.supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user = res
                    st.success("Login realizado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao entrar: {e}")

        with tab_cadastro:
            new_email = st.text_input("Seu E-mail")
            new_senha = st.text_input("Sua Senha (mín 6 dígitos)", type="password")
            if st.button("Cadastrar"):
                try:
                    res = st.session_state.supabase.auth.sign_up({"email": new_email, "password": new_senha})
                    st.success("Conta criada! Verifique seu e-mail ou faça login.")
                except Exception as e:
                    st.error(f"Erro ao cadastrar: {e}")
    
    st.stop() # Para o código aqui se não estiver logado

# ==============================================================================
# ÁREA LOGADA
# ==============================================================================

# --- SIDEBAR COM PERFIL ---
with st.sidebar:
    st.title("🏥 MedResidency")
    usuario_email = st.session_state.user.user.email
    st.write(f"👤 **{usuario_email}**")
    
    if is_admin():
        st.markdown("🔒 **Modo Desenvolvedor**")
    else:
        st.markdown("🎓 **Modo Aluno**")
        
    if st.button("Sair"):
        st.session_state.supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    st.markdown("---")
    
    # DEFINIÇÃO DO MENU BASEADO NO CARGO
    opcoes_menu = ["📝 Resolver Questões", "📊 Meu Desempenho"]
    if is_admin():
        opcoes_menu.extend(["📤 Importar JSON", "⚙️ Gerenciar Questões"])
        
    pagina = st.radio("Menu", opcoes_menu)

# ==============================================================================
# PÁGINA 1: RESOLVER QUESTÕES (COM HISTÓRICO INDIVIDUAL)
# ==============================================================================
if pagina == "📝 Resolver Questões":
    st.header("Simulador de Prova")

    # Filtros
    col1, col2 = st.columns(2)
    if 'lista_disciplinas' not in st.session_state:
        try:
            res = st.session_state.supabase.table("banco_questoes").select("disciplina").execute()
            lista = sorted(list(set([x['disciplina'] for x in res.data if x['disciplina']])))
            lista.insert(0, "Todas")
            st.session_state.lista_disciplinas = lista
        except: st.session_state.lista_disciplinas = ["Todas"]

    filtro = col1.selectbox("Disciplina:", st.session_state.lista_disciplinas, on_change=lambda: st.session_state.update(indice_questao=0, resposta_mostrada=False))
    
    if st.button("Carregar Questões"):
        query = st.session_state.supabase.table("banco_questoes").select("*")
        if filtro != "Todas": query = query.eq("disciplina", filtro)
        res = query.limit(100).execute() # Carrega 100 por vez
        if res.data:
            st.session_state.questoes_carregadas = res.data
            st.session_state.indice_questao = 0
            st.session_state.resposta_mostrada = False
            st.rerun()
        else:
            st.warning("Nenhuma questão encontrada.")

    st.markdown("---")

    if st.session_state.questoes_carregadas:
        qs = st.session_state.questoes_carregadas
        idx = st.session_state.indice_questao
        if idx >= len(qs): idx = 0
        q = qs[idx]
        
        # --- VERIFICA SE O USUÁRIO JÁ RESPONDEU ESSA QUESTÃO ---
        ja_respondeu = False
        resp_anterior = None
        try:
            check_hist = st.session_state.supabase.table("historico_usuario")\
                .select("*")\
                .eq("user_email", usuario_email)\
                .eq("questao_id", q['id'])\
                .execute()
            if check_hist.data:
                ja_respondeu = True
                resp_anterior = check_hist.data[0]
        except: pass

        # --- NAVEGAÇÃO ---
        c1, c2, c3 = st.columns([1, 4, 1])
        if c1.button("⬅️ Anterior") and idx > 0:
            st.session_state.indice_questao -= 1
            st.session_state.resposta_mostrada = False
            st.rerun()
        
        status_txt = "✅ Respondida" if ja_respondeu else "⭕ Pendente"
        c2.markdown(f"<center><b>Questão {idx+1}/{len(qs)}</b><br><small>{status_txt}</small></center>", unsafe_allow_html=True)
        
        if c3.button("Próxima ➡️") and idx < len(qs)-1:
            st.session_state.indice_questao += 1
            st.session_state.resposta_mostrada = False
            st.rerun()

        # --- EXIBIÇÃO ---
        st.markdown(f"#### {q['enunciado']}")
        
        alts = q.get('alternativas', {})
        chaves = ordenar_alternativas(alts)
        opts = [f"{k}) {alts[k]}" for k in chaves]
        
        # Se já respondeu, trava a escolha ou mostra o que marcou
        index_prev = None
        if ja_respondeu and resp_anterior['alternativa_marcada']:
            # Tenta achar o index da resposta anterior
            for i, opt in enumerate(opts):
                if opt.startswith(resp_anterior['alternativa_marcada'] + ")"):
                    index_prev = i
                    break
        
        escolha = st.radio("Sua Resposta:", opts, index=index_prev, key=f"r_{q['id']}", disabled=ja_respondeu)
        
        # Botão de Confirmar (Só aparece se não respondeu ainda)
        if not ja_respondeu:
            if st.button("✅ Confirmar"):
                if escolha:
                    letra = escolha.split(")")[0]
                    gab = q.get('gabarito', '').strip().upper()
                    acertou = (letra.upper() == gab)
                    
                    # SALVA NO HISTÓRICO DO USUÁRIO
                    st.session_state.supabase.table("historico_usuario").insert({
                        "user_email": usuario_email,
                        "questao_id": q['id'],
                        "alternativa_marcada": letra,
                        "acertou": acertou
                    }).execute()
                    
                    st.session_state.resposta_mostrada = True
                    st.rerun() # Recarrega para bloquear a questão
        else:
            st.info(f"Você já respondeu esta questão em {resp_anterior['data_resposta'][:10]}.")
            st.session_state.resposta_mostrada = True

        # --- FEEDBACK ---
        if st.session_state.resposta_mostrada or ja_respondeu:
            # Pega gabarito
            gab = q.get('gabarito', '').strip().upper()
            
            # Se for resposta nova usa 'escolha', se for antiga usa 'resp_anterior'
            letra_final = escolha.split(")")[0] if escolha else (resp_anterior['alternativa_marcada'] if ja_respondeu else "")
            
            st.divider()
            if letra_final.upper() == gab:
                st.success(f"**CORRETO!** 🎉")
            else:
                st.error(f"**INCORRETO.** Você marcou {letra_final}, mas a correta é **{gab}**.")
            
            # COMENTÁRIO ESTRUTURADO
            ce = q.get('comentario_estruturado')
            if ce and isinstance(ce, dict):
                t1, t2, t3 = st.tabs(["💡 Explicação", "❌ Análise Erros", "📚 Resumo"])
                with t1:
                    st.write(ce.get('fundamentacao_cientifica'))
                    just = ce.get('justificativa_alternativa_correta', {})
                    st.info(f"**{just.get('letra')}**: {just.get('explicacao')}")
                with t2:
                    inc = ce.get('analise_das_alternativas_incorretas', {})
                    for k, v in inc.items(): st.write(f"**{k})** {v}")
                with t3:
                    st.warning(ce.get('raciocinio_clinico_resumido'))
            else:
                st.info(q.get('comentario_integral') or "Sem comentário.")

# ==============================================================================
# PÁGINA 2: MEU DESEMPENHO (DASHBOARD INDIVIDUAL)
# ==============================================================================
elif pagina == "📊 Meu Desempenho":
    st.header(f"Desempenho de {usuario_email}")
    
    # Busca dados do usuário
    res = st.session_state.supabase.table("historico_usuario").select("*").eq("user_email", usuario_email).execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        total = len(df)
        acertos = len(df[df['acertou'] == True])
        erros = total - acertos
        perc = (acertos / total) * 100
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Questões Feitas", total)
        c2.metric("Acertos", acertos)
        c3.metric("Aproveitamento", f"{perc:.1f}%")
        
        st.markdown("### Histórico Recente")
        st.dataframe(df[['questao_id', 'alternativa_marcada', 'acertou', 'data_resposta']].sort_values('data_resposta', ascending=False))
    else:
        st.info("Você ainda não resolveu nenhuma questão.")

# ==============================================================================
# ÁREA DO ADMIN (SÓ APARECE SE FOR ADMIN)
# ==============================================================================
elif pagina == "📤 Importar JSON":
    if not is_admin(): st.error("Acesso Negado"); st.stop()
    
    st.header("Importador (Admin)")
    arq = st.file_uploader("JSON", type="json")
    if arq and st.button("Importar"):
        try:
            dados = json.load(arq)
            if isinstance(dados, list):
                # Tratamento básico para garantir formato
                tratados = []
                for item in dados:
                    item['id_original'] = str(item.get('id', ''))
                    # Remove ID numérico se existir para deixar o banco gerar
                    if 'id' in item and isinstance(item['id'], int): del item['id'] 
                    tratados.append(item)
                    
                st.session_state.supabase.table("banco_questoes").insert(tratados).execute()
                st.success(f"{len(dados)} importados!")
        except Exception as e: st.error(f"Erro: {e}")

elif pagina == "⚙️ Gerenciar Questões":
    if not is_admin(): st.error("Acesso Negado"); st.stop()
    
    st.header("Gestão Geral (Admin)")
    # (Código de gestão igual ao anterior, simplificado aqui para brevidade)
    termo = st.text_input("Buscar ID ou Texto")
    if termo:
        q = st.session_state.supabase.table("banco_questoes").select("*")
        if termo.isdigit(): res = q.eq("id", termo).execute()
        else: res = q.ilike("enunciado", f"%{termo}%").execute()
        
        for item in res.data:
            c1, c2 = st.columns([8, 1])
            c1.write(f"[{item['id']}] {item['enunciado']}")
            if c2.button("Del", key=item['id']):
                st.session_state.supabase.table("banco_questoes").delete().eq("id", item['id']).execute()
                st.rerun()
