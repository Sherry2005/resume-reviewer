# 📄 ResumeAI – Smart Resume Reviewer

An AI-powered resume analysis tool built with **Streamlit**, **Groq**, and **LLaMA 3.3**. Upload your PDF resume and receive a scored review complete with keyword gap analysis, section breakdowns, and line-by-line rewrite suggestions — all in seconds.

🔗 **Live demo → [resume-reviewer.streamlit.app](https://resume-reviewer.streamlit.app)**

---

## ✨ Features

- **Overall + sub-scores** — Overall, ATS, Impact, and Clarity scores rendered as visual rings
- **Strengths analysis** — 3 specific, evidence-backed strengths pulled from your actual resume text
- **Improvement suggestions** — 3 targeted improvements, each with a ready-to-paste rewrite
- **Keyword gap analysis** — Missing vs. present keywords, with job-description-aware matching when a JD is provided
- **Section scores** — Bar-chart breakdown for Experience, Skills, Education, and Formatting
- **Top recommendation** — A single, highest-priority action item
- **Raw JSON view** — Developer-friendly expander to inspect the full AI response

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| UI Framework | [Streamlit](https://streamlit.io) |
| LLM | LLaMA 3.3 70B via [Groq](https://groq.com) |
| PDF Parsing | [pdfplumber](https://github.com/jsvine/pdfplumber) |
| API Client | `groq` Python SDK |
| Hosting | Streamlit Cloud |

---

## ⚙️ How It Works

1. **Upload** a text-based PDF resume (scanned images are not supported)
2. **Optionally paste** a job description for tailored keyword matching
3. **Click Analyze** — the resume text is extracted and sent to Groq's API
4. LLaMA 3.3 returns a **structured JSON response** with scores, strengths, improvements, and keywords
5. Results are rendered across **four tabbed sections** with a visual scoring dashboard

---

## 🚀 Run Locally

### 1. Clone the repo

```bash
git clone https://github.com/Sherry2005/resume-reviewer.git
cd resume-reviewer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your Groq API key

Create a `.streamlit/secrets.toml` file:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
```

Get a free API key at [console.groq.com](https://console.groq.com).

### 4. Run the app

```bash
streamlit run app.py
```

---

## 📁 Project Structure

```
resume-reviewer/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── secrets.toml        # API keys (not committed to git)
└── README.md
```

---

## 📦 Requirements

```
streamlit
pdfplumber
groq
```

---

## 🔒 Privacy

Your resume is sent to Groq's API for analysis only. It is **not stored** by this application. Review [Groq's privacy policy](https://groq.com/privacy-policy/) for details on their data handling.

---

## 🙋 Author

Built by **Sherry Mohareb** — AI Engineer  
[GitHub](https://github.com/Sherry2005) · [LinkedIn](https://linkedin.com/in/sherry-mohareb) · [Upwork](https://upwork.com)
