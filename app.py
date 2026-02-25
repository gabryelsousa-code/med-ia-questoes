import streamlit as st
from supabase import create_client, Client
import json
import time
import math

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedResidency - Pro",
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
    if not alternativas: return []
    chaves = list(alternativas.keys())
    chaves_upper = [k.upper() for k in chaves]
    if set(chaves_upper) == {'C', 'E'}:
        return sorted(chaves, key=lambda x: 0 if x.upper() == 'C' else 1)
    if set(chaves_upper) == {'V', 'F'}:
         return sorted(chaves, key=lambda x: 0 if x.upper() == 'V' else 1)
    return sorted(chaves)

def callback_selecionar_tudo():
    estado_mestre = st.session_state.chk_master
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
    st.header("Importador de Questões (Formato Pro)")
    st.caption("Suporta JSON com comentário estruturado, fundamentação científica e metadados.")
    
    arquivo_upload = st.file_uploader("Arquivo .json", type="json")
    
    if arquivo_upload and st.session_state.supabase:
        if st.button("💾 Salvar no Banco"):
            try:
                dados_brutos = json.load(arquivo_upload)
                
                # Adaptação para garantir compatibilidade com o banco
                dados_tratados = []
                if isinstance(dados_brutos, list):
                    for item in dados_brutos:
                        # Mapeia campos do JSON para as colunas do banco
                        novo_item = {
                            "id_original": str(item.get("id", "")), # Guarda o ID original do JSON
                            "disciplina": item.get("disciplina"),
                            "assunto": item.get("assunto"),
                            "tipo": item.get("tipo"),
                            "enunciado": item.get("enunciado"),
                            "alternativas": item.get("alternativas"),
                            "gabarito": item.get("gabarito"),
                            "gabarito_metodo": item.get("gabarito_metodo"),
                            "gabarito_confianca": item.get("gabarito_confianca"),
                            "comentario_estruturado": item.get("comentario_estruturado"),
                            "comentario_integral": item.get("comentario_integral")
                        }
                        dados_tratados.append(novo_item)

                    progresso = st.progress(0)
                    st.session_state.supabase.table("banco_questoes").insert(dados_tratados).execute()
                    progresso.progress(100)
                    st.success(f"Sucesso! {len(dados_tratados)} questões importadas.")
                else:
                    st.error("JSON deve ser uma lista [ ].")
            except Exception as e:
                st.error(f"Erro na importação: {e}")

# ==============================================================================
# PÁGINA 2: SIMULADOR (VISUALIZAÇÃO RICA)
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
        
        # Header da Questão
        id_display = q.get('id_original') if q.get('id_original') else q.get('id')
        c2.markdown(f"<center><b>Questão {idx+1}/{len(qs)}</b> (ID: {id_display})<br><small>{q.get('disciplina')} | {q.get('assunto')}</small></center>", unsafe_allow_html=True)
        
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
            
        # --- LÓGICA DE GABARITO E COMENTÁRIO RICO ---
        if st.session_state.resposta_mostrada and escolha:
            letra_user = escolha.split(")")[0]
            gab = q.get('gabarito', '').strip().upper()
            
            st.divider()
            if letra_user.upper() == gab: st.success("CORRETO! 🎉")
            else: st.error(f"ERRADO. Gabarito: **{gab}**")
            
            # EXIBIÇÃO ESTRUTURADA DO COMENTÁRIO
            ce = q.get('comentario_estruturado')
            
            if ce and isinstance(ce, dict):
                # Se tiver a estrutura nova, mostra bonitinho
                tab1, tab2, tab3 = st.tabs(["💡 Explicação & Fundamentação", "❌ Análise das Incorretas", "📚 Resumo Clínico"])
                
                with tab1:
                    st.markdown("### Por que essa é a correta?")
                    just = ce.get('justificativa_alternativa_correta', {})
                    st.info(f"**Alternativa {just.get('letra')}**: {just.get('explicacao')}")
                    
                    st.markdown("---")
                    st.markdown("### Fundamentação Científica")
                    st.write(ce.get('fundamentacao_cientifica'))
                    
                    if just.get('base_cientifica'):
                        st.caption(f"📚 Fontes: {', '.join(just.get('base_cientifica', []))}")

                with tab2:
                    st.markdown("### Por que as outras estão erradas?")
                    incorretas = ce.get('analise_das_alternativas_incorretas', {})
                    for letra, explicacao in incorretas.items():
                        st.markdown(f"**{letra})** {explicacao}")
                        st.divider()

                with tab3:
                    st.markdown("### Raciocínio Clínico")
                    st.warning(ce.get('raciocinio_clinico_resumido'))
                    
                    if ce.get('pontos_de_prova'):
                        st.markdown("**Pontos Chave para Prova:**")
                        for p in ce.get('pontos_de_prova', []):
                            st.markdown(f"- {p}")

            else:
                # Fallback para o comentário integral antigo
                st.info(f"💡 {q.get('comentario_integral') or 'Sem comentário.'}")

    elif st.session_state.get('questoes_carregadas') == []:
        st.info("Clique em Carregar Questões.")

