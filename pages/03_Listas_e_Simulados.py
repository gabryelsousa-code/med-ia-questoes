import random
import streamlit as st

from services.auth import require_auth, logout
from services.database import get_supabase
from services.categories import (
    list_categories,
    create_category,
    ensure_default_category,
    delete_category,
)
from services.exams import (
    get_user_exams,
    delete_exam,
    get_exam_question_ids,
    create_exam,
    update_exam,
)
from services.attempts import start_attempt

from utils.components import inject_custom_css

st.set_page_config(layout="wide")
inject_custom_css()
require_auth()

# Sidebar manual (mesmo padrão do seu app)
with st.sidebar:
    st.markdown(f"**Dr(a). {st.session_state.profile['full_name']}**")
    st.markdown("---")
    if st.button("📊 Meu Desempenho", use_container_width=True):
        st.switch_page("pages/01_Dashboard.py")
    if st.button("🔍 Banco de Questões", use_container_width=True):
        st.switch_page("pages/02_Banco_de_Questoes.py")
    if st.button("🗂️ Listas & Simulados", use_container_width=True):
        st.switch_page("pages/03_Listas_e_Simulados.py")
    if st.button("❌ Caderno de Erros", use_container_width=True):
        st.switch_page("pages/06_Caderno_de_Erros.py")
    if st.button("📌 Revisão do Dia", use_container_width=True):
        st.switch_page("pages/07_Revisao_do_Dia.py")

    if st.session_state.profile.get("role") == "admin":
        if st.button("⚙️ Administração", use_container_width=True):
            st.switch_page("pages/99_Painel_Admin.py")

    st.markdown("---")
    if st.button("Sair da Conta"):
        logout()

st.title("🗂️ Listas & Simulados")

client = get_supabase()
user_id = st.session_state.user.id

# Categorias
default_cat_id = ensure_default_category(user_id)
cats = list_categories(user_id)
cat_map = {c["id"]: c for c in cats}
cat_items = [("ALL", "📚 Todas as categorias")] + [(c["id"], f"{(c.get('icon') or '📁')} {c['name']}") for c in cats]

top1, top2, top3 = st.columns([2.2, 3.2, 2.6])

with top1:
    selected_cat = st.selectbox(
        "Filtrar por categoria",
        [x[0] for x in cat_items],
        format_func=lambda v: dict(cat_items)[v],
    )

with top2:
    with st.expander("📁 Gerenciar categorias"):
        c1, c2 = st.columns([3, 1])
        new_name = c1.text_input("Nova categoria", placeholder="Ex: Cardiologia", key="cat_new_name")
        new_icon = c2.text_input("Ícone", value="📁", key="cat_new_icon")
        if st.button("Criar categoria", use_container_width=True):
            if new_name.strip():
                create_category(user_id, new_name.strip(), icon=new_icon.strip() or "📁")
                st.success("Categoria criada!")
                st.rerun()

        st.markdown("---")
        st.caption("Remover categoria NÃO apaga listas/simulados (eles ficam sem categoria).")
        for c in cats:
            col_a, col_b = st.columns([6, 1])
            col_a.write(f"{c.get('icon') or '📁'} **{c['name']}**")
            if col_b.button("🗑️", key=f"del_cat_{c['id']}"):
                delete_category(c["id"])
                st.rerun()

with top3:
    st.markdown("""
    <div class="toolbar">
      <b>Dica:</b> selecione questões no <b>Banco</b> e salve como <b>Lista</b> ou <b>Simulado</b>.
      <div class="small-muted">Você também pode gerar simulados automaticamente abaixo.</div>
    </div>
    """, unsafe_allow_html=True)

tabs = st.tabs(["📚 Listas", "🧪 Simulados", "⚡ Gerar Simulado"])

def fetch_exams(exam_type: str):
    cat_id = None if selected_cat == "ALL" else selected_cat
    return get_user_exams(user_id, exam_type=exam_type, category_id=cat_id)

