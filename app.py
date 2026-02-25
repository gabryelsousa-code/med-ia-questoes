import streamlit as st
from supabase import create_client, Client
import json
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MedResidency - Banco de Questões",
    page_icon="🏥",
    layout="wide"
)

# --- ESTADO DA SESSÃO ---
if 'supabase' not in st.session_state: st.session_state.supabase = None
if 'indice_questao' not in st.session_state: st.session_state.indice_questao = 0
if 'questoes_carregadas' not in st.session_state: st.session_state.questoes_carregadas = []
if 'resposta_mostrada' not in st.session_state: st.session_state.resposta_mostrada = False

# --- FUNÇÕES ---
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except:
        return None

def resetar_navegacao():
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
    # ADICIONEI A NOVA PÁGINA AQUI
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
# PÁGINA 2: SIMULADOR
# ==============================================================================
elif pagina == "📝 Resolver Questões":
    st.header("Simulador de Prova")
    
    if not st.session_state.supabase:
        st.warning("Banco desconectado.")
        st.stop()

    col1, col2 = st.columns(2)
    if 'lista_disciplinas' not in st.session_state:
        try:
            res = st.session_state.supabase.table("banco_questoes").select("disciplina").execute()
            lista = sorted(list(set([x['disciplina'] for x in res.data if x['disciplina']])))
            lista.insert(0, "Todas")
            st.session_state.lista_disciplinas = lista
        except:
            st.session_state.lista_disciplinas = ["Todas"]

    filtro_disciplina = col1.selectbox("Disciplina:", st.session_state.lista_disciplinas, on_change=resetar_navegacao)
    
    if st.button("Carregar Questões"):
        try:
            query = st.session_state.supabase.table("banco_questoes").select("*")
            if filtro_disciplina != "Todas":
                query = query.eq("disciplina", filtro_disciplina)
            res = query.limit(10000).execute() # Limite alto
            
            if res.data:
                st.session_state.questoes_carregadas = res.data
                resetar_navegacao()
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
            if letra.upper() == gab:
                st.success("CORRETO! 🎉")
            else:
                st.error(f"ERRADO. Gabarito: **{gab}**")
            st.info(f"💡 {q.get('comentario', 'Sem comentário.')}")

    elif st.session_state.get('questoes_carregadas') == []:
        st.info("Clique em Carregar Questões.")

# ==============================================================================
# PÁGINA 3: GERENCIADOR (NOVIDADE!)
# ==============================================================================
elif pagina == "⚙️ Gerenciar Questões":
    st.header("Gerenciamento do Banco")
    
    if not st.session_state.supabase:
        st.warning("Banco desconectado.")
        st.stop()

    # 1. Pesquisa
    termo = st.text_input("🔍 Pesquisar por enunciado ou ID:", placeholder="Digite uma palavra chave...")
    
    resultados = []
    if termo:
        try:
            # Busca por ID se for número, ou Enunciado se for texto
            if termo.isdigit():
                 res = st.session_state.supabase.table("banco_questoes").select("*").eq("id", int(termo)).execute()
            else:
                 res = st.session_state.supabase.table("banco_questoes").select("*").ilike("enunciado", f"%{termo}%").limit(20).execute()
            resultados = res.data
        except Exception as e:
            st.error(f"Erro na busca: {e}")

    # 2. Exibição da Tabela
    if resultados:
        st.write(f"Encontrados: {len(resultados)}")
        
        # Cria um selectbox para escolher qual editar
        opcoes_edicao = {f"{q['id']} - {q['enunciado'][:50]}...": q for q in resultados}
        selecionada_chave = st.selectbox("Selecione a questão para editar:", list(opcoes_edicao.keys()))
        
        if selecionada_chave:
            q_edit = opcoes_edicao[selecionada_chave]
            
            st.markdown("---")
            st.subheader(f"Editando Questão #{q_edit['id']}")
            
            with st.form("form_edicao"):
                col_a, col_b = st.columns(2)
                novo_disc = col_a.text_input("Disciplina", q_edit.get('disciplina'))
                novo_assunto = col_b.text_input("Assunto", q_edit.get('assunto'))
                
                novo_enunciado = st.text_area("Enunciado", q_edit.get('enunciado'), height=150)
                
                # Editor de Alternativas (JSON)
                st.markdown("**Alternativas (Formato JSON):**")
                alt_str = json.dumps(q_edit.get('alternativas', {}), indent=2, ensure_ascii=False)
                novo_alt_str = st.text_area("Edite o JSON das alternativas", alt_str, height=200)
                
                col_c, col_d = st.columns(2)
                novo_gabarito = col_c.text_input("Gabarito (Letra)", q_edit.get('gabarito'))
                novo_comentario = st.text_area("Comentário", q_edit.get('comentario'), height=150)
                
                # Botões de Ação
                c1, c2 = st.columns([1, 5])
                salvar = c1.form_submit_button("💾 Salvar Alterações")
                
            # Botão de Excluir (Fora do form para evitar submit acidental)
            if st.button("🗑️ EXCLUIR ESTA QUESTÃO", type="primary"):
                 try:
                     st.session_state.supabase.table("banco_questoes").delete().eq("id", q_edit['id']).execute()
                     st.success("Questão excluída com sucesso!")
                     time.sleep(1)
                     st.rerun()
                 except Exception as e:
                     st.error(f"Erro ao excluir: {e}")

            # Lógica de Salvar
            if salvar:
                try:
                    # Valida o JSON das alternativas
                    novas_alts = json.loads(novo_alt_str)
                    
                    dados_atualizados = {
                        "disciplina": novo_disc,
                        "assunto": novo_assunto,
                        "enunciado": novo_enunciado,
                        "alternativas": novas_alts,
                        "gabarito": novo_gabarito,
                        "comentario": novo_comentario
                    }
                    
                    st.session_state.supabase.table("banco_questoes").update(dados_atualizados).eq("id", q_edit['id']).execute()
                    st.success("Questão atualizada com sucesso!")
                    time.sleep(1)
                    st.rerun()
                    
                except json.JSONDecodeError:
                    st.error("Erro: O campo 'Alternativas' contém um JSON inválido. Verifique as aspas e vírgulas.")
                except Exception as e:
                    st.error(f"Erro ao atualizar: {e}")
            
    elif termo:
        st.warning("Nenhuma questão encontrada.")
