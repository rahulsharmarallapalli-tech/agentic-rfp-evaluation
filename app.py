"""Streamlit entry point. Run: streamlit run app.py"""
import json
import uuid
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from rfp.db import get_run, init_db, list_runs, load_criteria, save_criteria
from rfp.evaluator import FixtureEvaluator, GeminiEvaluator
from rfp.models import Supplier
from rfp.orchestrator import evaluate_batch
from rfp.validation import InvalidResponse, validate_response

ROOT = Path(__file__).parent
st.set_page_config(page_title="RFP Intelligence | Supplier Evaluation", page_icon="◈", layout="wide")
st.markdown("""<style>
.block-container{padding-top:4rem;max-width:1400px}
[data-testid="stMetric"]{background:white;border:1px solid #dbe5eb;border-radius:12px;padding:18px}
h1{letter-spacing:-1.5px} h3{letter-spacing:-.3px}
</style>""", unsafe_allow_html=True)
if "workspace_id" not in st.session_state:
    st.session_state.workspace_id = str(uuid.uuid4())
db_path = ROOT / "data" / "sessions" / f"{st.session_state.workspace_id}.sqlite"
init_db(db_path)

with st.sidebar:
    st.markdown("## ◈ RFP Intelligence")
    st.caption("EVIDENCE → EVALUATION → DECISION")
    st.divider()
    mode = st.radio("Evaluation mode", ["Offline demonstration", "Live Gemini evaluation"])
    if mode == "Live Gemini evaluation":
        st.text_input("Gemini API key", type="password", key="api_key")
        st.text_input("Gemini model", value="gemini-2.5-flash", key="model")
        st.caption("Your key stays in this browser session's server memory. It is never saved in SQLite or exports.")
        st.button("Forget API key", on_click=lambda: st.session_state.pop("api_key", None))
    else:
        st.info("Fixed, human-authored scorecards. No live AI call. PDF extraction, validation, calculations and saving run normally.")
    st.divider()
    st.caption("Ranking: PPI ↓ · Date ↑ · Experience ↓ · Name ↑")
    st.caption("Each browser session has its own SQLite workspace. Download JSON before ending your session; cloud restarts may remove local data.")

st.caption("PROCUREMENT DECISION WORKSPACE")
st.title("Compare proposals. See the evidence.")
st.markdown("Evaluate supplier fit with traceable scorecards and transparent peer rankings.")
tab_run, tab_criteria, tab_history, tab_lab = st.tabs(["Evaluate & compare", "Evaluation criteria", "Saved runs", "Validation lab"])