def enrich_exam_stats(exams: list[dict]):
    """Calcula contagem de questões e tentativas (sem N+1 pesado)."""
    if not exams:
        return {}, {}, {}, {}

    exam_ids = [e["id"] for e in exams]

    # contagem de questões por exam
    eq = client.table("exam_questions").select("exam_id").in_("exam_id", exam_ids).execute().data or []
    qcount = {}
    for r in eq:
        qcount[r["exam_id"]] = qcount.get(r["exam_id"], 0) + 1

    # tentativas
    atts = client.table("attempts") \
        .select("id,exam_id,status,started_at,finished_at,current_index") \
        .eq("user_id", user_id) \
        .in_("exam_id", exam_ids) \
        .order("started_at", desc=True).execute().data or []

    in_progress = {}
    last_finished = {}
    for a in atts:
        if a["status"] == "in_progress" and a["exam_id"] not in in_progress:
            in_progress[a["exam_id"]] = a
        if a["status"] == "finished" and a["exam_id"] not in last_finished:
            last_finished[a["exam_id"]] = a

    # scores do último finished
    last_ids = [a["id"] for a in last_finished.values()]
    score_map = {}
    if last_ids:
        ans = client.table("attempt_answers") \
            .select("attempt_id,is_correct,user_answer") \
            .in_("attempt_id", last_ids).execute().data or []
        tmp = {}
        for row in ans:
            aid = row["attempt_id"]
            tmp.setdefault(aid, {"answered": 0, "correct": 0})
            if row.get("user_answer") is not None:
                tmp[aid]["answered"] += 1
            if row.get("is_correct") is True:
                tmp[aid]["correct"] += 1
        score_map = tmp

    return qcount, in_progress, last_finished, score_map

