import os
import re
import json
import string
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from transformers import pipeline
from concurrent.futures import ThreadPoolExecutor

# ============================================================
# LOAD ENV
# ============================================================
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ============================================================
# FASTAPI APP + CORS FIX  (Fixes OPTIONS 405)
# ============================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # or specific URL
    allow_credentials=True,
    allow_methods=["*"],          # fixes OPTIONS preflight
    allow_headers=["*"],
)

# ============================================================
# LOAD NLI MODEL (RUN SYNC USING EXECUTOR)
# ============================================================
print("Loading MNLI model...")
nli_model = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
)
executor = ThreadPoolExecutor(max_workers=4)
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
# ASYNC SERPAPI SEARCH
# ============================================================
async def serpapi_search(query):
    url = "https://serpapi.com/search"
    params = {"engine": "google", "q": query, "api_key": SERPAPI_KEY}

    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(url, params=params) as r:
                data = await r.json()

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
# SCRAPING (ASYNC)
# ============================================================
def extract_visible_text(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        text = " ".join(p.text.strip() for p in soup.find_all("p"))
        return re.sub(r"\s+", " ", text)[:800]
    except:
        return ""


async def scrape_page(url):

    # First try direct fetch
    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(
                url,
                timeout=6,
                headers={"User-Agent": "Mozilla/5.0"}
            ) as r:
                html = await r.text()
                txt = extract_visible_text(html)
                if len(txt) > 60:
                    return txt
    except:
        pass

    # Fallback to Scrapeninja
    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                "https://scrapeninja.net/api/scrape",
                json={"url": url},
                timeout=8
            ) as r:
                if r.status == 200:
                    html = (await r.json()).get("body", "")
                    return extract_visible_text(html)
    except:
        pass

    return ""


# ============================================================
# EVIDENCE RETRIEVAL
# ============================================================
async def retrieve_evidence(claim):
    cleaned = clean_query(claim)

    strict = (
        f"\"{cleaned}\" (site:cdc.gov OR site:who.int OR site:nih.gov "
        f"OR site:mayoclinic.org OR site:hopkinsmedicine.org OR site:yalemedicine.org)"
    )

    items = await serpapi_search(strict)

    if not items:
        fallback = cleaned + " medical research verified"
        items = await serpapi_search(fallback)

    evidence = []

    for it in items[:3]:
        link = it.get("link", "")
        scraped = await scrape_page(link)
        final_snippet = scraped[:600] if scraped.strip() else it.get("snippet", "")

        evidence.append({
            "title": it.get("title", ""),
            "link": link,
            "snippet": final_snippet
        })

    return evidence


# ============================================================
# ASYNC NLI MODEL EXECUTION (RUN IN EXECUTOR)
# ============================================================
async def ml_nli_label(claim, evidence):
    support = 0.0
    contra = 0.0

    loop = asyncio.get_event_loop()

    for ev in evidence[:2]:
        snippet = ev["snippet"][:300]
        if len(snippet) < 30:
            continue

        result = await loop.run_in_executor(
            executor,
            lambda: nli_model(
                snippet,
                candidate_labels=["supports", "contradicts", "unrelated"],
                hypothesis_template=f"This text {{}} the claim: '{claim}'."
            )
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
# GEMINI (ASYNC)
# ============================================================
async def gemini_reasoning(claim, evidence):

    text = "\n".join(ev["snippet"][:350] for ev in evidence)
    prompt = f"""
CLAIM: {claim}

EVIDENCE:
{text}

Return only one word:
REAL
MISINFORMATION
UNCERTAIN
"""

    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]}
            ) as r:
                data = await r.json()
                txt = data["candidates"][0]["content"]["parts"][0]["text"].upper()

                for w in ["REAL", "MISINFORMATION", "UNCERTAIN"]:
                    if w in txt:
                        return w
    except:
        pass

    return "UNCERTAIN"


# ============================================================
# SUMMARY GENERATION
# ============================================================
async def generate_summary(claim, evidence):
    text = "\n".join(ev["snippet"][:400] for ev in evidence)

    prompt = f"""
Summarize the evidence in 3–5 scientific sentences.

CLAIM: {claim}

EVIDENCE:
{text}
"""

    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]}
            ) as r:
                data = await r.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "No summary available."


# ============================================================
# LLAMA REASONING
# ============================================================
async def llama_reasoning(claim, evidence):

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
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                json={
                    "model": "meta-llama/llama-3.1-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}]
                }
            ) as r:
                data = await r.json()
                txt = data["choices"][0]["message"]["content"].upper()

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
async def detect(data: InputData):

    claim = extract_claim(data.url)
    evidence = await retrieve_evidence(claim)

    ml = await ml_nli_label(claim, evidence)
    gem = await gemini_reasoning(claim, evidence)

    llama = ml if ml == gem else await llama_reasoning(claim, evidence)

    final = ensemble(ml, gem, llama)
    trust = round((sum([ml == final, gem == final, llama == final]) / 3) * 100)

    summary = await generate_summary(claim, evidence)

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


# ============================================================
# UVICORN RUNNER
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