def show_run(run):
    st.divider()
    st.subheader("Supplier leaderboard")
    st.caption(f"Run {run['rfp_run_id']} · {run['created_at']} · {run['status'].upper()}")
    if run["mode"] == "offline_fixture":
        st.warning("DEMONSTRATION — scores are authored fixtures, not an LLM evaluation. Rankings are calculated from validated scores.")
    if run["failures"]:
        st.error("Incomplete cohort: one or more suppliers failed. Peer comparisons use successful suppliers only and are provisional.")
        st.dataframe(run["failures"], hide_index=True, use_container_width=True)
    suppliers = run["suppliers"]
    if suppliers:
        warning_count = sum(len(s["evaluation"]["warnings"]) + len(s["document"]["warnings"]) +
                            sum(len(c["warnings"]) for c in s["metrics"]) for s in suppliers)
        a, b, c, d = st.columns(4)
        a.metric("Suppliers ranked", len(suppliers))
        b.metric("Leading supplier", suppliers[0]["supplier_name"])
        c.metric("Leading PPI", f"{suppliers[0]['ppi']:.2f}%")
        d.metric("Review warnings", warning_count)
        table = pd.DataFrame([{"Rank": s["final_rank"], "Supplier": s["supplier_name"],
            "Absolute / 100": s["absolute_score"], "PPI %": s["ppi"], "Submitted": s["submission_date"],
            "Experience / 10": s["experience_rating"]} for s in suppliers])
        st.dataframe(table, hide_index=True, use_container_width=True,
                     column_config={"Absolute / 100": st.column_config.NumberColumn(format="%.2f"),
                                    "PPI %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.2f")})
        st.caption("PPI ranks this cohort; absolute score measures configured requirements. Display rounding never controls tie-breaks.")
        st.bar_chart(table.set_index("Supplier")[["Absolute / 100", "PPI %"]], color=["#0d9488", "#517ca4"], stack=False)
        st.subheader("Evidence & scorecards")
        selected = st.selectbox("Inspect supplier", [s["supplier_name"] for s in suppliers], key=f"supplier_{run['rfp_run_id']}")
        s = next(s for s in suppliers if s["supplier_name"] == selected)
        st.write(s["evaluation"]["overall_summary"])
        st.info(s["rank_explanation"])
        st.dataframe(pd.DataFrame([{ "Criterion": m["criterion_name"], "Score": m["score"], "Max": m["max_score"],
            "Weight %": m["weight"], "Weighted": m["weighted_score"], "Peer best": m["benchmark"],
            "Gap": m["gap"], "Relative %": m["relative_percent"]} for m in s["metrics"]]),
            hide_index=True, use_container_width=True)
        for m in s["metrics"]:
            with st.expander(f"{m['criterion_name']} · {m['score']:g}/{m['max_score']:g} · page {m['evidence_page'] or '—'}", expanded=False):
                st.write(m["justification"])
                st.caption("EXTRACTED EVIDENCE · " + ("QUOTE MATCH VERIFIED" if m["evidence_verified"] else "UNVERIFIED"))
                st.text(m["evidence"] or "No evidence provided.")
                for w in m["warnings"]:
                    st.warning(w)
        for w in s["evaluation"]["warnings"] + s["document"]["warnings"]:
            st.warning(w)
        if s["evaluation"]["risks"]:
            st.markdown("**Risks to clarify**")
            for risk in s["evaluation"]["risks"]:
                st.write("• " + risk)
        with st.expander("Source text and document fingerprint"):
            st.code(s["document"]["sha256"], language=None)
            for page in s["document"]["pages"]:
                st.caption(f"Page {page['page']}")
                st.text(page["text"])
    with st.expander("Rules, criteria snapshot & workflow trace"):
        st.json({"rules": run["rules"], "criteria_snapshot": run["criteria_snapshot"], "trace": run["trace"]})
    st.download_button("Download complete run JSON", json.dumps(run, indent=2, ensure_ascii=False, allow_nan=False),
                       file_name=f"rfp_run_{run['rfp_run_id']}.json", mime="application/json", key=f"download_{run['rfp_run_id']}")


with tab_criteria:
    st.subheader("Define what good looks like")
    st.write("Active weights must total 100%. Every run retains the criteria used at evaluation time.")
    rows = [c.model_dump() for c in load_criteria(db_path, only_active=False)]
    edited = st.data_editor(pd.DataFrame(rows), hide_index=True, num_rows="dynamic", use_container_width=True,
                            key="criteria_editor", column_config={"is_active": st.column_config.CheckboxColumn("Active"),
                            "weight": st.column_config.NumberColumn("Weight %", min_value=0, max_value=100),
                            "max_score": st.column_config.NumberColumn("Maximum", min_value=0.1)})
    if st.button("Save criteria", type="primary"):
        try:
            save_criteria(db_path, edited.to_dict("records"))
            st.success("Criteria saved in SQLite. The next run will use these values.")
        except (ValueError, TypeError) as exc:
            st.error(str(exc))

