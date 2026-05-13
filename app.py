import streamlit as st
import httpx
import json
from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="FactLayer – AI Fact Checker",
    page_icon="🔍",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom Styling
# ─────────────────────────────────────────────────────────────────────────────

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

.verified {
    border-color: #00e676;
    background: #061a0e;
}

.inaccurate {
    border-color: #ffab00;
    background: #1a1200;
}

.false {
    border-color: #ff4569;
    background: #1a0009;
}

.skipped {
    border-color: #555555;
    background: #111111;
}

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

.badge-verified {
    background: #00e676;
    color: #000;
}

.badge-inaccurate {
    background: #ffab00;
    color: #000;
}

.badge-false {
    background: #ff4569;
    color: #fff;
}

.badge-skipped {
    background: #555555;
    color: #fff;
}

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

section[data-testid="stSidebar"] {
    background: #111111;
    border-right: 1px solid #222;
}

hr {
    border-color: #222222;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="hero-title">🔍 FactLayer</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="hero-subtitle">Automated Truth Layer for PDF Documents — Powered by AI + Live Web Search</div>',
    unsafe_allow_html=True
)

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ℹ️ How it works")

    st.markdown("""
1. **Upload** any PDF document  
2. **AI extracts** factual claims  
3. Claims are **verified using live web search**  
4. Each claim is classified as:

- ✅ VERIFIED  
- ⚠️ INACCURATE  
- ❌ FALSE  
""")

    st.markdown("---")

    st.caption("Built for Cog Culture PM Assessment · FactLayer v1.0")

# ─────────────────────────────────────────────────────────────────────────────
# Load API Keys
# ─────────────────────────────────────────────────────────────────────────────

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    SERPER_KEY = st.secrets["SERPER_API_KEY"]

except KeyError:
    st.error(
        "🔑 API keys not configured. Please add `GROQ_API_KEY` and `SERPER_API_KEY` to Streamlit Secrets."
    )
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Configure Groq
# ─────────────────────────────────────────────────────────────────────────────

client = Groq(api_key=GROQ_KEY)

# ─────────────────────────────────────────────────────────────────────────────
# PDF Text Extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str | None:
    try:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        text = ""

        for page in doc:
            text += page.get_text()

        return text.strip()

    except Exception:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# Live Web Search
# ─────────────────────────────────────────────────────────────────────────────

def search_web(query: str) -> str:
    try:
        response = httpx.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_KEY,
                "Content-Type": "application/json"
            },
            json={
                "q": query,
                "num": 5
            },
            timeout=15
        )

        data = response.json()

        organic = data.get("organic", [])[:4]

        results = []

        for item in organic:
            title = item.get("title", "")
            snippet = item.get("snippet", "")

            results.append(f"{title}: {snippet}")

        return "\n".join(results)

    except Exception:
        return "No web results found."

# ─────────────────────────────────────────────────────────────────────────────
# Extract Claims
# ─────────────────────────────────────────────────────────────────────────────

def extract_claims(text: str) -> list:

    prompt = f"""
You are a fact-checking assistant.

Read the following document and extract up to 10 specific, verifiable factual claims.

These should include:
- statistics
- dates
- percentages
- factual statements
- company facts
- scientific facts

DO NOT include opinions.

Return ONLY a JSON array like this:

[
  {{"claim": "OpenAI was founded in 2015"}},
  {{"claim": "The global EV market was worth $250 billion in 2022"}}
]

DOCUMENT:
{text[:4000]}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=1000
    )

    raw = response.choices[0].message.content.strip()

    raw = raw.replace("```json", "").replace("```", "").strip()

    return json.loads(raw)

# ─────────────────────────────────────────────────────────────────────────────
# Verify Claims
# ─────────────────────────────────────────────────────────────────────────────

def verify_claim(claim_text: str, web_results: str) -> dict:

    prompt = f"""
You are a professional fact-checker.

CLAIM:
"{claim_text}"

LIVE WEB RESULTS:
{web_results}

Based on the evidence, classify the claim as ONE of:

- VERIFIED
- INACCURATE
- FALSE

Return ONLY valid JSON like this:

{{
    "verdict": "VERIFIED",
    "explanation": "Multiple trusted sources confirm this information.",
    "correct_fact": ""
}}

If the claim is INACCURATE or FALSE,
provide the corrected information in correct_fact.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=600
    )

    raw = response.choices[0].message.content.strip()

    raw = raw.replace("```json", "").replace("```", "").strip()

    return json.loads(raw)

# ─────────────────────────────────────────────────────────────────────────────
# Render Result Cards
# ─────────────────────────────────────────────────────────────────────────────

