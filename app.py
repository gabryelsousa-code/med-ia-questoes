import streamlit as st
from supabase import create_client, Client
import json
import time
import math

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedResidency - Admin",
    page_icon="🏥",
    layout="wide"
)

# --- ESTADO DA SESSÃO ---
if 'supabase' not in st.session_state: st.session_state.supabase = None
# Aluno
if 'indice_questao' not in st.session_state: st.session_state.indice_questao = 0
if 'questoes_carregadas' not in st.session_state: st.session_state.questoes_carregadas = []
if 'resposta_mostrada' not in st.session_state: st.session_state.resposta_mostrada = False
# Admin
if 'admin_pagina_atual' not in st.session_state: st.session_state.admin_pagina_atual = 1
if 'admin_editando_id' not in st.session_state: st.session_state.admin_editando_id = None
if 'selecionados_para_exclusao' not in st.session_state: st.session_state.selecionados_para_exclusao = []

# --- FUNÇÕES ---
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except:
        return None

def resetar_navegacao_aluno():
    st.session_state.indice_questao = 0
    st.session_state.resposta_mostrada = False

def ordenar_alternativas(alternativas):
    chaves = list(alternativas.keys())
    chaves_upper = [k.upper() for k in chaves]
    if set(chaves_upper) == {'C', 'E'}:
        return sorted(chaves, key=lambda x: 0 if x.upper() == 'C' else 1)
    if set(chaves_upper) == {'V', 'F'}:
         return sorted(chaves, key=lambda x: 0 if x.upper() == 'V' else 1)
    return sorted(chaves)

# --- CONEXÃO AUTOMÁTICA ---
if not st.session_state.supabase:
    st.session_state.supabase = init_supabase()

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🏥 MedResidency")
    
    if st.session_state.supabase:
        st.success("✅ Banco Conectado")
    else:
        st.error("❌ Banco Desconectado")
        st.warning("Configure 'st.secrets'.")

    st.markdown("---")
    pagina = st.radio("Menu", ["📝 Resolver Questões", "📤 Importar JSON", "⚙️ Gerenciar Questões"])

# ==============================================================================
# PÁGINA 1: IMPORTADOR
# ==============================================================================
if pagina == "📤 Importar JSON":
    st.header("Importador de Questões")
    arquivo_upload = st.file_uploader("Arquivo .json", type="json")
    
    if arquivo_upload and st.session_state.supabase:
        if st.button("💾 Salvar no Banco"):
            try:
                dados = json.load(arquivo_upload)
                if isinstance(dados, list):
                    progresso = st.progress(0)
                    st.session_state.supabase.table("banco_questoes").insert(dados).execute()
                    progresso.progress(100)
                    st.success(f"Sucesso! {len(dados)} questões importadas.")
                else:
                    st.error("JSON deve ser uma lista [ ].")
            except Exception as e:
                st.error(f"Erro: {e}")

