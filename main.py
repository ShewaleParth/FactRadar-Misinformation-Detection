import os
import re
import json
import string
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from transformers import pipeline

# ============================================================
# LOAD ENV
# ============================================================
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = FastAPI()

# ============================================================
# LOAD NLI (FAST MODE)
# ============================================================
print("Loading MNLI model...")
nli_model = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=-1
)
print("MNLI ready.")


# ============================================================
# INPUT MODEL
# ============================================================
class InputData(BaseModel):
    url: str


# ============================================================
# HELPERS
# ============================================================
def clean_query(text):
    allowed = string.ascii_letters + string.digits + " -/"
    return " ".join("".join(c for c in text if c in allowed).split()[:12])


def extract_claim(text):
    return re.sub(r"\s+", " ", text.strip())[:300]


# ============================================================
# SERPAPI SEARCH
# ============================================================
def serpapi_search(query):
    url = "https://serpapi.com/search"
    params = {"engine": "google", "q": query, "api_key": SERPAPI_KEY}
    try:
        r = requests.get(url, params=params)
        data = r.json()

        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })
        return results

    except Exception as e:
        print("SerpAPI error:", e)
        return []


# ============================================================
# SCRAPING
# ============================================================
def extract_visible_text(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        text = " ".join(p.text.strip() for p in soup.find_all("p"))
        return re.sub(r"\s+", " ", text)[:800]
    except:
        return ""


def scrape_page(url):
    print("SCRAPING:", url)

    try:
        html = requests.get(url, timeout=4, headers={"User-Agent": "Mozilla/5.0"}).text
        txt = extract_visible_text(html)
        if len(txt) > 60:
            return txt
    except:
        pass

    try:
        r = requests.post("https://scrapeninja.net/api/scrape", json={"url": url}, timeout=7)
        if r.status_code == 200:
            html = r.json().get("body", "")
            return extract_visible_text(html)
    except:
        pass

    return ""


# ============================================================
# EVIDENCE RETRIEVAL
# ============================================================
def retrieve_evidence(claim):
    cleaned = clean_query(claim)

    strict = (
        f"\"{cleaned}\" (site:cdc.gov OR site:who.int OR site:nih.gov "
        f"OR site:mayoclinic.org OR site:hopkinsmedicine.org OR site:yalemedicine.org)"
    )

    items = serpapi_search(strict)

    if not items:
        fallback = cleaned + " medical research verified"
        items = serpapi_search(fallback)

    evidence = []

    for it in items[:3]:
        title = it.get("title", "")
        link = it.get("link", "")
        snippet = it.get("snippet", "")

        scraped = scrape_page(link)
        final_snippet = scraped[:600] if scraped.strip() else snippet

        evidence.append({
            "title": title,
            "link": link,
            "snippet": final_snippet
        })

    return evidence


# ============================================================
# NLI CLASSIFICATION
# ============================================================
def ml_nli_label(claim, evidence):
    support = 0.0
    contra = 0.0

    for ev in evidence[:2]:
        snippet = ev["snippet"][:300]
        if len(snippet) < 30:
            continue

        result = nli_model(
            snippet,
            candidate_labels=["supports", "contradicts", "unrelated"],
            hypothesis_template=f"This text {{}} the claim: '{claim}'."
        )

        lbl = result["labels"][0]
        score = float(result["scores"][0])

        if score > 0.35:
            if lbl == "supports":
                support += score
            elif lbl == "contradicts":
                contra += score

    if contra > support and contra > 0.5:
        return "MISINFORMATION"
    if support > contra and support > 0.5:
        return "REAL"
    return "UNCERTAIN"


# ============================================================
# GEMINI REASONING
# ============================================================
def gemini_reasoning(claim, evidence):
    text = "\n".join(ev["snippet"][:350] for ev in evidence)

    prompt = f"""
Scientific fact-check the following:

CLAIM: {claim}

EVIDENCE:
{text if text else "NO EVIDENCE"}

Output one word:
REAL
MISINFORMATION
UNCERTAIN
"""

    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].upper()

        for w in ["REAL", "MISINFORMATION", "UNCERTAIN"]:
            if w in txt:
                return w
    except:
        pass

    return "UNCERTAIN"


# ============================================================
# GEMINI SUMMARY GENERATOR
# ============================================================
def generate_summary(claim, evidence):
    text = "\n".join(ev["snippet"][:400] for ev in evidence)

    prompt = f"""
Summarize the scientific evidence in 3–5 sentences.

CLAIM: {claim}

EVIDENCE:
{text if text else "NO EVIDENCE"}

Your summary must:
- Be scientific and neutral
- Explain what the evidence suggests
- Avoid giving verdict labels
"""

    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )

        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "No summary available."


# ============================================================
# LLAMA (ONLY IF NEEDED)
# ============================================================
def llama_reasoning(claim, evidence):
    text = "\n".join(ev["snippet"][:350] for ev in evidence)

    prompt = f"""
CLAIM: {claim}
EVIDENCE:
{text}

One word:
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
        txt = r.json()["choices"][0]["message"]["content"].upper()

        for w in ["REAL", "MISINFORMATION", "UNCERTAIN"]:
            if w in txt:
                return w
    except:
        pass

    return "UNCERTAIN"


# ============================================================
# ENSEMBLE DECISION
# ============================================================
def ensemble(ml, gem, llama):
    votes = [ml, gem, llama]

    if votes.count("MISINFORMATION") >= 2:
        return "MISINFORMATION"
    if votes.count("REAL") >= 2:
        return "REAL"
    return "UNCERTAIN"


# ============================================================
# MAIN ENDPOINT
# ============================================================
@app.post("/detect")
def detect(data: InputData):

    claim = extract_claim(data.url)
    evidence = retrieve_evidence(claim)

    ml = ml_nli_label(claim, evidence)
    gem = gemini_reasoning(claim, evidence)

    if ml == gem:
        llama = ml
    else:
        llama = llama_reasoning(claim, evidence)

    final = ensemble(ml, gem, llama)
    trust = round((sum([ml == final, gem == final, llama == final]) / 3) * 100)

    summary = generate_summary(claim, evidence)

    return {
        "claim": claim,
        "ml_label": ml,
        "gemini_label": gem,
        "openrouter_label": llama,
        "final_label": final,
        "trust_score": trust,
        "evidence": evidence,
        "summary": summary
    }
