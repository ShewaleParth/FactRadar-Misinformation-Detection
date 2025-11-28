import os
import re
import json
import string
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from transformers import pipeline

# =========================================================
# ENV
# =========================================================
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# =========================================================
# FASTAPI
# =========================================================
app = FastAPI()

# =========================================================
# LOAD ML MODEL
# =========================================================
print("Loading MNLI...")
nli_model = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=-1
)
print("MNLI ready.")


# =========================================================
# INPUT FORMAT (Matches app2.py)
# =========================================================
class InputData(BaseModel):
    text: str | None = None
    url: str | None = None


# =========================================================
# HELPERS
# =========================================================
def clean_query(text):
    allowed = string.ascii_letters + string.digits + " -/"
    cleaned = ''.join(c for c in text if c in allowed)
    return " ".join(cleaned.split()[:12])


def extract_claim(text):
    return re.sub(r"\s+", " ", text.strip())[:300]


def extract_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join([p.text.strip() for p in soup.find_all("p")])
    return re.sub(r"\s+", " ", text)[:800]


# =========================================================
# GOOGLE SEARCH (SERPAPI)
# =========================================================
def serpapi_search(query, logs):
    logs.append(f"[SERPAPI] Query: {query}")

    url = "https://serpapi.com/search"
    params = {"engine": "google", "q": query, "api_key": SERPAPI_KEY}

    try:
        r = requests.get(url, params=params)
        data = r.json()
        items = data.get("organic_results", [])
    except Exception as e:
        logs.append(f"[SERPAPI] ERROR: {str(e)}")
        return []

    results = []
    for x in items:
        results.append({
            "title": x.get("title", ""),
            "url": x.get("link", ""),
            "snippet": x.get("snippet", "")
        })

    logs.append(f"[SERPAPI] Retrieved {len(results)} items")
    return results


# =========================================================
# SCRAPER
# =========================================================
def scrape(url, logs):
    logs.append(f"[SCRAPER] Scraping: {url}")

    # Fast direct fetch
    try:
        html = requests.get(url, timeout=4, headers={"User-Agent": "Mozilla/5.0"}).text
        text = extract_visible_text(html)
        if len(text) > 60:
            logs.append("[SCRAPER] Direct OK")
            return text
    except:
        logs.append("[SCRAPER] Direct failed")

    # Fallback: ScrapeNinja
    try:
        r = requests.post("https://scrapeninja.net/api/scrape", json={"url": url}, timeout=7)
        if r.status_code == 200:
            logs.append("[SCRAPER] Ninja OK")
            return extract_visible_text(r.json().get("body", ""))
    except:
        logs.append("[SCRAPER] Ninja failed")

    return ""


# =========================================================
# EVIDENCE RETRIEVAL PIPELINE
# =========================================================
def retrieve_evidence(claim, logs):
    cleaned = clean_query(claim)

    strict = (
        f"\"{cleaned}\" (site:cdc.gov OR site:nih.gov OR site:mayoclinic.org "
        f"OR site:hopkinsmedicine.org OR site:who.int)"
    )

    strict_results = serpapi_search(strict, logs)

    if not strict_results:
        fallback = cleaned + " medical research"
        logs.append("[SEARCH] Using fallback query")
        strict_results = serpapi_search(fallback, logs)

    evidence = []

    for x in strict_results[:3]:
        content = scrape(x["url"], logs)
        snippet = content if content.strip() else x["snippet"]

        evidence.append({
            "title": x["title"],
            "url": x["url"],
            "snippet": snippet
        })

    logs.append(f"[EVIDENCE] Total sources: {len(evidence)}")
    return evidence


# =========================================================
# NLI
# =========================================================
def ml_nli_label(claim, evidence, logs):
    support = 0
    contradict = 0

    for ev in evidence[:2]:
        text = ev["snippet"][:300]

        if len(text) < 20:
            continue

        result = nli_model(
            text,
            candidate_labels=["supports", "contradicts", "unrelated"],
            hypothesis_template=f"This text {{}} the claim: '{claim}'."
        )

        lbl = result["labels"][0]
        score = float(result["scores"][0])

        logs.append(f"[NLI] {lbl} ({score:.2f})")

        if lbl == "supports" and score > 0.35:
            support += score
        elif lbl == "contradicts" and score > 0.35:
            contradict += score

    if contradict > support and contradict > 0.55:
        return "MISINFORMATION"
    if support > contradict and support > 0.55:
        return "REAL"
    return "UNCERTAIN"


# =========================================================
# GEMINI
# =========================================================
def gemini_reasoning(claim, evidence, logs):
    text = "\n".join(ev["snippet"][:350] for ev in evidence)

    prompt = f"""
Fact-check the claim using scientific reasoning.

CLAIM: {claim}

EVIDENCE:
{text}

Rules:
- Strong support → REAL
- Strong contradiction → MISINFORMATION
- Insufficient evidence → UNCERTAIN

Return ONE WORD ONLY.
"""

    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        out = r.json()
        raw = out["candidates"][0]["content"]["parts"][0]["text"].upper()

        logs.append(f"[GEMINI] Raw: {raw}")

        for w in ["REAL", "MISINFORMATION", "UNCERTAIN"]:
            if w in raw:
                return w
    except Exception as e:
        logs.append(f"[GEMINI] ERROR: {str(e)}")

    return "UNCERTAIN"


# =========================================================
# LLAMA
# =========================================================
def llama_reasoning(claim, evidence, logs):
    text = "\n".join(ev["snippet"][:350] for ev in evidence)

    prompt = f"""
CLAIM: {claim}
EVIDENCE:
{text}

Return ONE WORD:
REAL
MISINFORMATION
UNCERTAIN
"""

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

        raw = r.json()["choices"][0]["message"]["content"].upper()
        logs.append(f"[LLAMA] Raw: {raw}")

        for w in ["REAL", "MISINFORMATION", "UNCERTAIN"]:
            if w in raw:
                return w

    except Exception as e:
        logs.append(f"[LLAMA] ERROR: {str(e)}")

    return "UNCERTAIN"


# =========================================================
# ENSEMBLE
# =========================================================
def ensemble(ml, gem, llama, logs):
    votes = [ml, gem, llama]
    logs.append(f"[ENSEMBLE] Votes: {votes}")

    if votes.count("MISINFORMATION") >= 2:
        return "MISINFORMATION"
    if votes.count("REAL") >= 2:
        return "REAL"
    return "UNCERTAIN"


# =========================================================
# ENDPOINT
# =========================================================
@app.post("/detect")
def detect(data: InputData):

    logs = []

    # 1. Extract claim
    claim = extract_claim(data.text or data.url or "")
    logs.append(f"[CLAIM] {claim}")

    # 2. Evidence
    evidence = retrieve_evidence(claim, logs)

    # 3. Models
    ml = ml_nli_label(claim, evidence, logs)
    gem = gemini_reasoning(claim, evidence, logs)

    # Llama skipped if ML is strong
    if ml in ["REAL", "MISINFORMATION"]:
        llama = ml
    else:
        llama = llama_reasoning(claim, evidence, logs)

    # 4. Final
    final = ensemble(ml, gem, llama, logs)
    trust = round((sum([ml == final, gem == final, llama == final]) / 3) * 100)

    # 5. Return
    return {
        "claim": claim,
        "ml_label": ml,
        "gemini_label": gem,
        "llama_label": llama,
        "final_label": final,
        "trust_score": trust,
        "evidence": evidence,
        "logs": logs,
    }