# ==============================================================================
# PÁGINA 2: SIMULADOR (ALUNO)
# ==============================================================================
elif pagina == "📝 Resolver Questões":
    st.header("Simulador de Prova")
    
    if not st.session_state.supabase:
        st.warning("Banco desconectado."); st.stop()

    col1, col2 = st.columns(2)
    if 'lista_disciplinas' not in st.session_state:
        try:
            res = st.session_state.supabase.table("banco_questoes").select("disciplina").execute()
            lista = sorted(list(set([x['disciplina'] for x in res.data if x['disciplina']])))
            lista.insert(0, "Todas")
            st.session_state.lista_disciplinas = lista
        except:
            st.session_state.lista_disciplinas = ["Todas"]

    filtro = col1.selectbox("Disciplina:", st.session_state.lista_disciplinas, on_change=resetar_navegacao_aluno)
    
    if st.button("Carregar Questões"):
        try:
            query = st.session_state.supabase.table("banco_questoes").select("*")
            if filtro != "Todas": query = query.eq("disciplina", filtro)
            res = query.limit(1000).execute()
            
            if res.data:
                st.session_state.questoes_carregadas = res.data
                resetar_navegacao_aluno()
                st.rerun()
            else:
                st.warning("Nenhuma questão encontrada.")
        except Exception as e:
            st.error(f"Erro: {e}")

    st.markdown("---")

    if st.session_state.questoes_carregadas:
        qs = st.session_state.questoes_carregadas
        idx = st.session_state.indice_questao
        if idx >= len(qs): idx = 0
        q = qs[idx]
        
        c1, c2, c3 = st.columns([1, 4, 1])
        if c1.button("⬅️") and idx > 0:
            st.session_state.indice_questao -= 1
            st.session_state.resposta_mostrada = False
            st.rerun()
        c2.markdown(f"<center><b>{idx+1}/{len(qs)}</b><br><small>{q.get('disciplina')} | {q.get('assunto')}</small></center>", unsafe_allow_html=True)
        if c3.button("➡️") and idx < len(qs)-1:
            st.session_state.indice_questao += 1
            st.session_state.resposta_mostrada = False
            st.rerun()

        st.markdown(f"#### {q['enunciado']}")
        alts = q.get('alternativas', {})
        chaves = ordenar_alternativas(alts)
        opts = [f"{k}) {alts[k]}" for k in chaves]
        escolha = st.radio("Resposta:", opts, index=None, key=f"r_{q['id']}")
        
        if st.button("✅ Confirmar"):
            if escolha: st.session_state.resposta_mostrada = True
            
        if st.session_state.resposta_mostrada and escolha:
            letra = escolha.split(")")[0]
            gab = q.get('gabarito', '').strip().upper()
            st.divider()
            if letra.upper() == gab: st.success("CORRETO! 🎉")
            else: st.error(f"ERRADO. Gabarito: **{gab}**")
            st.info(f"💡 {q.get('comentario', 'Sem comentário.')}")
    elif st.session_state.get('questoes_carregadas') == []:
        st.info("Clique em Carregar Questões.")