def render_card(claim_text, verdict, explanation, correct_fact):

    css_map = {
        "VERIFIED": "verified",
        "INACCURATE": "inaccurate",
        "FALSE": "false"
    }

    badge_map = {
        "VERIFIED": "badge-verified",
        "INACCURATE": "badge-inaccurate",
        "FALSE": "badge-false"
    }

    icon_map = {
        "VERIFIED": "✅",
        "INACCURATE": "⚠️",
        "FALSE": "❌"
    }

    css_class = css_map.get(verdict, "skipped")
    badge_class = badge_map.get(verdict, "badge-skipped")
    icon = icon_map.get(verdict, "⚪")

    correct_html = ""

    if correct_fact:
        correct_html = f"""
        <div class="correct-fact">
            📌 <b>Correct fact:</b> {correct_fact}
        </div>
        """

    st.markdown(f"""
    <div class="fact-card {css_class}">
        <span class="badge {badge_class}">
            {icon} {verdict}
        </span>

        <div class="claim-text">
            "{claim_text}"
        </div>

        <div class="explanation">
            {explanation}
        </div>

        {correct_html}
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Skipped Card
# ─────────────────────────────────────────────────────────────────────────────

def render_skipped(claim_text):

    st.markdown(f"""
    <div class="fact-card skipped">

        <span class="badge badge-skipped">
            ⚪ SKIPPED
        </span>

        <div class="claim-text">
            "{claim_text}"
        </div>

        <div class="explanation" style="color:#888;">
            Could not verify this claim automatically.
        </div>

    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    "📄 Upload a PDF to fact-check",
    type=["pdf"]
)

if uploaded_file:

    pdf_bytes = uploaded_file.read()

    with st.spinner("📖 Reading your PDF..."):
        text = extract_text_from_pdf(pdf_bytes)

    if not text:
        st.error(
            "❌ Could not read the PDF. Make sure it's a text-based PDF."
        )
        st.stop()

    st.success(
        f"✅ PDF processed successfully — {len(text):,} characters extracted"
    )

    # ─────────────────────────────────────────────────────────────────────────

    with st.spinner("🤖 AI is extracting factual claims..."):

        try:
            claims = extract_claims(text)

        except Exception as e:
            st.error(f"❌ Error extracting claims: {e}")
            claims = []

    if not claims:
        st.warning("⚠️ No factual claims found.")
        st.stop()

    st.markdown(
        f"### Found **{len(claims)} claims** to verify"
    )

    st.markdown("---")

    verdicts = {
        "VERIFIED": 0,
        "INACCURATE": 0,
        "FALSE": 0
    }

    # ─────────────────────────────────────────────────────────────────────────

    for i, item in enumerate(claims):

        claim_text = item.get("claim", "").strip()

        if not claim_text:
            continue

        with st.spinner(
            f"🔎 Verifying claim {i+1} of {len(claims)}..."
        ):

            try:
                web_results = search_web(claim_text)

                result = verify_claim(
                    claim_text,
                    web_results
                )

                verdict = result.get(
                    "verdict",
                    "VERIFIED"
                ).upper()

                explanation = result.get(
                    "explanation",
                    ""
                )

                correct_fact = result.get(
                    "correct_fact",
                    ""
                )

                if verdict not in verdicts:
                    verdict = "VERIFIED"

                verdicts[verdict] += 1

                render_card(
                    claim_text,
                    verdict,
                    explanation,
                    correct_fact
                )

            except Exception:
                render_skipped(claim_text)

    # ─────────────────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────────────────

    st.markdown("---")

    st.markdown("### 📊 Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "✅ Verified",
        verdicts["VERIFIED"]
    )

    col2.metric(
        "⚠️ Inaccurate",
        verdicts["INACCURATE"]
    )

    col3.metric(
        "❌ False",
        verdicts["FALSE"]
    )

# ─────────────────────────────────────────────────────────────────────────────
# Empty State
# ─────────────────────────────────────────────────────────────────────────────

else:

    st.markdown("""
    <div style="text-align:center; padding: 5rem 2rem; color: #444;">

        <div style="font-size: 4.5rem;">
            📄
        </div>

        <div style="
            font-size: 1.25rem;
            margin-top: 1rem;
            color: #888;
            font-weight: 600;
        ">
            Upload a PDF above to begin fact-checking
        </div>

        <div style="
            font-size: 0.92rem;
            margin-top: 0.6rem;
            color: #555;
        ">
            Works on research papers, reports, articles, and more
        </div>

    </div>
    """, unsafe_allow_html=True)

    </div>
    """, unsafe_allow_html=True)
