"""ThreatLens UI. Uses the API if THREATLENS_API_URL is set, otherwise runs the pipeline in-process."""

import os
import re

import httpx
import streamlit as st

API_URL = os.getenv("THREATLENS_API_URL", "")

st.set_page_config(page_title="ThreatLens", page_icon="🔎", layout="wide")
st.title("🔎 ThreatLens")
st.caption("RAG copilot for SOC & CTI — MITRE ATT&CK · CISA KEV · NVD · CERT-FR · Sigma")

EXAMPLES = [
    "Is CVE-2024-3400 exploited in the wild and what should I do?",
    "winword.exe spawned powershell.exe -enc JABzAD0A... — what is this and how do I detect it?",
    "How do attackers dump credentials from LSASS, and which Sigma rules detect it?",
    "Quels avis CERT-FR récents concernent Fortinet ?",
]

with st.sidebar:
    st.subheader("Examples")
    for ex in EXAMPLES:
        if st.button(ex[:60] + ("…" if len(ex) > 60 else ""), use_container_width=True):
            st.session_state["q"] = ex
    model_choice = st.radio("Model", ["auto (router)", "small", "large"])

question = st.text_area("Question, alert or log line", key="q", height=120)


def run(q: str, force: str | None) -> dict:
    if API_URL:
        r = httpx.post(f"{API_URL}/ask", json={"question": q, "force_model": force}, timeout=180)
        r.raise_for_status()
        return r.json()
    from threatlens.pipeline import answer

    return answer(q, force_model=force).to_dict()


if st.button("Ask", type="primary") and question.strip():
    from threatlens.config import settings

    force = {"small": settings.small_model, "large": settings.large_model}.get(model_choice)
    with st.spinner("Retrieving and reasoning…"):
        res = run(question, force)

    urls = {c["chunk"]["doc_id"]: c["chunk"]["url"] for c in res["citations"]}

    def linkify(text: str) -> str:
        return re.sub(
            r"\[([a-z]+:[^\]\s]+)\]",
            lambda m: f"[[{m.group(1)}]]({urls[m.group(1)]})" if m.group(1) in urls else m.group(0),
            text,
        )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(linkify(res["answer"]))
    with col2:
        st.metric("Model", res["model"].split("/")[-1])
        st.caption(f"Route: {res['route_reason']}")
        st.metric("Latency", f"{res['latency_ms']} ms")
        st.metric("Cost", f"${res['cost_usd']:.5f}")
        if res["guard_flags"]:
            st.warning("Guard flags: " + ", ".join(res["guard_flags"]))
        st.subheader("Sources")
        for c in res["citations"]:
            ch = c["chunk"]
            with st.expander(f"{ch['doc_id']} · {c['score']:.2f}"):
                st.markdown(f"[{ch['title']}]({ch['url']})")
                st.text(ch["text"][:1200])
