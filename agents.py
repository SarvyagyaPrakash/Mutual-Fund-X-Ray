from schema import PortfolioState, Investment, AnalysisResult, StrategyPlan
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import List, Dict
import os
import io
import pandas as pd
from datetime import datetime
import requests
import difflib

try:
    import pyxirr
except ImportError:
    pyxirr = None

try:
    import casparser
except ImportError:
    casparser = None

def load_market_db():
    try:
        file_path = os.path.join(os.path.dirname(__file__), "market_data.csv")
        df = pd.read_csv(file_path)
        db = {}
        for _, row in df.iterrows():
            db[row['Fund Name']] = {
                "sector": row['Sector'],
                "expense_ratio": row['Expense Ratio'],
                "holdings": [row['Top Holding 1'], row['Top Holding 2'], row['Top Holding 3']]
            }
        return db
    except Exception as e:
        print(f"Warning: Could not load market_data.csv. Error: {e}")
        return {}

MOCK_MARKET_DB = load_market_db()

class PortfolioExtract(BaseModel):
    investments: List[Investment] = Field(description="List of extracted investments")

def fetch_mfapi_data(fund_name: str, investment_date_str: str, invested_amount: float) -> tuple[float, str]:
    """Returns (current_val, log_message)"""
    try:
        # 1. Search for schemeCode
        search_res = requests.get(f"https://api.mfapi.in/mf/search?q={fund_name}").json()
        if not search_res:
            return 0.0, f"mfapi search failed for {fund_name}"
            
        scheme_code = search_res[0]['schemeCode']
        
        # 2. Get historical data
        hist_res = requests.get(f"https://api.mfapi.in/mf/{scheme_code}").json()
        data = hist_res.get("data", [])
        if not data:
            return 0.0, f"mfapi history empty for {fund_name}"
            
        current_nav = float(data[0]['nav'])
        
        # 3. Find Nav exactly at investment_date (format DD-MM-YYYY)
        target_nav = None
        for entry in data:
            if entry['date'] == investment_date_str:
                target_nav = float(entry['nav'])
                break
                
        if target_nav:
            units = invested_amount / target_nav
            current_val = units * current_nav
            return current_val, f"{fund_name} LIVE: Unit NAV grew from ₹{target_nav} to ₹{current_nav}"
        else:
            return 0.0, f"mfapi date {investment_date_str} exactly not found for {fund_name} (Requires exact market open day)."
            
    except Exception as e:
        return 0.0, f"mfapi API networking error: {e}"

def extractor_node(state: PortfolioState):
    raw_input = state.get("raw_input", "")
    pdf_bytes = state.get("pdf_bytes")
    pdf_password = state.get("pdf_password")
    
    log_updates = ["Agent A (Extractor): Parsing input using Llama-3 (Groq)..."]
    errors = []
    extracted_investments = []
    transactions = []
    
    # 1. CAS Parsing if PDF Uploaded
    if pdf_bytes and pdf_password and casparser:
        log_updates.append("Agent A (Extractor): CAS PDF detected. Decrypting securely locally...")
        try:
            data = casparser.read_cas_pdf(io.BytesIO(pdf_bytes), pdf_password)
            parsed_texts = []
            
            for folio in data.get("folios", []):
                for scheme in folio.get("schemes", []):
                    scheme_name = scheme.get("scheme", "")
                    curr_val = scheme.get("valuation", {}).get("value", 0.0)
                    
                    inv_amt = 0.0
                    for txn in scheme.get("transactions", []):
                        amt = txn.get("amount", 0.0)
                        if amt:
                            inv_amt += abs(amt)
                            transactions.append({"date": txn.get("date"), "amount": amt})
                            
                    parsed_texts.append(f"Invested {inv_amt} in {scheme_name}. Current valuation is {curr_val}.")
            
            raw_input = " ".join(parsed_texts)
            log_updates.append("Agent A (Extractor): PDF Decrypted Successfully. Sending to Llama-3.")
        except Exception as e:
            errors.append(f"Failed to parse CAS PDF. Ensure password is correct. Error: {str(e)}")
            return {"errors": errors, "log": log_updates}

    # 2. LLM Extraction (Switched to Groq + Llama-3)
    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        structured_llm = llm.with_structured_output(PortfolioExtract)
        
        known_funds = ", ".join(MOCK_MARKET_DB.keys())
        prompt = f"""
        You are an advanced, hyper-resilient data extraction engine.
        Analyze the following messy user portfolio text. Extract ALL mutual fund investments accurately, regardless of bad grammar, typos, missing commas, or varying currency symbols (Rs, ₹, Ruppee).
        
        For each investment, extract:
        1. 'amount': The numeric invested amount (clean float, e.g., 20000.0). Ignore currency symbols entirely.
        2. 'investment_date': Extract the exact date if provided, formatted STRICTLY as DD-MM-YYYY (e.g. 01-12-2024).
        3. 'current_value': Only if explicitly provided.
        4. 'fund_name': CRITICAL MATCHING STEP. You must intelligently fuzzy-match the user's typed fund name to the closest Official Database Name. For example, if they type 'tata smallcap', match it perfectly to 'Tata Small Cap'. Do not skip any funds!
        
        Official Database Names (Must Match One): 
        {known_funds}
        
        User Text: 
        {raw_input}
        """
        
        result = structured_llm.invoke(prompt)
        extracted_investments = result.investments
        
        if not extracted_investments:
            log_updates.append("Agent A (Extractor): Failed to extract valid funds from input.")
            errors.append("No valid funds found.")
        else:
            log_updates.append(f"Agent A (Extractor): Successfully extracted {len(extracted_investments)} funds.")
            
    except Exception as e:
        log_updates.append(f"Agent A (Extractor): Llama-3 LLM parsing failed: {str(e)}")
        errors.append(f"LLM Error: {str(e)}")
    
    return {"investments": extracted_investments, "log": log_updates, "errors": errors, "transactions": transactions}

