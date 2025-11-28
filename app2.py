import streamlit as st
import requests
import time

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="🛰️ FactRadar — AI Misinformation Detector",
    layout="wide",
)

API_URL = "http://127.0.0.1:8000/detect"

st.title("🛰️ FactRadar — AI-Ensemble Misinformation Detection")
st.markdown("### ML (MNLI) + Gemini 2.5 + Llama 3.1 + Web Scraping + SerpAPI")
st.markdown("---")

# =========================================================
# INPUT MODE
# =========================================================
mode = st.radio("Choose input type:", ["Claim Text", "URL"], horizontal=True)

user_input = st.text_area(
    "Paste a claim or news article URL:",
    height=140,
    placeholder=(
        "Example (Claim): COVID vaccine causes infertility\n\n"
        "Example (URL): https://example.com/news/abc"
    ),
)

# =========================================================
# ANALYZE BUTTON
# =========================================================
if st.button("Analyze", use_container_width=True):

    if not user_input.strip():
        st.warning("⚠️ Please enter a claim or URL before analyzing.")
        st.stop()

    # Prepare payload for backend
    payload = {
        "text": user_input if mode == "Claim Text" else None,
        "url": user_input if mode == "URL" else None,
    }

    # ====== RUN BACKEND ======
    start = time.time()
    with st.spinner("⏳ Running AI ensemble analysis..."):
        try:
            r = requests.post(API_URL, json=payload, timeout=200)
            r.raise_for_status()
            res = r.json()
        except Exception as e:
            st.error(f"❌ Backend Error: {e}")
            st.stop()

    end = time.time()
    st.success(f"Analysis completed in **{round(end - start, 2)} seconds**")
    st.markdown("---")

    # =========================================================
    # FINAL VERDICT
    # =========================================================
    st.subheader("🧭 Final Verdict")

    verdict = res["final_label"]
    trust = res["trust_score"]

    if verdict == "REAL":
        st.success(f"🟢 REAL — Trust Score: {trust}%")
    elif verdict == "MISINFORMATION":
        st.error(f"🔴 MISINFORMATION — Trust Score: {trust}%")
    else:
        st.warning(f"🟡 UNCERTAIN — Trust Score: {trust}%")

    st.markdown("---")

    # =========================================================
    # MODEL VOTES
    # =========================================================
    st.subheader("🗳️ AI Model Votes (Ensemble Decision)")

    col1, col2, col3 = st.columns(3)

    col1.metric("ML Model (MNLI)", res["ml_label"])
    col2.metric("Gemini 2.5 Flash", res["gemini_label"])
    col3.metric("Llama 3.1 (OpenRouter)", res["llama_label"])

    st.markdown("---")

    # =========================================================
    # EXTRACTED CLAIM
    # =========================================================
    st.subheader("📝 Extracted Claim")
    st.info(res["claim"])
    st.markdown("---")

    # =========================================================
    # EVIDENCE SECTION
    # =========================================================
    st.subheader("📚 Evidence Retrieved (SerpAPI + Web Scraping)")

    evidence = res.get("evidence", [])

    if not evidence:
        st.warning("⚠️ No evidence sources were retrieved from search engines.")
    else:
        for idx, ev in enumerate(evidence):
            st.markdown(f"### 🔗 Source {idx + 1}: [{ev['title']}]({ev['url']})")

            st.write(f"**URL:** {ev['url']}")
            st.write("**Extracted Text / Snippet:**")
            st.info(ev["snippet"])

            st.markdown("---")

    # =========================================================
    # SYSTEM LOGS
    # =========================================================
    st.subheader("🧠 Agent Logs (Backend Processing Steps)")

    logs = res.get("logs", [])

    with st.expander("Click to view detailed logs"):
        if logs:
            st.code("\n".join(logs))
        else:
            st.info("No logs returned from backend.")