# ==============================================================================
# PÁGINA 3: GERENCIADOR (CMS)
# ==============================================================================
elif pagina == "⚙️ Gerenciar Questões":
    st.header("Gestão do Banco")
    if not st.session_state.supabase: st.error("Banco off"); st.stop()

    if st.session_state.admin_editando_id:
        res = st.session_state.supabase.table("banco_questoes").select("*").eq("id", st.session_state.admin_editando_id).execute()
        if res.data:
            q = res.data[0]
            st.info(f"Editando ID: {q['id']}")
            with st.form("edit_form"):
                # Campos Básicos
                c1, c2 = st.columns(2)
                disc = c1.text_input("Disciplina", q.get('disciplina'))
                assu = c2.text_input("Assunto", q.get('assunto'))
                enun = st.text_area("Enunciado", q.get('enunciado'))
                
                # Campos JSON Complexos (Edição como Texto)
                c3, c4 = st.columns(2)
                alt_str = json.dumps(q.get('alternativas'), indent=2, ensure_ascii=False)
                novas_alts = c3.text_area("Alternativas (JSON)", alt_str, height=200)
                
                com_est_str = json.dumps(q.get('comentario_estruturado'), indent=2, ensure_ascii=False)
                novo_com_est = c4.text_area("Comentário Estruturado (JSON Completo)", com_est_str, height=200)
                
                gab = st.text_input("Gabarito", q.get('gabarito'))
                
                b1, b2, b3 = st.columns([1,1,1])
                if b1.form_submit_button("💾 Salvar"):
                    try:
                        upd = {
                            "disciplina": disc, "assunto": assu, "enunciado": enun, "gabarito": gab,
                            "alternativas": json.loads(novas_alts),
                            "comentario_estruturado": json.loads(novo_com_est)
                        }
                        st.session_state.supabase.table("banco_questoes").update(upd).eq("id", q['id']).execute()
                        st.success("Salvo!"); st.session_state.admin_editando_id = None; time.sleep(0.5); st.rerun()
                    except Exception as e: st.error(f"Erro JSON: {e}")
                
                if b2.form_submit_button("Cancelar"): st.session_state.admin_editando_id = None; st.rerun()

    else:
        # LISTAGEM
        c_ord, c_nav = st.columns([1, 2])
        ordem = c_ord.selectbox("Ordem", ["Recentes", "Antigas", "Alfabética"])
        
        try:
            tot = st.session_state.supabase.table("banco_questoes").select("id", count='exact').execute().count
            pags = math.ceil(tot / 50)
        except: pags = 1
        
        with c_nav:
            n1, n2, n3 = st.columns([1,1,1])
            if n1.button("⬅️") and st.session_state.admin_pagina_atual > 1: st.session_state.admin_pagina_atual -= 1; st.rerun()
            n2.write(f"<center>{st.session_state.admin_pagina_atual}/{pags}</center>", unsafe_allow_html=True)
            if n3.button("➡️") and st.session_state.admin_pagina_atual < pags: st.session_state.admin_pagina_atual += 1; st.rerun()

        off = (st.session_state.admin_pagina_atual - 1) * 50
        qry = st.session_state.supabase.table("banco_questoes").select("*")
        if "Recentes" in ordem: qry = qry.order("id", desc=True)
        elif "Antigas" in ordem: qry = qry.order("id", desc=False)
        else: qry = qry.order("enunciado", desc=False)
        lista = qry.range(off, off + 49).execute().data
        
        st.session_state.ids_pagina_atual = [x['id'] for x in lista] if lista else []
        
        # AÇÕES EM MASSA
        cont_topo = st.container()
        st.checkbox("Selecionar Tudo", key="chk_master", on_change=callback_selecionar_tudo)
        st.divider()
        
        sel_ids = []
        if lista:
            for item in lista:
                cc, ct, ce, cd = st.columns([0.5, 9, 0.5, 0.5])
                if cc.checkbox("", key=f"sel_{item['id']}"): sel_ids.append(item['id'])
                ct.markdown(f"**[{item.get('id_original') or item['id']}]** {item.get('disciplina')} - {item.get('enunciado')[:80]}...")
                if ce.button("✏️", key=f"e_{item['id']}"): st.session_state.admin_editando_id = item['id']; st.rerun()
                if cd.button("🗑️", key=f"d_{item['id']}"): 
                    st.session_state.supabase.table("banco_questoes").delete().eq("id", item['id']).execute()
                    st.rerun()
                st.divider()
        
        if sel_ids:
            with cont_topo:
                st.error(f"{len(sel_ids)} SELECIONADOS")
                if st.button("EXCLUIR SELECIONADOS", type="primary"):
                    st.session_state.supabase.table("banco_questoes").delete().in_("id", sel_ids).execute()
                    st.rerun()
