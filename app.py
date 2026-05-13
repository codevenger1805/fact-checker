import streamlit as st
import google.generativeai as genai
import httpx
import json

st.set_page_config(
    page_title="FactLayer – AI Fact Checker",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Sora:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Sora', sans-serif; background-color: #0d0d0d; color: #f0f0f0; }
h1, h2, h3 { font-family: 'Space Mono', monospace; }
.stApp { background: #0d0d0d; }
.fact-card { border-radius: 12px; padding: 1.2rem 1.5rem; margin-bottom: 1rem; border-left: 5px solid; }
.verified { border-color: #00e676; background: #0a1f12; }
.inaccurate { border-color: #ffab00; background: #1f1700; }
.false { border-color: #ff1744; background: #1f0008; }
.badge { display: inline-block; padding: 2px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; font-family: 'Space Mono', monospace; margin-bottom: 0.5rem; }
.badge-verified { background: #00e676; color: #000; }
.badge-inaccurate { background: #ffab00; color: #000; }
.badge-false { background: #ff1744; color: #fff; }
.claim-text { font-size: 1rem; font-weight: 600; margin-bottom: 0.4rem; }
.explanation { font-size: 0.88rem; color: #bbb; line-height: 1.6; }
div[data-testid="stFileUploader"] { border: 2px dashed #333; border-radius: 12px; padding: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🔍 FactLayer")
st.markdown("#### Automated Truth Layer for PDF Documents — Powered by AI + Live Web Search")
st.markdown("---")

with st.sidebar:
    st.markdown("### ⚙️ API Keys")
    st.markdown("Paste your keys below. They are never stored.")
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
    serper_key = st.text_input("Serper API Key", type="password", placeholder="your-serper-key")
    st.markdown("---")
    st.markdown("**How it works**")
    st.markdown("1. Upload a PDF\n2. AI reads and pulls out all factual claims\n3. Each claim is searched on the live web\n4. Results flagged as ✅ Verified, ⚠️ Inaccurate, or ❌ False")
    st.markdown("---")
    st.caption("Built for Cog Culture PM Assessment")

uploaded_file = st.file_uploader("📄 Upload a PDF to fact-check", type=["pdf"])


def extract_text_from_pdf(pdf_bytes):
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        return None


def search_web(query, serper_key):
    try:
        response = httpx.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
            json={"q": query, "num": 5},
            timeout=15
        )
        data = response.json()
        snippets = []
        for item in data.get("organic", [])[:4]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            snippets.append(f"{title}: {snippet}")
        return "\n".join(snippets)
    except Exception as e:
        return "No web results found."


def extract_claims(text, gemini_key):
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

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
    raw = response.text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    claims = json.loads(raw)
    return claims


def verify_claim(claim_text, web_results, gemini_key):
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

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
    raw = response.text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    result = json.loads(raw)
    return result


# --- Main App Logic ---
if uploaded_file:
    if not gemini_key or not serper_key:
        st.warning("⚠️ Please enter both API keys in the left sidebar to continue.")
    else:
        pdf_bytes = uploaded_file.read()
        with st.spinner("📖 Reading your PDF..."):
            text = extract_text_from_pdf(pdf_bytes)

        if not text:
            st.error("Could not read the PDF. Make sure it's a text-based PDF, not a scanned image.")
        else:
            st.success(f"✅ PDF read successfully — {len(text)} characters extracted")

            with st.spinner("🤖 AI is identifying factual claims..."):
                try:
                    claims = extract_claims(text, gemini_key)
                except Exception as e:
                    st.error(f"Error extracting claims: {e}")
                    claims = []

            if claims:
                st.markdown(f"### Found **{len(claims)} claims** to verify")
                st.markdown("---")

                verdicts = {"VERIFIED": 0, "INACCURATE": 0, "FALSE": 0}

                for i, item in enumerate(claims):
                    claim_text = item.get("claim", "")
                    with st.spinner(f"🔎 Verifying claim {i+1} of {len(claims)}..."):
                        try:
                            web_results = search_web(claim_text, serper_key)
                            result = verify_claim(claim_text, web_results, gemini_key)
                            verdict = result.get("verdict", "VERIFIED")
                            explanation = result.get("explanation", "")
                            correct_fact = result.get("correct_fact", "")

                            verdicts[verdict] = verdicts.get(verdict, 0) + 1

                            if verdict == "VERIFIED":
                                css_class = "verified"
                                badge_class = "badge-verified"
                                icon = "✅"
                            elif verdict == "INACCURATE":
                                css_class = "inaccurate"
                                badge_class = "badge-inaccurate"
                                icon = "⚠️"
                            else:
                                css_class = "false"
                                badge_class = "badge-false"
                                icon = "❌"

                            correct_html = f'<div style="margin-top:0.5rem; color:#aaa; font-size:0.85rem;">📌 <b>Correct fact:</b> {correct_fact}</div>' if correct_fact else ""

                            st.markdown(f"""
                            <div class="fact-card {css_class}">
                                <span class="badge {badge_class}">{icon} {verdict}</span>
                                <div class="claim-text">"{claim_text}"</div>
                                <div class="explanation">{explanation}</div>
                                {correct_html}
                            </div>
                            """, unsafe_allow_html=True)

                        except Exception as e:
                            st.markdown(f"""
                            <div class="fact-card" style="border-color:#555; background:#111;">
                                <span class="badge" style="background:#555; color:#fff;">⚪ SKIPPED</span>
                                <div class="claim-text">"{claim_text}"</div>
                                <div class="explanation">Could not verify this claim automatically.</div>
                            </div>
                            """, unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("### 📊 Summary")
                col1, col2, col3 = st.columns(3)
                col1.metric("✅ Verified", verdicts.get("VERIFIED", 0))
                col2.metric("⚠️ Inaccurate", verdicts.get("INACCURATE", 0))
                col3.metric("❌ False", verdicts.get("FALSE", 0))
            else:
                st.warning("No specific factual claims were found in this document.")
else:
    st.markdown("""
    <div style="text-align:center; padding: 4rem 2rem; color: #555;">
        <div style="font-size: 4rem;">📄</div>
        <div style="font-size: 1.2rem; margin-top: 1rem;">Upload a PDF above to begin fact-checking</div>
        <div style="font-size: 0.9rem; margin-top: 0.5rem;">Works on marketing reports, research papers, news articles, and more</div>
    </div>
    """, unsafe_allow_html=True)
