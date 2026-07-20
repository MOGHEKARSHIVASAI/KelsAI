# 🎯 KelsAI — Your AI Job Search Copilot

KelsAI is an advanced, automated AI agent designed to supercharge your job search process. It automatically scrapes multiple job boards, intelligently scores jobs against your specific resume using semantic embeddings, and tracks your entire application pipeline in a centralized, professional dashboard. 

## ✨ Features

- **🚀 Parallel Job Scraping**: Concurrently scrapes 10+ job platforms including LinkedIn, Internshala, AngelList, Instahyre, Himalayas, Remotive, and more.
- **⚡ Smart AI Matching**: Uses `SentenceTransformers` to locally generate semantic embeddings for jobs, and strictly queries the Gemini/OpenRouter API only for highly relevant matches to provide concise match summaries.
- **📝 Automated Cover Letters**: Generates highly personalized, 3-paragraph cover letters tailored specifically to the company and job description you're applying for.
- **🎯 Skill Gap Analyzer**: Compares your resume with high-matching job descriptions to identify missing skills and provides official documentation and tutorial links to bridge the gap.
- **⏰ Background Automation**: Set a daily schedule to automatically hunt for jobs in the background and receive a summarized HTML email digest of your top matches.
- **📊 Analytics Dashboard**: Track your application funnel (Found ➔ Saved ➔ Applied ➔ Interview ➔ Offered) with beautiful, interactive visualizations.
- **⏱️ CRM History Timeline**: Every action you take on a job is time-stamped and logged, giving you a clear history of your interaction with that company.

---

## 🛠 Prerequisites

- Python 3.10+
- An API Key from [Google Gemini](https://aistudio.google.com/app/apikey) or [OpenRouter](https://openrouter.ai/)

---

## 🚀 Installation & Setup

**1. Clone the repository:**
```bash
git clone https://github.com/MOGHEKARSHIVASAI/KelsAI.git
cd KelsAI
```

**2. Create and activate a virtual environment:**
```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Set up Environment Variables:**
Create a `.env` file in the root directory and add your API keys:
```ini
GEMINI_API_KEY="your_gemini_api_key_here"
# Optional, if using OpenRouter
OPENROUTER_API_KEY="your_openrouter_api_key_here"
```

---

## 💻 Running the App

Start the Streamlit application:
```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`. 

---

## 📖 How to Use KelsAI

1. **Set Up Profile**: Navigate to the **📄 My Profile** tab and upload your resume (PDF) or paste your LinkedIn URL. The AI will parse your experience and skills.
2. **Configure Preferences**: Go to **⚙️ Preferences** to define your desired job titles, keywords, location, and remote preferences.
3. **Start Job Hunt**: Navigate to **🔍 Job Hunt** and click "Start Job Hunt". The agent will scrape sources in parallel, score the jobs against your profile, and surface the strongest matches.
4. **Manage Applications**: Use the **📋 Applications** tab to update the status of jobs (Saved, Applied, Interviewing, Offered). 
5. **Generate Assets**: Use the **📝 Cover Letters** and **🎯 Skill Gap** tabs for selected jobs to generate application materials and prepare for interviews.
6. **Set Schedule**: Visit the **⏰ Scheduler** to turn on auto-hunts and daily email digests.

---

## 🧰 Tech Stack
- **Frontend**: Streamlit, Plotly, HTML/CSS
- **Backend/Agents**: Python 3, Concurrent Futures (Threading), BeautifulSoup4, Feedparser
- **AI/ML**: `google-genai` (Gemini), `sentence-transformers` (Local Embeddings)
- **Database**: SQLite3
- **Automation**: APScheduler, macOS `osascript`

---
*Built with AI by Antigravity*