with tab_run:
    if mode == "Offline demonstration":
        st.subheader("Four suppliers. One procurement brief.")
        st.write("Apex Systems · BrightPath Tech · NexaWorks · Orbit Digital")
        st.caption("Three-page fictional proposals for a customer-service platform. Different prices, plans, security controls and support commitments.")
        manifest = json.loads((ROOT / "samples/manifest.json").read_text())
        with st.expander("Download fictional proposals"):
            for m in manifest:
                st.download_button(m["supplier_name"], (ROOT / "samples/proposals" / m["pdf_file"]).read_bytes(),
                                   file_name=m["pdf_file"], mime="application/pdf")
        if st.button("Run four-supplier demo", type="primary"):
            inputs = [(Supplier(**{k: m[k] for k in ("supplier_name", "submission_date", "experience_rating")}),
                       (ROOT / "samples/proposals" / m["pdf_file"]).read_bytes()) for m in manifest]
            bar = st.progress(0, text="Starting evaluation")
            try:
                st.session_state.current_run = evaluate_batch(inputs, db_path, FixtureEvaluator(ROOT / "samples"),
                                                              progress=lambda v, t: bar.progress(v, text=t))
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.subheader("Upload supplier proposals")
        st.caption("2–10 selectable-text PDFs · up to 10 MB and 50 pages each · experience rating 0–10")
        uploads = st.file_uploader("Proposal PDFs", type="pdf", accept_multiple_files=True)
        metadata = []
        for i, file in enumerate(uploads):
            with st.expander(f"Supplier {i+1}: {file.name}", expanded=True):
                a, b, c = st.columns([2, 1, 1])
                name = a.text_input("Supplier name", value=Path(file.name).stem.replace("_", " "), key=f"name_{i}_{file.file_id}")
                day = b.date_input("Submission date", value=date.today(), key=f"date_{i}_{file.file_id}")
                experience = c.number_input("Historical experience / 10", min_value=0.0, max_value=10.0, value=5.0, step=0.5,
                                            key=f"experience_{i}_{file.file_id}")
                metadata.append((name, day, experience, file))
        consent = st.checkbox("Send extracted proposal text to Google Gemini for evaluation.")
        if st.button("Evaluate uploaded proposals", type="primary", disabled=not consent):
            try:
                inputs = [(Supplier(supplier_name=n, submission_date=d, experience_rating=e), f.getvalue()) for n,d,e,f in metadata]
                evaluator = GeminiEvaluator(st.session_state.get("api_key", ""), st.session_state.get("model", "gemini-2.5-flash"))
                bar = st.progress(0, text="Starting evaluation")
                st.session_state.current_run = evaluate_batch(inputs, db_path, evaluator, progress=lambda v,t: bar.progress(v,text=t))
            except ValueError as exc:
                st.error(str(exc))
    if "current_run" in st.session_state:
        show_run(st.session_state.current_run)

with tab_history:
    st.subheader("Saved in this workspace")
    runs = list_runs(db_path)
    if runs:
        st.dataframe(runs, hide_index=True, use_container_width=True)
        run_id = st.selectbox("Run to open", [r["rfp_run_id"] for r in runs])
        if st.button("Load saved run"):
            st.session_state.current_run = get_run(db_path, run_id)
            st.success("Loaded. Open Evaluate & compare to inspect the results.")
    else:
        st.info("Run an evaluation to create a saved result.")

with tab_lab:
    st.subheader("Make failures visible")
    st.write("Exercise validation without spending API credits. This does not alter your saved evaluations.")
    case = st.selectbox("Test case", ["Malformed JSON", "Out-of-range and missing criteria", "Unsupported evidence"])
    if st.button("Run validation case"):
        criteria = load_criteria(db_path)
        first = criteria[0]
        raw = "{broken json" if case == "Malformed JSON" else json.dumps({"supplier_name":"Lab supplier", "criteria":[{
            "criterion_id":first.criterion_id, "score":first.max_score*2, "max_score":first.max_score,
            "justification":"Deliberately problematic model output for demonstration.",
            "evidence":"Documented capability." if case != "Unsupported evidence" else "Invented certification.",
            "evidence_page":1}], "risks":[], "overall_summary":"Validation example."})
        st.code(raw, language="json")
        try:
            result = validate_response(raw, criteria, "Lab supplier", [{"page":1,"text":"Documented capability."}])
            st.success("Normalized with warnings. Inspect clipped scores and missing-criterion defaults below.")
            st.json(result.model_dump())
        except InvalidResponse as exc:
            st.error(f"Rejected: {exc} In live evaluation this is retried up to three total attempts, then excluded.")

st.divider()
st.caption("Evidence matching verifies that a quotation exists, not that a supplier's claims are true. Human review remains part of procurement.")
