import json
import streamlit as st
import pandas as pd

from services.auth import require_auth, logout
from services.questions import (
    validate_question_dict,
    insert_question,
    update_question,
    get_question,
    search_questions_admin,
    upsert_questions_bulk,
)
from utils.components import inject_custom_css

st.set_page_config(layout="wide")
inject_custom_css()
require_auth()

if st.session_state.profile.get("role") != "admin":
    st.error("Acesso negado.")
    st.stop()

with st.sidebar:
    st.markdown(f"**Admin: {st.session_state.profile['full_name']}**")
    st.markdown("---")
    if st.button("📊 Meu Desempenho", use_container_width=True): st.switch_page("pages/01_Dashboard.py")
    if st.button("🔍 Banco de Questões", use_container_width=True): st.switch_page("pages/02_Banco_de_Questoes.py")
    if st.button("🗂️ Listas & Simulados", use_container_width=True): st.switch_page("pages/03_Listas_e_Simulados.py")
    if st.button("❌ Caderno de Erros", use_container_width=True): st.switch_page("pages/06_Caderno_de_Erros.py")
    if st.button("📌 Revisão do Dia", use_container_width=True): st.switch_page("pages/07_Revisao_do_Dia.py")
    if st.button("⚙️ Administração", use_container_width=True): st.switch_page("pages/99_Painel_Admin.py")
    st.markdown("---")
    if st.button("Sair da Conta"): logout()

st.title("⚙️ Painel Admin — Questões")

tabs = st.tabs(["📥 Importar JSON", "➕ Criar Questão", "✏️ Buscar / Editar"])

# ---------------------------
# TAB 1: IMPORT JSON
# ---------------------------
with tabs[0]:
    st.subheader("📥 Importar questões em JSON (preview + validação + upsert por id_original)")

    f = st.file_uploader("Envie um arquivo .json (lista de questões)", type=["json"])
    chunk_size = st.number_input("Chunk size (lote)", min_value=50, max_value=500, value=200)

    if f:
        try:
            data = json.load(f)
            if not isinstance(data, list):
                st.error("O JSON deve ser uma LISTA de questões.")
                st.stop()

            valid, invalid = [], []
            for i, q in enumerate(data):
                if not isinstance(q, dict):
                    invalid.append((i, ["Item não é objeto JSON (dict)"]))
                    continue

                # normalização leve
                if "gabarito" in q and isinstance(q["gabarito"], str):
                    q["gabarito"] = q["gabarito"].strip().upper()
                if "ativo" not in q:
                    q["ativo"] = True

                errs = validate_question_dict(q)
                if errs:
                    invalid.append((i, errs))
                else:
                    valid.append(q)

            c1, c2, c3 = st.columns(3)
            c1.metric("Total", len(data))
            c2.metric("Válidas", len(valid))
            c3.metric("Inválidas", len(invalid))

            with st.expander("👀 Preview (primeiras 10 válidas)", expanded=True):
                if valid:
                    st.dataframe(pd.DataFrame(valid[:10]), use_container_width=True)
                else:
                    st.info("Nenhuma questão válida para pré-visualizar.")

            if invalid:
                with st.expander("⚠️ Itens inválidos (erros)", expanded=False):
                    for idx, errs in invalid[:40]:
                        st.write(f"Item #{idx}: {errs}")

            st.markdown("---")
            if st.button("🚀 Importar agora (UPsert)", type="primary", use_container_width=True, disabled=(len(valid) == 0)):
                ok, fail, errs = upsert_questions_bulk(valid, chunk_size=int(chunk_size))
                st.success(f"Import finalizado: OK={ok} | Falhas={fail}")
                if errs:
                    st.warning("Ocorreram erros em alguns lotes:")
                    for e in errs[:6]:
                        st.code(e)

                st.info("Recomendação: mantenha id_original único para evitar duplicações.")
        except Exception as e:
            st.error(f"Falha ao ler JSON: {e}")

