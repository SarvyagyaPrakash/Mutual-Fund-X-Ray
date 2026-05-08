# ET MoneyMentor Pro ✨

<p align="center">
  <a href="https://calyx-et-moneymentor.streamlit.app/" target="_blank">
    <img src="https://raw.githubusercontent.com/Naman-GG/Mutual-Fund-X-Ray/main/qr_code.png" alt="QR Code - ET MoneyMentor Pro" width="200" />
  </a>
  <br><br>
  <a href="https://calyx-et-moneymentor.streamlit.app/" target="_blank"><strong><big><big>Click Here To Try The Live App</big></big></strong></a>
</p>

<br>

The model is live and accessible at: **https://calyx-et-moneymentor.streamlit.app/**

ET MoneyMentor Pro is an accessible, highly friendly, and extremely powerful **Open-Source AI Portfolio Mentor** built for the **Economic Times AI Hackathon**. 

It completely abandons the intimidating, hyper-technical "FinTech" aesthetic found in most apps. Instead, it offers a "WhatsApp-style", soft, and genuinely approachable experience for everyday investors. Under the hood, it is powered by a multi-agent **LangGraph** workflow driving Meta's **Llama-3**, backed by real-time high-speed data from **mfapi.in**, and even includes native Voice-to-Portfolio audio transcription powered by **Whisper-Large-v3**!

---

## 🚀 Key Features

*   **🎙️ Voice-To-Portfolio (Whisper V3)**: Users don't even need to type! Simply click the microphone, narrate your investment history naturally (e.g. *"Uh, I bought 50k of SBI Bluechip back in Jan..."*), and Groq's insanely fast Whisper endpoint will transcribe and securely process it. 
*   **🤖 LangGraph Llama-3 Engine**: Replaces proprietary APIs completely. Uses 100% open-source Llama-3-8B (via Groq) to intelligently parse incredibly messy human text or audio into formal mathematical Python data structures.
*   **📡 Real-Time Live Valuations**: Directly integrates with the open-source `mfapi.in` network. When a user provides an investment date, the Analyst Agent literally travels back in time to fetch the exact historical NAV, pulls today's live NAV, and mathematically calculates the True XIRR!
*   **🧸 Ultra-Friendly "Cute" UI**: Built on Quicksand typography, pillowed CSS metric cards, and bubblegum pastel colors (`#B8DB80`, `#F7DB91`, `#FD7979`). It strips away financial anxiety and feels like texting a smart, safe mentor.
*   **💬 Contextual Co-Pilot Chatbot**: After generating your report, you can chat with the AI endlessly below the dashboard without losing your data! The AI strictly operates under legal "Educational Mentor" guardrails, refusing to give explicit investing advice.
*   **🧠 Algorithmic Auto-Corrector**: Employs built-in Python `difflib` semantic auto-correct to instantly catch and repair spelling mistakes in mutual fund names (e.g. converting "Axis Mid" to "Axis Midcap" seamlessly) before querying live APIs.

---

## 🛠️ Local Installation & Setup

Deploying the open-source ET MoneyMentor Pro is incredibly straightforward!

### 1. Clone the Repository
```bash
git clone https://github.com/Naman-GG/Mutual-Fund-X-Ray.git
cd Mutual-Fund-X-Ray
```

### 2. Set Up a Virtual Environment (Highly Recommended)
Isolate your dependencies to avoid interfering with system Python packages.

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Required Dependencies
All underlying packages (`streamlit`, `langgraph`, `casparser`, `requests`, `groq`, etc.) are bundled cleanly.
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
This project utilizes **Groq's LPU** infrastructure for near-instant Llama-3 & Whisper generation.

1. Open your terminal and copy the provided environment template to a functional `.env` file:
   **macOS / Linux:**
   ```bash
   cp .env.example .env
   ```
   **Windows:**
   ```powershell
   copy .env.example .env
   ```

2. Open the new `.env` file and replace the placeholder text with your actual **Groq API Key**:
   *(You can generate a free, lightning-fast key instantly from [GroqCloud Console](https://console.groq.com/keys))*
   ```env
   GROQ_API_KEY="gsk_your_actual_key_here..."
   ```

### 5. Launch the Mentor!
Initialize the Streamlit Server and your dashboard will immediately boot natively in Light Mode.
```bash
streamlit run app.py
```
> The application will automatically bridge to your default web browser at `http://localhost:8501`.

---

## 📜 Development Commit History

The following chronological sequence maps the overarching build process for the ET Hackathon from our initial dark-mode proprietary prototype to our fully open-source, conversational final submission:

* **`feat: initialized project architecture`** 
  * Bootstrapped the initial 3-node LangGraph logic (Extractor, Analyst, Strategist).
* **`chore: pivot from Closed-Source Gemini to Open-Source Llama-3`**
  * Swapped `langchain-google-genai` for `langchain-groq`.
  * Rewrote extraction prompt logic to handle Llama-3's specific parsing semantics.
* **`feat: integrate real-time API (mfapi.in) for true historical NAV lookups`**
  * Ditched the static mock values; the Analyst agent now loops through `investments`, detects `investment_date`, and calculates true portfolio growth mathematically against live market data.
* **`fix: repair Llama-3 Extractor matching hallucination`**
  * Handled Edge Cases where user typing (or Llama-3 output) merged spacings (e.g., "FlexiCap" instead of "Flexi Cap"). Added a resilient standard-library `difflib.get_close_matches` semantic auto-checker.
* **`ui: overhaul aesthetics to 'Cute & Approachable' Custom CSS Light Theme`**
  * Completely removed "Pro-Max Cyber" aesthetics. Implemented `[theme]` inside `.streamlit/config.toml` to force a warm, creamy `#FFFDF8` backdrop.
  * Replaced Fira Code typography with friendly, bubbly `Quicksand`.
  * Injected native deep-Crimson (`#DB1A1A`) ET branding for typography hits, alongside a beautifully preserved Pastel Pie-Chart sequences (`#B8DB80`, `#F7DB91`, `#FD7979`).
* **`feat: engineered the 'Ask Your AI Finance Mentor' contextual chatbot`**
  * Appended a native persistent chat-bot at the bottom of the page.
  * Separated Streamlit render execution into a robust `st.session_state` cache so users can chat without the Streamlit `run_workflow` wiping their dashboard.
  * Bolstered System Prompt Constraints: Enforced strict "Educational-Only" guardrails so the mentor doesn't illegally provide explicit financial buy/sell advice.
* **`feat: mount Whisper-V3 Voice-to-Portfolio recording engine`**
  * Implemented Streamlit's cutting edge `st.audio_input` for zero-friction user narration.
  * Handled dynamic buffer intercept to `.wav` translation, firing off asynchronous transcriptions to `whisper-large-v3` with sub-1-second audio decoding. 
* **`fix: Streamlit Cloud native CSS bypass` (*latest*)**
  * Repaired an issue where `.streamlit/` was ignored by git, depriving the Streamlit server of the Light-Mode CSS sequence.
  * Explicitly embedded the "Made with ❤️ by Team Calyx" watermark signature onto the deployment dashboard directly matching the UI schema!