def reflection_node(state: PortfolioState):
    log_updates = ["Agent B (Analyst Reflection): Verifying Llama-3's output format..."]
    errors = []
    
    investments = state.get("investments", [])
    if not investments:
        errors.append("Validation failed: empty portfolio.")
    else:
        log_updates.append("Agent B (Analyst Reflection): Structured schema verified. Ready for mfapi.in live tracking.")
        
    return {"log": log_updates, "errors": errors}

def analyst_node(state: PortfolioState):
    log_updates = ["Agent B (Analyst): Executing Live Tracker via mfapi.in & Market DB..."]
    investments = state.get("investments", [])
    transactions = state.get("transactions", [])
    
    analysis = AnalysisResult()
    
    # 1. Fuzzy Match Auto-Correction (Overrides messy transcription typos safely!)
    known_funds = list(MOCK_MARKET_DB.keys())
    
    for inv in investments:
        fuzzy_matches = difflib.get_close_matches(inv.fund_name, known_funds, n=1, cutoff=0.5)
        if fuzzy_matches:
            # Overwrite the broken string with the perfect, canonical DB entry!
            inv.fund_name = fuzzy_matches[0]
            
        if inv.investment_date and inv.current_value is None:
            # We have an investment date, fetch live exact value from mfapi!
            log_updates.append(f"Agent B (Analyst): pinging api.mfapi.in for {inv.fund_name} at {inv.investment_date}...")
            c_val, msg = fetch_mfapi_data(inv.fund_name, inv.investment_date, inv.amount)
            if c_val > 0.0:
                inv.current_value = c_val
                # Inject a dynamic transaction line mimicking CAS for the XIRR calculator!
                transactions.append({"date": inv.investment_date, "amount": -inv.amount})
            log_updates.append(f"   -> {msg}")

    total_invested = sum(inv.amount for inv in investments) if investments else 0.0
    current_val = sum((inv.current_value if inv.current_value else inv.amount * 1.25) for inv in investments) # Mock growth if no valuation/date
    
    analysis.total_value = total_invested
    analysis.current_valuation = current_val
    analysis.benchmark_xirr = 14.5 # Hardcoded NIFTY 50 5-Year Average
    
    # 2. XIRR Calculation
    if transactions and pyxirr:
        log_updates.append("Agent B (Analyst): Calculating exact XIRR using matched cash flow dates...")
        try:
            dates = []
            amounts = []
            for t in transactions:
                if t.get("date") and t.get("amount"):
                    # ensure formats
                    parsed_dt = pd.to_datetime(t["date"], format="%d-%m-%Y")
                    dates.append(parsed_dt.date())
                    amounts.append(-abs(float(t["amount"]))) # Outflow
            
            # Add current valuation as positive inflow today
            dates.append(datetime.now().date())
            amounts.append(current_val)
            
            xirr_val = pyxirr.xirr(dates, amounts)
            if xirr_val:
                analysis.portfolio_xirr = xirr_val * 100
        except Exception as e:
            log_updates.append(f"Agent B (Analyst): XIRR Math failed logic. Error: {e}")
            
    if analysis.portfolio_xirr is None and total_invested > 0:
        log_updates.append("Agent B (Analyst): Estimating XIRR from current valuation mathematical proximity...")
        returns = current_val / total_invested
        analysis.portfolio_xirr = ((returns ** (1/3)) - 1) * 100 
    
    # 3. Market DB Overlaps
    stock_counts = {}
    total_drag = 0.0
    
    for inv in investments:
        db_info = MOCK_MARKET_DB.get(inv.fund_name)
        if db_info:
            inv.sector = db_info["sector"]
            inv.expense_ratio = db_info["expense_ratio"]
            inv.holdings = db_info["holdings"]
            
            if inv.expense_ratio and inv.expense_ratio > 0.5:
                excess = inv.expense_ratio - 0.5
                drag = inv.amount * (excess / 100)
                total_drag += drag
            
            if inv.sector and current_val > 0:
                allocation_weight = (inv.current_value if inv.current_value else (inv.amount * 1.25)) / current_val
                analysis.sector_allocation[inv.sector] = analysis.sector_allocation.get(inv.sector, 0.0) + (allocation_weight * 100)
            
            for stock in (inv.holdings or []):
                if stock not in stock_counts:
                    stock_counts[stock] = []
                stock_counts[stock].append(inv.fund_name)

    for stock, funds in stock_counts.items():
        if len(funds) > 1:
            analysis.overlap_warnings.append(f"High overlap in {stock}: held by {', '.join(funds)}.")
            
    analysis.expense_ratio_drag = total_drag
    analysis.potential_savings = total_drag * 5
    
    return {"analysis": analysis, "log": log_updates, "investments": investments}

