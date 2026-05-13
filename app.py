import streamlit as st
import httpx
import json
import google.generativeai as genai

st.set_page_config(
    page_title="FactLayer – AI Fact Checker",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Sora:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
    background-color: #0d0d0d;
    color: #f0f0f0;
}

h1, h2, h3 {
    font-family: 'Space Mono', monospace;
}

.stApp {
    background: #0d0d0d;
}

.hero-title {
    font-family: 'Space Mono', monospace;
    font-size: 3rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -1px;
    margin-bottom: 0.2rem;
}

.hero-subtitle {
    font-size: 1rem;
    color: #aaaaaa;
    margin-bottom: 2rem;
    font-weight: 300;
}

.fact-card {
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
    border-left: 5px solid;
    position: relative;
}

.verified   { border-color: #00e676; background: #061a0e; }
.inaccurate { border-color: #ffab00; background: #1a1200; }
.false      { border-color: #ff4569; background: #1a0009; }
.skipped    { border-color: #555555; background: #111111; }

.badge {
    display: inline-block;
    padding: 3px 14px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
    margin-bottom: 0.6rem;
    letter-spacing: 0.5px;
}

.badge-verified   { background: #00e676; color: #000; }
.badge-inaccurate { background: #ffab00; color: #000; }
.badge-false      { background: #ff4569; color: #fff; }
.badge-skipped    { background: #555555; color: #fff; }

.claim-text {
    font-size: 1.02rem;
    font-weight: 600;
    color: #f5f5f5;
    margin-bottom: 0.5rem;
    line-height: 1.5;
}

.explanation {
    font-size: 0.9rem;
    color: #cccccc;
    line-height: 1.7;
}

.correct-fact {
    margin-top: 0.6rem;
    padding: 0.5rem 0.8rem;
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    font-size: 0.88rem;
    color: #e0e0e0;
    line-height: 1.6;
}

.correct-fact b {
    color: #ffffff;
}

div[data-testid="stFileUploader"] {
    border: 2px dashed #333;
    border-radius: 14px;
    padding: 1.2rem;
    background: #111;
}

div[data-testid="metric-container"] {
    background: #161616;
    border-radius: 12px;
    padding: 1rem;
    border: 1px solid #2a2a2a;
}

div[data-testid="metric-container"] label {
    color: #aaaaaa !important;
    font-size: 0.85rem !important;
}

div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    color: #ffffff !important;
    font-size: 2rem !important;
    font-family: 'Space Mono', monospace !important;
}

.stSpinner > div > div {
    color: #aaaaaa !important;
}

p, li, span {
    color: #e0e0e0;
}

.stMarkdown p {
    color: #e0e0e0;
}

section[data-testid="stSidebar"] {
    background: #111111;
    border-right: 1px solid #222;
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] span {
    color: #cccccc !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
}

div[data-testid="stAlert"] {
    border-radius: 10px;
}

hr {
    border-color: #222222;
}
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">🔍 FactLayer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Automated Truth Layer for PDF Documents — Powered by AI + Live Web Search</div>',
    unsafe_allow_html=True
)
st.markdown("---")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ℹ️ How it works")
    st.markdown("""
1. **Upload** any PDF document  
2. **AI reads** and extracts all verifiable factual claims  
3. Each claim is **searched on the live web**  
4. Claims are flagged as:
   - ✅ **Verified** — confirmed accurate  
   - ⚠️ **Inaccurate** — outdated or partially wrong  
   - ❌ **False** — contradicted or no evidence found  
""")
    st.markdown("---")
    st.caption("Built for Cog Culture PM Assessment · FactLayer v1.0")

# ── Load keys from Streamlit Secrets ─────────────────────────────────────────
try:
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    SERPER_KEY = st.secrets["SERPER_API_KEY"]
except KeyError:
    st.error(
        "🔑 API keys not configured. Please add `GEMINI_API_KEY` and `SERPER_API_KEY` "
        "to your Streamlit Secrets (App Settings → Secrets)."
    )
    st.stop()

# Configure Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# ── Helper functions ──────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str | None:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return "".join(page.get_text() for page in doc).strip() or None
    except Exception:
        return None


def search_web(query: str) -> str:
    try:
        resp = httpx.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 5},
            timeout=15,
        )
        items = resp.json().get("organic", [])[:4]
        return "\n".join(f"{i.get('title','')}: {i.get('snippet','')}" for i in items) or "No web results found."
    except Exception:
        return "No web results found."


def extract_claims(text: str) -> list[dict]:
    prompt = f"""You are a fact-checking assistant. Read the following document and extract up to 10 specific, verifiable factual claims. These should be stats, numbers, dates, named facts, or specific figures — NOT opinions.

Return ONLY a JSON array like this:
[
  {{"claim": "The global EV market was worth $250 billion in 2022"}},
  {{"claim": "OpenAI was founded in 2015"}}
]

Document:
{text[:4000]}

Return only the JSON array, nothing else."""

    response = model.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def verify_claim(claim_text: str, web_results: str) -> dict:
    prompt = f"""You are a fact-checker. A document made the following claim:

CLAIM: "{claim_text}"

Here is what the live web says about this topic:
{web_results}

Based on the web evidence, classify this claim as one of:
- VERIFIED (the web confirms it is accurate)
- INACCURATE (the web shows it is outdated or partially wrong)
- FALSE (the web clearly contradicts it or there is no supporting evidence)

Return ONLY a JSON object like this:
{{"verdict": "VERIFIED", "explanation": "According to multiple sources, this figure is correct as of 2024.", "correct_fact": ""}}

If INACCURATE or FALSE, fill in correct_fact with the right information.
Return only the JSON, nothing else."""

    response = model.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ── Card renderer ─────────────────────────────────────────────────────────────

def render_card(claim_text: str, verdict: str, explanation: str, correct_fact: str):
    css_map   = {"VERIFIED": "verified",   "INACCURATE": "inaccurate",   "FALSE": "false"}
    badge_map = {"VERIFIED": "badge-verified", "INACCURATE": "badge-inaccurate", "FALSE": "badge-false"}
    icon_map  = {"VERIFIED": "✅",          "INACCURATE": "⚠️",           "FALSE": "❌"}

    css_class   = css_map.get(verdict, "skipped")
    badge_class = badge_map.get(verdict, "badge-skipped")
    icon        = icon_map.get(verdict, "⚪")

    correct_html = (
        f'<div class="correct-fact">📌 <b>Correct fact:</b> {correct_fact}</div>'
        if correct_fact else ""
    )

    st.markdown(f"""
    <div class="fact-card {css_class}">
        <span class="badge {badge_class}">{icon} {verdict}</span>
        <div class="claim-text">"{claim_text}"</div>
        <div class="explanation">{explanation}</div>
        {correct_html}
    </div>
    """, unsafe_allow_html=True)


def render_skipped(claim_text: str):
    st.markdown(f"""
    <div class="fact-card skipped">
        <span class="badge badge-skipped">⚪ SKIPPED</span>
        <div class="claim-text">"{claim_text}"</div>
        <div class="explanation" style="color:#888;">Could not verify this claim automatically.</div>
    </div>
    """, unsafe_allow_html=True)


# ── Main app logic ────────────────────────────────────────────────────────────

uploaded_file = st.file_uploader("📄 Upload a PDF to fact-check", type=["pdf"])

if uploaded_file:
    pdf_bytes = uploaded_file.read()

    with st.spinner("📖 Reading your PDF..."):
        text = extract_text_from_pdf(pdf_bytes)

    if not text:
        st.error("❌ Could not read the PDF. Make sure it's a text-based PDF, not a scanned image.")
        st.stop()

    st.success(f"✅ PDF read successfully — {len(text):,} characters extracted")

    with st.spinner("🤖 AI is identifying factual claims..."):
        try:
            claims = extract_claims(text)
        except Exception as e:
            st.error(f"❌ Error extracting claims: {e}")
            claims = []

    if not claims:
        st.warning("⚠️ No specific factual claims were found in this document.")
        st.stop()

    st.markdown(f"### Found **{len(claims)} claim{'s' if len(claims) != 1 else ''}** to verify")
    st.markdown("---")

    verdicts = {"VERIFIED": 0, "INACCURATE": 0, "FALSE": 0}

    for i, item in enumerate(claims):
        claim_text = item.get("claim", "").strip()
        if not claim_text:
            continue

        with st.spinner(f"🔎 Verifying claim {i + 1} of {len(claims)}: *{claim_text[:80]}...*"):
            try:
                web_results  = search_web(claim_text)
                result       = verify_claim(claim_text, web_results)
                verdict      = result.get("verdict", "VERIFIED").upper()
                explanation  = result.get("explanation", "")
                correct_fact = result.get("correct_fact", "")

                if verdict not in verdicts:
                    verdict = "VERIFIED"
                verdicts[verdict] += 1

                render_card(claim_text, verdict, explanation, correct_fact)

            except Exception:
                render_skipped(claim_text)

    # ── Summary ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Verified",    verdicts["VERIFIED"])
    col2.metric("⚠️ Inaccurate", verdicts["INACCURATE"])
    col3.metric("❌ False",       verdicts["FALSE"])

else:
    st.markdown("""
    <div style="text-align:center; padding: 5rem 2rem; color: #444;">
        <div style="font-size: 4.5rem;">📄</div>
        <div style="font-size: 1.25rem; margin-top: 1rem; color: #888; font-weight: 600;">
            Upload a PDF above to begin fact-checking
        </div>
        <div style="font-size: 0.92rem; margin-top: 0.6rem; color: #555;">
            Works on marketing reports, research papers, news articles, and more
        </div>
    </div>
    """, unsafe_allow_html=True)
