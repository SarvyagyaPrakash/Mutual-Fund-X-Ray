import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from workflow import build_workflow
from agents import run_chat_assistant
from schema import PortfolioState
import os
from groq import Groq

load_dotenv(override=True)

# SVG Icons remapped to Pastel Cute Palette
SVG_WARN = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FD7979" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 8px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
SVG_CHECK = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#B8DB80" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 8px;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
SVG_INFO = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F7DB91" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 8px;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'

st.set_page_config(page_title="ET MoneyMentor Pro", layout="wide", page_icon="💸")

# Cute Design System: Bubbly fonts, Pastel vectors, thick rounds, joyful gradients
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');
    
    /* Apply Quicksand via top-level inheritance only to avoid breaking Streamlit's internal SVG/ligature icon engine */
    html, body, .stApp, .stMarkdown, h1, h2, h3, h4, h5, h6, p, div[data-testid="stText"] {
        font-family: 'Quicksand', sans-serif;
    }
    
    .stApp {
        background-color: #FFFDF8;
    }
    
    .main-header {
        background: -webkit-linear-gradient(45deg, #DB1A1A, #DB1A1A);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.5rem;
        margin-bottom: 0px;
        letter-spacing: -1px;
    }
    .sub-header {
        color: #475569;
        font-weight: 600;
        margin-bottom: 2rem;
    }
    .metric-container {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #FFFFFF;
        border: 2px solid #FDF4EB;
        border-top: 6px solid #DB1A1A;
        border-radius: 28px;
        padding: 1.8rem;
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        box-shadow: 0 10px 24px rgba(0,0,0,0.04);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        cursor: pointer;
    }
    .metric-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 16px 36px rgba(205,44,88,0.12);
        border: 2px solid #F7DB91;
        border-top: 6px solid #F7DB91;
    }
    .metric-title {
        color: #64748B;
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    .metric-value-score, .metric-value-money, .metric-value-savings {
        font-size: 3rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .metric-value-score { color: #DB1A1A; } /* ET Crimson */
    .metric-value-money { color: #FD7979; } /* Coral */
    .metric-value-savings { color: #B8DB80; } /* Matcha green */
    
    .metric-subtitle {
        color: #94A3B8;
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    
    .svg-container {
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem;
        color: #475569;
        font-weight: 600;
    }
    
    /* Tweaking generic streamlit text slightly for cute visibility against cream back */
    h2, h3, h4, p {
        color: #334155;
    }
    
    /* Bubble Feedback Box */
    .feedback-bubble {
        background: #FFFFFF;
        border: 2px solid #F7DB91;
        box-shadow: 0 8px 16px rgba(247,219,145,0.2);
        padding: 1.5rem;
        border-radius: 24px;
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>ET MoneyMentor Pro ✨</h1>", unsafe_allow_html=True)
st.markdown("<h3 class='sub-header'>A friendly place for your financial peace of mind.</h3>", unsafe_allow_html=True)

st.write("Welcome! This safe, secure tool gently analyzes your statements or texts to build a friendly, strictly directional plan for your financial journey.")

tab1, tab2 = st.tabs(["Paste Text Input", "Upload CAS PDF"])

run_workflow = False
initial_state = {"raw_input": "", "pdf_bytes": None, "pdf_password": None, "investments": [], "errors": [], "log": [], "transactions": []}

with tab2:
    st.markdown(f"<div class='svg-container'>{SVG_INFO} <span>Securely hand over your CAMS or KFintech CAS PDF. We'll handle the math!</span></div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload Statement Archive (.pdf)", type=["pdf"], label_visibility="collapsed")
    pdf_password = st.text_input("Decrypt Key (PAN Hash)", type="password")
    if st.button("Initialize PDF Protocol"):
        if uploaded_file and pdf_password:
            initial_state["pdf_bytes"] = uploaded_file.getvalue()
            initial_state["pdf_password"] = pdf_password
            run_workflow = True
        else:
            st.error("Authentication halted: File and Key required.")

with tab1:
    MOCK_TEXT = "I invested ₹100,000 in UTI Mastershare on 15-01-2023, ₹75,000 in UTI Flexi Cap on 10-06-2023, and ₹30,000 in Axis Midcap on 01-12-2023 and Rs 20000 in Tata Smallcap on 01-12-2024"
    if "input_text_val" not in st.session_state:
        st.session_state.input_text_val = MOCK_TEXT
        
    st.markdown("<h4 style='color:#334155; margin-bottom: 0px;'>🎙️ Voice-To-Portfolio</h4>", unsafe_allow_html=True)
    audio_file = st.audio_input("Speak out your portfolio investments openly!", label_visibility="collapsed")
    
    if audio_file is not None:
        audio_bytes_len = len(audio_file.getvalue())
        if st.session_state.get("last_audio_id") != audio_bytes_len:
            with st.spinner("Processing Voice with Whisper-Large-V3..."):
                client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                transcription = client.audio.transcriptions.create(
                    file=("recorded.wav", audio_file.getvalue()),
                    model="whisper-large-v3",
                    response_format="text"
                )
                st.session_state.input_text_val = transcription
                st.session_state.last_audio_id = audio_bytes_len
                st.rerun()
                
    st.markdown("<br><h4 style='color:#334155; margin-bottom: 0px;'>✍️ Or Type Manually</h4>", unsafe_allow_html=True)
    raw_input = st.text_area("Tell us about your investments:", value=st.session_state.input_text_val, height=100, label_visibility="collapsed")
    
    # Store user edit buffer if they manually type over the transcription
    st.session_state.input_text_val = raw_input
    
    if st.button("Review My Portfolio"):
        if raw_input:
            initial_state["raw_input"] = raw_input
            run_workflow = True

if "analysis_state" not in st.session_state:
    st.session_state.analysis_state = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [{"role": "assistant", "content": "Hi! I'm your Finance Mentor.🤑 Do you have any questions about your XIRR, overlaps, or general finance concepts? I'm here to help!"}]

if run_workflow:
    workflow_app = build_workflow()
    
    with st.status("Analyzing your portfolio..."):
        with st.expander("System Diagnostic Logs", expanded=True):
            st.info("Llama-3 Open-Source Engine Active. Tracking logic pathways...")
            final_state = workflow_app.invoke(initial_state)
            
            for log_entry in final_state.get('log', []):
                parts = log_entry.split(':', 1)
                if len(parts) == 2:
                    st.write(f"**{parts[0]}**:{parts[1]}")
                else:
                    st.write(f"{log_entry}")
                    
    if final_state and not final_state.get('errors', []):
        st.session_state.analysis_state = final_state
        # Reset chat history on new query so the context doesn't clash
        st.session_state.chat_messages = [{"role": "assistant", "content": "Hi! I'm your Finance Mentor. 🤑 Do you have any questions about your XIRR, overlaps, or general finance concepts? I'm here to help!"}]
    else:
        st.error("Analysis hit an error. Please review the logs.")

# Render Dashboard fully independently out of Session State!
if st.session_state.analysis_state:
    st.success("Hooray! Portfolio Check Complete.")
    final_state = st.session_state.analysis_state
    
    analysis = final_state['analysis']
    strategy = final_state['strategy']
    
    xirr_display = f"{analysis.portfolio_xirr:,.2f}%" if analysis.portfolio_xirr is not None else "Analyzing..."
        
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-card">
            <div class="metric-title">Health Score</div>
            <div class="metric-value-score">{strategy.health_score}<span style="font-size:1.5rem; color:#94A3B8;">/100</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Live Valuation</div>
            <div class="metric-value-money">₹{analysis.current_valuation:,.0f}</div>
            <div class="metric-subtitle">Invested roughly ₹{analysis.total_value:,.0f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">True Portfolio XIRR</div>
            <div class="metric-value-savings">{xirr_display}</div>
            <div class="metric-subtitle">vs {analysis.benchmark_xirr:.1f}% Target Benchmark</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("Asset Reconstruction & Overlaps")
    vcol1, vcol2 = st.columns(2)
    
    with vcol1:
        alloc_data = [{"Sector": k, "Allocation": v} for k, v in analysis.sector_allocation.items()]
        if alloc_data:
            df_alloc = pd.DataFrame(alloc_data)
            fig_sunburst = px.sunburst(df_alloc, path=['Sector'], values='Allocation', 
                                       title="Sector Allocation Weighting",
                                       color_discrete_sequence=['#B8DB80', '#F7DB91', '#FD7979', '#CD2C58'],
                                       template="plotly_white")
            fig_sunburst.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_sunburst, use_container_width=True)
        
    with vcol2:
        inv_data = [{"Fund": inv.fund_name, "Amount": inv.amount, "Sector": inv.sector} for inv in final_state['investments']]
        if inv_data:
            df_inv = pd.DataFrame(inv_data)
            fig_bar = px.bar(df_inv, x='Fund', y='Amount', color='Sector', 
                             title="Capital Deployment by Scheme",
                             color_discrete_sequence=['#B8DB80', '#F7DB91', '#FD7979', '#CD2C58'],
                             template="plotly_white")
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_bar, use_container_width=True)
        
    st.divider()
    st.subheader("Strategist Recommendation Engine")
    
    # Inject custom SVG box for primary feedback instead of standard st.info matching new UI rules
    st.markdown(f'''
    <div class="feedback-bubble">
        <h4 style="color:#DB1A1A; margin-bottom: 0.5rem;"> 🤑 A Note From Your Finance Mentor:</h4>
        <p style="font-size: 1.1rem; line-height: 1.6; color: #475569;">{strategy.feedback}</p>
    </div>
    ''', unsafe_allow_html=True)
    
    col_warn, col_steps = st.columns(2)
    with col_warn:
        if analysis.overlap_warnings:
            st.markdown("<h4 style='color: #334155;'>Detected Overlaps & Overheads</h4>", unsafe_allow_html=True)
            for warning in analysis.overlap_warnings:
                st.markdown(f"<div class='svg-container'>{SVG_WARN} <span>{warning}</span></div>", unsafe_allow_html=True)
        elif analysis.potential_savings > 1000:
            st.markdown(f"<div class='svg-container'>{SVG_WARN} <span>High Expense Ratio Overheads Detected! (~₹{analysis.potential_savings:,.0f} 5-year drag)</span></div>", unsafe_allow_html=True)
    
    with col_steps:
        if strategy.rebalancing_steps:
            st.markdown("<h4 style='color: #334155;'>Friendly Next Steps</h4>", unsafe_allow_html=True)
            for step in strategy.rebalancing_steps:
                st.markdown(f"<div class='svg-container'>{SVG_CHECK} <span>{step}</span></div>", unsafe_allow_html=True)
            
    st.divider()
    st.markdown("<h2 style='color:#DB1A1A; margin-bottom: 0px;'>💬 Ask Your AI Finance Mentor</h2>", unsafe_allow_html=True)
    st.write("Need help understanding what Expense Ratio Drag means? Or why XIRR is so high? Type your question below!")
    
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
    if user_prompt := st.chat_input("Ask a question about your portfolio metrics..."):
        st.session_state.chat_messages.append({"role": "user", "content": user_prompt})
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Reflecting..."):
                    response_text = run_chat_assistant(st.session_state.chat_messages, analysis, strategy)
                    st.markdown(response_text)
                    st.session_state.chat_messages.append({"role": "assistant", "content": response_text})
            
st.markdown("<div style='text-align: center; color: #94A3B8; font-size: 0.95rem; margin-top: 5rem; margin-bottom: 2rem;'><strong>ET MoneyMentor Pro ✨</strong><br>Created with ❤️ by <strong>Team Calyx</strong></div>", unsafe_allow_html=True)