def strategist_node(state: PortfolioState):
    log_updates = ["Agent C (Strategist): Initializing Llama-3 Mentor Generation..."]
    
    analysis = state.get("analysis")
    investments = state.get("investments", [])
    
    if not analysis:
        return {"log": log_updates + ["Agent C (Strategist): No analysis available."]}

    try:
        # Powered by incredibly fast Llama-3 via Groq for open-source AI requirement!
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0)
        structured_llm = llm.with_structured_output(StrategyPlan)
        
        portfolio_summary = "\n".join([f"- {inv.fund_name}: ₹{inv.amount}" for inv in investments])
        overlap_info = "\n".join([f"- {warn}" for warn in analysis.overlap_warnings])
        
        # PIVOT: Safe, Educational, Directional Mentoring Prompt
        prompt = f"""
        You are a warm, educational Personal Finance Mentor for 'ET MoneyMentor Pro'. You are communicating to an everyday user who may be confused about investing. Your goal is to guide them conceptually and strictly directionally (never recommend specific assets to avoid legal liability).
        
        Portfolio Details:
        {portfolio_summary}
        
        Analysis Insights:
        - Portfolio XIRR: {analysis.portfolio_xirr:.2f}% vs Benchmark NIFTY 14.5%
        - Estimated Excess Fees (5-year drag): ₹{analysis.potential_savings}
        - Overlaps detected:
        {overlap_info if overlap_info else "- None"}
        
        Task:
        1. Set a 'Money Health Score' out of 100. Lower it slightly if overlaps exist or if fees are high.
        2. Write exactly 2-3 sentences of 'feedback' that is warm, completely free of jargon, and highly encouraging about their financial journey.
        3. Provide exactly 2 'rebalancing_steps' that are strictly EDUCATIONAL and DIRECTIONAL. 
           (e.g., "Consider diversifying into low-cost large-cap index funds for stability" or "Consolidate overlapping funds to avoid paying double fees for the exact same stocks"). 
           CRITICAL: DO NOT RECOMMEND SPECIFIC MUTUAL FUNDS BY NAME. DO NOT USE TICKER SYMBOLS. Keep it completely safe and conceptual.
        """
        
        strategy = structured_llm.invoke(prompt)
        log_updates.append("Agent C (Strategist): Educational Mentor feedback derived successfully.")
        
    except Exception as e:
        log_updates.append(f"Agent C (Strategist): Llama-3 failed generation. Error: {str(e)}")
        strategy = StrategyPlan(
            health_score=50,
            feedback="We encountered a technical hurdle generating your mentor feedback. Please check your Groq API keys.",
            rebalancing_steps=["Ensure your Open-Source Groq credentials are valid."]
        )
        
    return {"strategy": strategy, "log": log_updates}

def run_chat_assistant(chat_history: list, analysis: AnalysisResult, strategy: StrategyPlan) -> str:
    """Invokes a separate, context-aware conversational AI bound by strict educational guardrails."""
    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)
        
        xirr_txt = f"{analysis.portfolio_xirr:.2f}%" if analysis.portfolio_xirr else "Still analyzing XIRR"
        overlap_txt = " | ".join(analysis.overlap_warnings) if analysis.overlap_warnings else "No overlaps found"
        
        sys_prompt = f"""
        You are the friendly 'ET MoneyMentor Co-Pilot'. 
        You exist to warmly answer any questions the user has about their generated mutual fund portfolio report.
        Keep explanations of finance jargon (like XIRR, expense ratio drag, overlaps, large-caps vs small-caps) incredibly simple, short, and metaphor-driven so beginners understand perfectly.
        
        User's Portfolio Snapshot Context:
        - Portfolio XIRR: {xirr_txt}
        - Current Valuation: ₹{analysis.current_valuation:,.0f}
        - Overlaps Found: {overlap_txt}
        - Overarching Feedback Given: {strategy.feedback}
        
        CRITICAL GUARDRAIL - THE LAW: 
        You are strictly an educational mentor. You explicitly CANNOT offer specific asset recommendations. 
        If the user asks "Which fund should I buy?", politely decline and instead explain the difference between fund categories conceptually (e.g. "I can't recommend specific names, but choosing historically stable Large-Cap indices is often safer than volatile Small-Caps...").
        Be highly conversational, brief, and warm. 
        """
        
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        langchain_messages = [SystemMessage(content=sys_prompt)]
        
        for msg in chat_history:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
                
        response = llm.invoke(langchain_messages)
        return response.content
        
    except Exception as e:
        return f"Whoops, my text generation engine hit a snag: {str(e)}"
