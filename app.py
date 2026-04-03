import streamlit as st
import pdfplumber
import json
import re
from groq import Groq

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ResumeAI – Smart Resume Reviewer",
    page_icon="📄",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Overall page */
    .main { background-color: #0f1117; }
    [data-testid="stAppViewContainer"] { background: #0f1117; }
    [data-testid="stSidebar"] { background: #16191f; border-right: 1px solid #2a2d35; }

    /* Score ring */
    .score-ring {
        width: 130px; height: 130px;
        border-radius: 50%;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        margin: 0 auto 1.2rem;
        font-family: 'Courier New', monospace;
    }
    .score-num { font-size: 2.6rem; font-weight: 700; line-height: 1; }
    .score-label { font-size: 0.65rem; letter-spacing: 0.15em; opacity: 0.75; margin-top: 2px; }

    /* Cards */
    .card {
        background: #1c1f27;
        border: 1px solid #2a2d35;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
    }
    .card-title {
        font-size: 0.72rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 0.75rem;
    }

    /* Keyword pills */
    .pill-wrap { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
    .pill {
        background: #1e2330;
        border: 1px solid #3a3f52;
        border-radius: 999px;
        padding: 3px 12px;
        font-size: 0.78rem;
        color: #a0a8c0;
    }
    .pill-missing {
        background: #2a1a1a;
        border: 1px solid #6b2e2e;
        color: #f87171;
    }

    /* Strength / improvement items */
    .item { display: flex; gap: 10px; margin-bottom: 0.85rem; align-items: flex-start; }
    .item-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }
    .item-text { font-size: 0.9rem; line-height: 1.55; color: #c9d1e0; }
    .item-evidence { font-size: 0.78rem; color: #6b7280; margin-top: 3px; }
    .rewrite-box {
        background: #111827;
        border-left: 3px solid #3b82f6;
        border-radius: 0 6px 6px 0;
        padding: 8px 12px;
        margin-top: 8px;
        font-size: 0.82rem;
        color: #93c5fd;
        font-family: 'Courier New', monospace;
    }

    /* Section score bar */
    .bar-wrap { background: #111827; border-radius: 999px; height: 6px; margin-top: 6px; }
    .bar-fill { height: 6px; border-radius: 999px; }

    /* Buttons */
    .stButton > button {
        background: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        width: 100% !important;
        padding: 0.65rem !important;
        font-size: 0.95rem !important;
    }
    .stButton > button:hover { background: #2563eb !important; }

    /* Tabs */
    [data-testid="stTabs"] button { color: #6b7280; border-bottom: 2px solid transparent; }
    [data-testid="stTabs"] button[aria-selected="true"] { color: #e2e8f0; border-bottom: 2px solid #3b82f6; }

    /* Spinner */
    [data-testid="stSpinner"] { color: #3b82f6; }

    /* File uploader */
    [data-testid="stFileUploader"] {
        border: 1.5px dashed #2a2d35 !important;
        border-radius: 12px !important;
        background: #16191f !important;
    }

    /* Hide Streamlit default top bar */
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Groq client ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    return Groq(api_key=st.secrets["GROQ_API_KEY"])


# ── PDF extractor ──────────────────────────────────────────────────────────────
def extract_text(uploaded_file) -> str:
    text_parts = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts).strip()


# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior technical recruiter and career coach with 15+ years of experience
reviewing resumes for software engineering, AI/ML, and data science roles.

Analyze the resume (and job description if provided) and return ONLY valid JSON — no markdown,
no explanation, no code fences. Your response must be parseable by json.loads().

Return exactly this structure:
{
  "overall_score": <integer 0-100>,
  "ats_score": <integer 0-100>,
  "impact_score": <integer 0-100>,
  "clarity_score": <integer 0-100>,
  "one_liner": "<one punchy sentence summarizing the resume's biggest opportunity>",
  "strengths": [
    {
      "point": "<strength title>",
      "evidence": "<specific quote or example from the resume>"
    }
  ],
  "improvements": [
    {
      "point": "<what to improve>",
      "evidence": "<specific weak line or section from the resume>",
      "rewrite": "<a rewritten version of that line, ready to paste>"
    }
  ],
  "keyword_gaps": ["<missing keyword 1>", "<missing keyword 2>", ...],
  "present_keywords": ["<found keyword 1>", "<found keyword 2>", ...],
  "section_scores": {
    "experience": <0-100>,
    "skills": <0-100>,
    "education": <0-100>,
    "formatting": <0-100>
  },
  "top_recommendation": "<the single most important thing to do right now>"
}

Rules:
- strengths: exactly 3 items
- improvements: exactly 3 items, each with a ready-to-paste rewrite
- keyword_gaps: 5–10 items (keywords from the job description missing in the resume; if no JD provided, use common industry keywords)
- present_keywords: 6–12 keywords already in the resume
- Be specific. Quote actual lines. No vague feedback.
"""


# ── Groq call ──────────────────────────────────────────────────────────────────
def review_resume(resume_text: str, job_desc: str = "") -> dict:
    client = get_client()

    user_msg = f"RESUME:\n{resume_text}"
    if job_desc.strip():
        user_msg += f"\n\nJOB DESCRIPTION:\n{job_desc}"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=1800,
    )

    raw = response.choices[0].message.content.strip()

    # Strip any accidental markdown code fences
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    return json.loads(raw)


# ── Score ring helper ──────────────────────────────────────────────────────────
def score_color(score: int) -> tuple[str, str]:
    """Returns (ring_border_color, text_color) based on score."""
    if score >= 80:
        return "#22c55e", "#4ade80"   # green
    elif score >= 60:
        return "#f59e0b", "#fbbf24"   # amber
    else:
        return "#ef4444", "#f87171"   # red


def render_score_ring(score: int, label: str):
    border, color = score_color(score)
    st.markdown(f"""
    <div class="score-ring" style="border: 5px solid {border};">
        <span class="score-num" style="color:{color};">{score}</span>
        <span class="score-label" style="color:{color};">{label}</span>
    </div>
    """, unsafe_allow_html=True)


def render_bar(score: int, label: str):
    border, color = score_color(score)
    st.markdown(f"""
    <div style="margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;font-size:0.8rem;color:#9ca3af;">
        <span>{label}</span><span style="color:{color};">{score}</span>
      </div>
      <div class="bar-wrap">
        <div class="bar-fill" style="width:{score}%;background:{border};"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Main UI ────────────────────────────────────────────────────────────────────
def main():
    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style='padding:1rem 0 1.5rem;'>
          <div style='font-size:1.3rem;font-weight:700;color:#e2e8f0;letter-spacing:-0.5px;'>
            📄 ResumeAI
          </div>
          <div style='font-size:0.78rem;color:#6b7280;margin-top:4px;'>
            AI-powered resume analysis
          </div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Upload your resume (PDF)",
            type=["pdf"],
            help="Max 10MB. Text-based PDFs only (not scanned images).",
        )

        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        job_desc = st.text_area(
            "Job description (optional but recommended)",
            height=180,
            placeholder="Paste the job posting here to get keyword gap analysis and tailored feedback…",
        )

        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        analyze_btn = st.button("🔍  Analyze Resume")

        st.markdown("""
        <div style='margin-top:2rem;padding-top:1.5rem;border-top:1px solid #2a2d35;
                    font-size:0.75rem;color:#4b5563;line-height:1.7;'>
          <b style='color:#6b7280;'>How it works</b><br>
          1. Upload your PDF<br>
          2. Optionally paste a job description<br>
          3. Get a scored review with rewrites<br><br>
          <b style='color:#6b7280;'>Privacy</b><br>
          Your resume is sent to Groq's API for analysis and is not stored.
        </div>
        """, unsafe_allow_html=True)

    # ── Main area ──────────────────────────────────────────────────────────────
    if not uploaded_file and not st.session_state.get("result"):
        # Landing state
        st.markdown("""
        <div style='text-align:center;padding:5rem 1rem 2rem;'>
          <div style='font-size:3rem;margin-bottom:1rem;'>📄</div>
          <h1 style='font-size:2rem;font-weight:700;color:#e2e8f0;letter-spacing:-0.5px;margin-bottom:0.5rem;'>
            AI Resume Reviewer
          </h1>
          <p style='color:#6b7280;font-size:1rem;max-width:480px;margin:0 auto;line-height:1.7;'>
            Upload your PDF resume and get a detailed score, keyword gap analysis,
            and line-by-line rewrite suggestions — powered by Groq + LLaMA 3.3.
          </p>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        for col, icon, title, desc in [
            (c1, "🎯", "ATS Score", "See how well your resume passes automated filters"),
            (c2, "✍️", "Line Rewrites", "Get ready-to-paste improved versions of weak lines"),
            (c3, "🔑", "Keyword Gaps", "Discover missing keywords from the job description"),
        ]:
            with col:
                st.markdown(f"""
                <div class="card" style="text-align:center;">
                  <div style="font-size:1.8rem;margin-bottom:0.5rem;">{icon}</div>
                  <div style="font-weight:600;color:#e2e8f0;margin-bottom:0.3rem;">{title}</div>
                  <div style="font-size:0.82rem;color:#6b7280;line-height:1.6;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)
        return

    # ── Run analysis ───────────────────────────────────────────────────────────
    if analyze_btn and uploaded_file:
        with st.spinner("Analyzing your resume with LLaMA 3.3…"):
            try:
                resume_text = extract_text(uploaded_file)
                if len(resume_text) < 100:
                    st.error("Could not extract enough text. Make sure your PDF is text-based (not a scanned image).")
                    return
                result = review_resume(resume_text, job_desc)
                st.session_state["result"] = result
                st.session_state["filename"] = uploaded_file.name
            except json.JSONDecodeError:
                st.error("The AI returned an unexpected format. Please try again.")
                return
            except Exception as e:
                st.error(f"Error: {e}")
                return

    # ── Display results ────────────────────────────────────────────────────────
    result = st.session_state.get("result")
    if not result:
        return

    fname = st.session_state.get("filename", "your resume")

    # Header
    st.markdown(f"""
    <div style='padding:1.5rem 0 0.5rem;'>
      <div style='font-size:0.75rem;color:#6b7280;letter-spacing:0.1em;text-transform:uppercase;
                  margin-bottom:4px;'>Analysis complete</div>
      <h2 style='font-size:1.5rem;font-weight:700;color:#e2e8f0;margin:0;'>{fname}</h2>
      <p style='color:#9ca3af;font-size:0.9rem;margin-top:6px;font-style:italic;'>
        "{result.get('one_liner', '')}"
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Score row
    col_o, col_a, col_i, col_c = st.columns(4)
    with col_o:
        render_score_ring(result["overall_score"], "OVERALL")
    with col_a:
        render_score_ring(result["ats_score"], "ATS")
    with col_i:
        render_score_ring(result["impact_score"], "IMPACT")
    with col_c:
        render_score_ring(result["clarity_score"], "CLARITY")

    st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)

    # Top recommendation banner
    top_rec = result.get("top_recommendation", "")
    if top_rec:
        st.markdown(f"""
        <div style='background:#1e2d3d;border:1px solid #1d4ed8;border-radius:10px;
                    padding:1rem 1.25rem;margin-bottom:1.5rem;display:flex;gap:12px;align-items:flex-start;'>
          <span style='font-size:1.1rem;'>💡</span>
          <div>
            <div style='font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;
                        color:#60a5fa;margin-bottom:4px;'>Top recommendation</div>
            <div style='color:#bfdbfe;font-size:0.9rem;line-height:1.6;'>{top_rec}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "  💪 Strengths  ",
        "  🔧 Improvements  ",
        "  🔑 Keywords  ",
        "  📊 Section Scores  ",
    ])

    # ── Tab 1: Strengths ───────────────────────────────────────────────────────
    with tab1:
        st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
        for item in result.get("strengths", []):
            st.markdown(f"""
            <div class="card">
              <div class="item">
                <div class="item-dot" style="background:#22c55e;margin-top:6px;"></div>
                <div>
                  <div class="item-text" style="font-weight:600;color:#e2e8f0;">{item['point']}</div>
                  <div class="item-evidence">{item['evidence']}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tab 2: Improvements ───────────────────────────────────────────────────
    with tab2:
        st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
        for item in result.get("improvements", []):
            st.markdown(f"""
            <div class="card">
              <div class="item">
                <div class="item-dot" style="background:#ef4444;margin-top:6px;"></div>
                <div style="width:100%;">
                  <div class="item-text" style="font-weight:600;color:#e2e8f0;">{item['point']}</div>
                  <div class="item-evidence" style="margin-top:4px;">Current: <em>{item['evidence']}</em></div>
                  <div class="rewrite-box">✏️ Rewrite: {item['rewrite']}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tab 3: Keywords ───────────────────────────────────────────────────────
    with tab3:
        st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

        col_k1, col_k2 = st.columns(2)
        with col_k1:
            st.markdown("""
            <div class="card">
              <div class="card-title">✅ Keywords present</div>
              <div class="pill-wrap">
            """ + "".join(
                f'<span class="pill">{k}</span>'
                for k in result.get("present_keywords", [])
            ) + """
              </div>
            </div>
            """, unsafe_allow_html=True)

        with col_k2:
            st.markdown("""
            <div class="card">
              <div class="card-title">❌ Keywords missing</div>
              <div class="pill-wrap">
            """ + "".join(
                f'<span class="pill pill-missing">{k}</span>'
                for k in result.get("keyword_gaps", [])
            ) + """
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tab 4: Section scores ─────────────────────────────────────────────────
    with tab4:
        st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
        section_scores = result.get("section_scores", {})
        labels = {
            "experience": "Work Experience",
            "skills": "Skills Section",
            "education": "Education",
            "formatting": "Formatting & Readability",
        }
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for key, label in labels.items():
            score = section_scores.get(key, 0)
            render_bar(score, label)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Raw JSON expander (for learning / debugging) ───────────────────────────
    with st.expander("🔬 Raw JSON response (for developers)"):
        st.json(result)


if __name__ == "__main__":
    main()