def render_exam_list(exams: list[dict], exam_type_label: str):
    if not exams:
        st.info(f"Você ainda não tem {exam_type_label.lower()} nesta categoria.")
        return

    qcount, in_progress, last_finished, score_map = enrich_exam_stats(exams)

    for e in exams:
        eid = e["id"]
        cat = cat_map.get(e.get("category_id") or "")
        cat_label = f"{(cat.get('icon') or '📁')} {cat['name']}" if cat else "📁 Sem categoria"

        prog = in_progress.get(eid)
        last = last_finished.get(eid)

        last_score_txt = "—"
        if last:
            s = score_map.get(last["id"])
            if s and s["answered"] > 0:
                pct = (s["correct"] / s["answered"]) * 100
                last_score_txt = f"{s['correct']}/{s['answered']} ({pct:.0f}%)"

        left, right = st.columns([7, 3])

        with left:
            st.markdown(f"""
            <div class="card-container">
              <div style="display:flex; justify-content:space-between; gap:10px;">
                <div>
                  <div style="font-weight:900; font-size:1.1rem; color:#0B1C2D;">{e.get('title')}</div>
                  <div class="small-muted">{cat_label} • tipo: <b>{(e.get('exam_type') or '').upper()}</b> • modo: <b>{(e.get('mode') or 'treino').upper()}</b></div>
                </div>
                <div class="small-muted" style="text-align:right;">
                  <div><b>{qcount.get(eid, 0)}</b> questões</div>
                  <div>Último: <b>{last_score_txt}</b></div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        with right:
            st.markdown("<br>", unsafe_allow_html=True)

            if prog:
                if st.button("▶️ Continuar", key=f"cont_{eid}", use_container_width=True):
                    st.session_state.active_attempt_id = prog["id"]
                    st.switch_page("pages/04_Resolver.py")
            else:
                if st.button("▶️ Iniciar", key=f"start_{eid}", use_container_width=True):
                    q_ids = get_exam_question_ids(eid)
                    if e.get("randomize_questions"):
                        random.shuffle(q_ids)
                    attempt_id = start_attempt(user_id, eid, question_order=q_ids)
                    st.session_state.active_attempt_id = attempt_id
                    st.switch_page("pages/04_Resolver.py")

            with st.expander("⚙️ Opções"):
                # mover categoria
                cat_choices = [("NONE", "Sem categoria")] + [(c["id"], f"{c.get('icon') or '📁'} {c['name']}") for c in cats]
                new_cat = st.selectbox(
                    "Mover para",
                    [x[0] for x in cat_choices],
                    format_func=lambda v: dict(cat_choices)[v],
                    key=f"mv_{eid}"
                )
                if st.button("Salvar categoria", key=f"mv_btn_{eid}", use_container_width=True):
                    update_exam(eid, {"category_id": None if new_cat == "NONE" else new_cat})
                    st.success("Atualizado!")
                    st.rerun()

                # editar título/mode rapidamente
                new_title = st.text_input("Renomear", value=e.get("title") or "", key=f"ttl_{eid}")
                new_mode = st.selectbox("Modo", ["treino", "prova"], index=0 if (e.get("mode") or "treino") == "treino" else 1, key=f"mode_{eid}")
                rnd = st.checkbox("Randomizar questões", value=bool(e.get("randomize_questions")), key=f"rnd_{eid}")
                if st.button("Salvar ajustes", key=f"save_cfg_{eid}", use_container_width=True):
                    update_exam(eid, {"title": new_title.strip() or e.get("title"), "mode": new_mode, "randomize_questions": rnd})
                    st.success("Salvo!")
                    st.rerun()

                if st.button("🗑️ Excluir", key=f"del_exam_{eid}", use_container_width=True):
                    delete_exam(eid)
                    st.rerun()

with tabs[0]:
    st.subheader("📚 Minhas Listas")
    listas = fetch_exams("lista")
    render_exam_list(listas, "Listas")

with tabs[1]:
    st.subheader("🧪 Meus Simulados")
    sims = fetch_exams("simulado")
    render_exam_list(sims, "Simulados")

with tabs[2]:
    st.subheader("⚡ Gerar Simulado Automático")

    with st.container(border=True):
        a, b, c, d = st.columns([2, 2, 1, 2])

        r = client.table("questions").select("disciplina,banca,ano").eq("ativo", True).limit(2000).execute()
        data = r.data or []
        disciplinas = sorted({x["disciplina"] for x in data if x.get("disciplina")})
        bancas = sorted({x["banca"] for x in data if x.get("banca")})
        anos = sorted({x["ano"] for x in data if x.get("ano")})

        f_disc = a.selectbox("Disciplina", ["Todas"] + disciplinas)
        f_banca = b.selectbox("Banca", ["Todas"] + bancas)
        f_ano = c.selectbox("Ano", ["Todos"] + [str(x) for x in anos])
        qtd = d.number_input("Qtd. questões", min_value=5, max_value=200, value=20)

        e1, e2, e3 = st.columns([3, 2, 2])
        sim_title = e1.text_input("Nome do simulado", value="Simulado Gerado")
        sim_mode = e2.selectbox("Modo", ["treino", "prova"])
        cat_only = [x for x in cat_items if x[0] != "ALL"]
        sim_cat = e3.selectbox("Categoria", [x[0] for x in cat_only], format_func=lambda v: dict(cat_only)[v])

        s1, s2, s3 = st.columns([2, 2, 2])
        randomize_q = s1.checkbox("Randomizar questões", value=True)
        time_limit = s2.number_input("Tempo (min) opcional", min_value=0, value=0)
        start_now = s3.checkbox("Iniciar após criar", value=True)

    if st.button("⚡ Gerar agora", use_container_width=True, type="primary"):
        q = client.table("questions").select("id").eq("ativo", True)
        if f_disc != "Todas":
            q = q.eq("disciplina", f_disc)
        if f_banca != "Todas":
            q = q.eq("banca", f_banca)
        if f_ano != "Todos":
            q = q.eq("ano", int(f_ano))

        pool = (q.limit(5000).execute().data or [])
        pool_ids = [x["id"] for x in pool]

        if len(pool_ids) < int(qtd):
            st.error(f"Poucas questões para gerar: encontrei {len(pool_ids)} e você pediu {qtd}.")
        else:
            random.shuffle(pool_ids)
            chosen = pool_ids[: int(qtd)]
            if not randomize_q:
                chosen = pool_ids[: int(qtd)]

            exam_id = create_exam(
                user_id=user_id,
                title=sim_title.strip() or "Simulado Gerado",
                exam_type="simulado",
                category_id=sim_cat,
                mode=sim_mode,
                question_ids=chosen,
                is_generated=True,
                time_limit_minutes=(None if time_limit == 0 else int(time_limit)),
                randomize_questions=False
            )
            st.success("Simulado gerado com sucesso!")

            if start_now:
                attempt_id = start_attempt(user_id, exam_id, question_order=chosen)
                st.session_state.active_attempt_id = attempt_id
                st.switch_page("pages/04_Resolver.py")
