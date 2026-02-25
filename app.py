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
if 'ids_pagina_atual' not in st.session_state: st.session_state.ids_pagina_atual = []

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

# --- CALLBACK PARA SELECIONAR TUDO ---
def callback_selecionar_tudo():
    # Pega o valor atual do checkbox Mestre
    estado_mestre = st.session_state.chk_master
    # Força esse valor em todos os IDs da página atual
    if 'ids_pagina_atual' in st.session_state:
        for q_id in st.session_state.ids_pagina_atual:
            st.session_state[f"sel_{q_id}"] = estado_mestre

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
# PÁGINA 3: GERENCIADOR (CMS COMPLETO)
# ==============================================================================
elif pagina == "⚙️ Gerenciar Questões":
    st.header("Gestão do Banco de Questões")
    
    if not st.session_state.supabase:
        st.error("Banco desconectado."); st.stop()

    # --- MODO EDIÇÃO ---
    if st.session_state.admin_editando_id:
        res_edit = st.session_state.supabase.table("banco_questoes").select("*").eq("id", st.session_state.admin_editando_id).execute()
        if res_edit.data:
            q_edit = res_edit.data[0]
            st.info(f"Editando Questão ID: {q_edit['id']}")
            
            with st.form("form_edicao"):
                c_disc, c_ass = st.columns(2)
                novo_disc = c_disc.text_input("Disciplina", q_edit.get('disciplina'))
                novo_ass = c_ass.text_input("Assunto", q_edit.get('assunto'))
                novo_enun = st.text_area("Enunciado", q_edit.get('enunciado'), height=150)
                alt_str = json.dumps(q_edit.get('alternativas', {}), indent=2, ensure_ascii=False)
                novo_alt_str = st.text_area("JSON Alternativas", alt_str, height=200)
                
                c_gab, c_com = st.columns(2)
                novo_gab = c_gab.text_input("Gabarito", q_edit.get('gabarito'))
                novo_com = c_com.text_input("Comentário", q_edit.get('comentario'))
                
                col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
                if col_btn1.form_submit_button("💾 Salvar"):
                    try:
                        novas_alts = json.loads(novo_alt_str)
                        upd = {"disciplina": novo_disc, "assunto": novo_ass, "enunciado": novo_enun, "alternativas": novas_alts, "gabarito": novo_gab, "comentario": novo_com}
                        st.session_state.supabase.table("banco_questoes").update(upd).eq("id", q_edit['id']).execute()
                        st.success("Salvo!"); st.session_state.admin_editando_id = None; time.sleep(0.5); st.rerun()
                    except: st.error("Erro JSON")
                
                if col_btn2.form_submit_button("❌ Cancelar"):
                    st.session_state.admin_editando_id = None; st.rerun()

                if col_btn3.form_submit_button("🗑️ DELETAR", type="primary"):
                    st.session_state.supabase.table("banco_questoes").delete().eq("id", q_edit['id']).execute()
                    st.session_state.admin_editando_id = None; st.rerun()

    # --- MODO LISTAGEM ---
    else:
        # Filtros e Paginação
        c_ordem, c_nav = st.columns([1, 2])
        ordem = c_ordem.selectbox("Ordem:", ["Recentes", "Antigas", "Alfabética"])
        
        ITENS_PAG = 50
        try:
            cnt = st.session_state.supabase.table("banco_questoes").select("id", count='exact').execute()
            tot_pag = math.ceil(cnt.count / ITENS_PAG)
        except: tot_pag = 1

        with c_nav:
            cn1, cn2, cn3 = st.columns([1,2,1])
            if cn1.button("⬅️") and st.session_state.admin_pagina_atual > 1:
                st.session_state.admin_pagina_atual -= 1; st.rerun()
            cn2.write(f"<center>{st.session_state.admin_pagina_atual} / {tot_pag}</center>", unsafe_allow_html=True)
            if cn3.button("➡️") and st.session_state.admin_pagina_atual < tot_pag:
                st.session_state.admin_pagina_atual += 1; st.rerun()

        st.markdown("---")

        # Busca Dados
        off = (st.session_state.admin_pagina_atual - 1) * ITENS_PAG
        qry = st.session_state.supabase.table("banco_questoes").select("*")
        if "Recentes" in ordem: qry = qry.order("id", desc=True)
        elif "Antigas" in ordem: qry = qry.order("id", desc=False)
        else: qry = qry.order("enunciado", desc=False)
        
        lista = qry.range(off, off + ITENS_PAG - 1).execute().data
        
        # Salva IDs da página atual para o callback funcionar
        st.session_state.ids_pagina_atual = [q['id'] for q in lista] if lista else []

        # CONTAINER PARA AÇÕES EM MASSA (NO TOPO)
        container_topo = st.container()

        # Checkbox Mestre (Com Callback para funcionar de verdade)
        st.checkbox("Selecionar Todos desta Página", key="chk_master", on_change=callback_selecionar_tudo)
        
        st.divider()

        # Lista
        ids_selecionados = []
        if lista:
            for q in lista:
                # Layout Ajustado: Checkbox | Texto | Editar | Excluir
                c_chk, c_txt, c_edt, c_del = st.columns([0.5, 10, 0.7, 0.7])
                
                # Checkbox Individual
                if c_chk.checkbox("", key=f"sel_{q['id']}"):
                    ids_selecionados.append(q['id'])
                
                c_txt.markdown(f"**[{q['id']}]** {q.get('disciplina')} - {q.get('enunciado')[:90]}...")
                
                if c_edt.button("✏️", key=f"ed_{q['id']}", help="Editar"):
                    st.session_state.admin_editando_id = q['id']; st.rerun()
                
                if c_del.button("🗑️", key=f"dl_{q['id']}", help="Excluir"):
                    st.session_state.supabase.table("banco_questoes").delete().eq("id", q['id']).execute()
                    st.toast("Deletado!"); time.sleep(0.5); st.rerun()
                
                st.divider()
        else:
            st.info("Vazio.")

        # ATUALIZA O CONTAINER DO TOPO SE HOUVER SELEÇÃO
        if ids_selecionados:
            with container_topo:
                st.error(f"⚠️ **{len(ids_selecionados)} ITENS MARCADOS PARA EXCLUSÃO**")
                if st.button("🗑️ EXCLUIR SELECIONADOS AGORA", type="primary"):
                    st.session_state.supabase.table("banco_questoes").delete().in_("id", ids_selecionados).execute()
                    st.success("Excluídos!"); time.sleep(1); st.rerun()