# ---------------------------
# Form helper
# ---------------------------
def question_form(initial: dict | None = None, submit_label: str = "Salvar"):
    initial = initial or {}
    with st.form(key=f"q_form_{initial.get('id','new')}"):
        c1, c2, c3, c4 = st.columns([2,2,2,1])
        id_original = c1.text_input("id_original", value=initial.get("id_original") or "")
        disciplina = c2.text_input("disciplina*", value=initial.get("disciplina") or "")
        assunto = c3.text_input("assunto", value=initial.get("assunto") or "")
        ativo = c4.checkbox("Ativo", value=bool(initial.get("ativo", True)))

        c5, c6, c7 = st.columns([2,1,1])
        banca = c5.text_input("banca", value=initial.get("banca") or "")
        ano = c6.number_input("ano", min_value=0, value=int(initial.get("ano") or 0))
        gabarito = c7.text_input("gabarito*", value=(initial.get("gabarito") or "").strip().upper(), max_chars=1)

        enunciado = st.text_area("enunciado*", value=initial.get("enunciado") or "", height=160)

        alts_default = initial.get("alternativas") or {"A":"", "B":"", "C":"", "D":"", "E":""}
        alts_text = st.text_area("alternativas (JSON)*", value=json.dumps(alts_default, ensure_ascii=False, indent=2), height=180)

        com_default = initial.get("comentario_estruturado") or {"fundamentacao_cientifica": "", "justificativa_alternativa_correta": {"letra": "", "explicacao": ""}}
        com_text = st.text_area("comentario_estruturado (JSON)", value=json.dumps(com_default, ensure_ascii=False, indent=2), height=180)

        tags_base_str = st.text_input("tags_base (vírgula)", value=",".join(initial.get("tags_base") or []))

        submitted = st.form_submit_button(submit_label, use_container_width=True)

    if not submitted:
        return None

    try:
        alternativas = json.loads(alts_text)
        if not isinstance(alternativas, dict):
            st.error("alternativas precisa ser JSON objeto (dict).")
            return None
    except Exception as e:
        st.error(f"JSON inválido em alternativas: {e}")
        return None

    try:
        comentario_estruturado = json.loads(com_text) if com_text.strip() else None
    except Exception as e:
        st.error(f"JSON inválido em comentario_estruturado: {e}")
        return None

    payload = {
        "id_original": id_original.strip() or None,
        "disciplina": disciplina.strip(),
        "assunto": assunto.strip() or None,
        "banca": banca.strip() or None,
        "ano": (int(ano) if int(ano) > 0 else None),
        "enunciado": enunciado.strip(),
        "alternativas": alternativas,
        "gabarito": (gabarito.strip().upper() if gabarito else ""),
        "comentario_estruturado": comentario_estruturado,
        "tags_base": [t.strip() for t in tags_base_str.split(",") if t.strip()],
        "ativo": ativo
    }

    errs = validate_question_dict(payload)
    if errs:
        st.error("Erros de validação:\n- " + "\n- ".join(errs))
        return None

    return payload

# ---------------------------
# TAB 2: CREATE
# ---------------------------
with tabs[1]:
    st.subheader("➕ Criar Questão")
    payload = question_form(initial=None, submit_label="Criar questão")
    if payload:
        try:
            created = insert_question(payload)
            st.success(f"Questão criada! id={created.get('id')}")
        except Exception as e:
            st.error(f"Falha ao criar: {e}")

# ---------------------------
# TAB 3: EDIT
# ---------------------------
with tabs[2]:
    st.subheader("✏️ Buscar e Editar Questões")

    s = st.text_input("Buscar por id_original ou texto do enunciado")
    if not s:
        st.info("Digite algo para buscar.")
        st.stop()

    results = search_questions_admin(s, limit=40)

    if not results:
        st.warning("Nenhum resultado.")
        st.stop()

    def label(r):
        return f"{r.get('id_original') or '—'} | {r.get('disciplina')} | {str(r.get('enunciado',''))[:70]}..."

    sel_id = st.selectbox(
        "Resultados",
        [r["id"] for r in results],
        format_func=lambda x: label(next(r for r in results if r["id"] == x))
    )

    q_full = get_question(sel_id)

    st.markdown("---")
    st.subheader("Editar")

    payload = question_form(initial=q_full, submit_label="Salvar alterações")
    if payload:
        try:
            update_question(sel_id, payload)
            st.success("Atualizado com sucesso!")
        except Exception as e:
            st.error(f"Falha ao atualizar: {e}")
