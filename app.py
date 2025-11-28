import streamlit as st
import requests
import time

# ======================================
# PREMIUM UI CSS
# ======================================
st.set_page_config(
    page_title="🛰️ FactRadar – AI Misinformation Detector",
    layout="wide",
)

st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

body {
    background: radial-gradient(circle at 10% 20%, #0a0f24 0%, #000000 100%);
    color: white !important;
}

.block-container {
    padding-top: 2rem;
}

h1, h2, h3 {
    color: #FFFFFF !important;
}

/* CARD STYLE */
.card {
    background: rgba(255, 255, 255, 0.08);
    padding: 20px;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 18px;
    transition: 0.2s ease;
}
.card:hover {
    background: rgba(255, 255, 255, 0.13);
}

/* Evidence card */
.evidence-card {
    background: rgba(255,255,255,0.06);
    padding: 18px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 14px;
}

/* Gradient text */
.gradient {
    background: linear-gradient(90deg, #00e5ff, #0084ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Summary box */
.summary-box {
    background: rgba(0, 136, 255, 0.12);
    border-left: 4px solid #008cff;
    padding: 14px;
    border-radius: 10px;
    margin-bottom: 20px;
}

/* Divider */
.divider {
    margin-top: 25px;
    margin-bottom: 25px;
    border-bottom: 1px solid rgba(255,255,255,0.15);
}

</style>
""", unsafe_allow_html=True)


# ======================================
# HEADER
# ======================================
st.markdown("<h1 class='gradient'>🛰️ FactRadar — AI Misinformation Intelligence</h1>", unsafe_allow_html=True)
st.write("### Multimodal AI system combining MNLI, Gemini 2.5, Llama 3.1, SerpAPI, and Smart Scraping.")

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)


# ======================================
# INPUT
# ======================================
st.markdown("### ✍️ Enter Claim or URL")
query = st.text_area(
    "",
    height=140,
    placeholder="Example: COVID vaccine causes infertility",
)

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)


# ======================================
# ANALYZE BUTTON
# ======================================
if st.button("🚀 Analyze", use_container_width=True):

    start = time.time()

    with st.spinner("FactRadar AI Agents working together..."):
        try:
            response = requests.post("http://127.0.0.1:8000/detect", json={"url": query}, timeout=120)
            res = response.json()
        except Exception as e:
            st.error(f"❌ Backend Error: {e}")
            st.stop()

    end = time.time()
    st.success(f"⏱ Completed in **{round(end - start, 2)}s**")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ======================================
    # FINAL VERDICT CARD
    # ======================================
    verdict = res["final_label"]
    trust = res["trust_score"]

    st.markdown("### 🧭 Final Verdict")

    if verdict == "REAL":
        st.markdown(f"<div class='card'><h2>🟢 REAL</h2><p>Trust Score: {trust}%</p></div>", unsafe_allow_html=True)
    elif verdict == "MISINFORMATION":
        st.markdown(f"<div class='card'><h2>🔴 MISINFORMATION</h2><p>Trust Score: {trust}%</p></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='card'><h2>🟡 UNCERTAIN</h2><p>Trust Score: {trust}%</p></div>", unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ======================================
    # SUMMARY
    # ======================================
    st.markdown("### 📝 AI Summary of Scientific Evidence")
    st.markdown(f"<div class='summary-box'>{res['summary']}</div>", unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ======================================
    # MODEL VOTES
    # ======================================
    st.markdown("### 🗳️ Model Votes (Ensemble)")

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='card'><h3>ML (MNLI)</h3><p>{res['ml_label']}</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><h3>Gemini 2.5 Flash</h3><p>{res['gemini_label']}</p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><h3>Llama 3.1</h3><p>{res['openrouter_label']}</p></div>", unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ======================================
    # EVIDENCE CARDS
    # ======================================
    st.markdown("### 📚 Evidence (SerpAPI + Smart Scraping)")

    evidence = res["evidence"]

    if not evidence:
        st.warning("No evidence found.")
    else:
        for ev in evidence:
            title = ev["title"]
            link = ev["link"]
            snippet = ev["snippet"]

            st.markdown(
                f"""
                <div class="evidence-card">
                    <h4>🔗 <a style="color:#4fcaff" href="{link}" target="_blank">{title}</a></h4>
                    <p>{snippet}</p>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