# ==============================================================================
# PÁGINA 3: GERENCIADOR (CMS)
# ==============================================================================
elif pagina == "⚙️ Gerenciar Questões":
    st.header("Gestão do Banco de Questões")
    
    if not st.session_state.supabase:
        st.error("Banco desconectado."); st.stop()

    # --- MODO DE EDIÇÃO INDIVIDUAL ---
    if st.session_state.admin_editando_id:
        res_edit = st.session_state.supabase.table("banco_questoes").select("*").eq("id", st.session_state.admin_editando_id).execute()
        
        if res_edit.data:
            q_edit = res_edit.data[0]
            st.info(f"Editando Questão ID: {q_edit['id']}")
            
            with st.form("form_edicao"):
                col_a, col_b = st.columns(2)
                novo_disc = col_a.text_input("Disciplina", q_edit.get('disciplina'))
                novo_assunto = col_b.text_input("Assunto", q_edit.get('assunto'))
                
                novo_enunciado = st.text_area("Enunciado", q_edit.get('enunciado'), height=150)
                
                st.markdown("**Alternativas (JSON):**")
                alt_str = json.dumps(q_edit.get('alternativas', {}), indent=2, ensure_ascii=False)
                novo_alt_str = st.text_area("JSON Alternativas", alt_str, height=200)
                
                col_c, col_d = st.columns(2)
                novo_gabarito = col_c.text_input("Gabarito", q_edit.get('gabarito'))
                novo_comentario = st.text_area("Comentário", q_edit.get('comentario'), height=100)
                
                c1, c2, c3 = st.columns([2, 1, 2])
                
                # Botão Salvar
                if c1.form_submit_button("💾 Salvar Alterações"):
                    try:
                        novas_alts = json.loads(novo_alt_str)
                        update_data = {
                            "disciplina": novo_disc, "assunto": novo_assunto,
                            "enunciado": novo_enunciado, "alternativas": novas_alts,
                            "gabarito": novo_gabarito, "comentario": novo_comentario
                        }
                        st.session_state.supabase.table("banco_questoes").update(update_data).eq("id", q_edit['id']).execute()
                        st.success("Salvo!"); time.sleep(0.5)
                        st.session_state.admin_editando_id = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro JSON: {e}")
                
                # Botão Cancelar
                if c2.form_submit_button("❌ Cancelar"):
                    st.session_state.admin_editando_id = None
                    st.rerun()
                
                # Botão Excluir (Dentro da Edição)
                if c3.form_submit_button("🗑️ EXCLUIR ESTA QUESTÃO", type="primary"):
                    try:
                        st.session_state.supabase.table("banco_questoes").delete().eq("id", q_edit['id']).execute()
                        st.toast(f"Questão {q_edit['id']} deletada!")
                        st.session_state.admin_editando_id = None
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")

    # --- MODO LISTAGEM E EXCLUSÃO EM MASSA ---
    else:
        # Filtros e Paginação
        col_filtro1, col_filtro2 = st.columns([3, 1])
        ordem = col_filtro1.selectbox("Ordenar por:", ["Mais Recentes", "Mais Antigas", "Ordem Alfabética"])
        
        ITENS_POR_PAGINA = 50
        try:
            count_res = st.session_state.supabase.table("banco_questoes").select("id", count='exact').execute()
            total_paginas = math.ceil(count_res.count / ITENS_POR_PAGINA)
        except: total_paginas = 1

        # Barra de Navegação
        col_nav1, col_nav2, col_nav3 = st.columns([1, 3, 1])
        if col_nav1.button("⬅️ Anterior") and st.session_state.admin_pagina_atual > 1:
            st.session_state.admin_pagina_atual -= 1; st.rerun()
            
        col_nav2.markdown(f"<center>Pág. <b>{st.session_state.admin_pagina_atual}</b> de {total_paginas}</center>", unsafe_allow_html=True)
        
        if col_nav3.button("Próxima ➡️") and st.session_state.admin_pagina_atual < total_paginas:
            st.session_state.admin_pagina_atual += 1; st.rerun()

        st.markdown("---")

        # Busca Dados
        offset_start = (st.session_state.admin_pagina_atual - 1) * ITENS_POR_PAGINA
        query = st.session_state.supabase.table("banco_questoes").select("*")
        
        if "Mais Recentes" in ordem: query = query.order("id", desc=True)
        elif "Mais Antigas" in ordem: query = query.order("id", desc=False)
        elif "Alfabética" in ordem: query = query.order("enunciado", desc=False)
            
        lista_questoes = query.range(offset_start, offset_start + ITENS_POR_PAGINA - 1).execute().data

        # --- CONTROLE DE SELEÇÃO EM MASSA ---
        
        # Checkbox Mestre (Selecionar Tudo da Página)
        selecionar_tudo = st.checkbox(f"Selecionar todas as {len(lista_questoes)} questões desta página")
        
        # Lista temporária para guardar IDs selecionados nesta interação
        ids_selecionados = []

        if lista_questoes:
            with st.container():
                for q in lista_questoes:
                    c_check, c_texto, c_edit = st.columns([0.5, 8, 1])
                    
                    # Checkbox Individual
                    # Se 'selecionar_tudo' for True, o valor padrão é True
                    is_checked = c_check.checkbox("", value=selecionar_tudo, key=f"sel_{q['id']}")
                    
                    if is_checked:
                        ids_selecionados.append(q['id'])
                    
                    # Texto da Questão
                    texto_resumo = f"**[{q.get('id')}]** {q.get('disciplina')} - {q.get('enunciado')[:90]}..."
                    c_texto.markdown(texto_resumo)
                    
                    # Botão Editar
                    if c_edit.button("✏️", key=f"edit_{q['id']}"):
                        st.session_state.admin_editando_id = q['id']
                        st.rerun()
                    
                    st.divider()
            
            # --- BOTÃO FLUTUANTE DE AÇÃO EM MASSA ---
            if ids_selecionados:
                st.markdown("### ⚠️ Ações em Massa")
                st.write(f"Você selecionou **{len(ids_selecionados)}** questões.")
                
                if st.button("🗑️ EXCLUIR ITENS SELECIONADOS", type="primary"):
                    with st.spinner("Excluindo..."):
                        try:
                            # Deleta usando o operador 'in' (lista de IDs)
                            st.session_state.supabase.table("banco_questoes").delete().in_("id", ids_selecionados).execute()
                            st.success("Itens excluídos com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir em massa: {e}")
        else:
            st.info("Nenhuma questão nesta página.")
