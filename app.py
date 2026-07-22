"""
app.py — Interactive Enterprise Web Dashboard for Video Research Agent
=====================================================================

Zero Emojis. Custom Enterprise Dark Theme matching design.
Features:
- Video Thumbnail Preview Card & Metadata
- Fully Responsive Layout (Desktop, Laptop, Tablet, Mobile breakpoints)
- Interactive Preset Chips for 1-click execution
- SVG Data-URI vector icons for guaranteed rendering
"""

import os
import re
import json
import time
import textwrap
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from agent import run_agent, TOOL_SCHEMAS

# =============================================================================
# PAGE CONFIGURATION & CUSTOM ENTERPRISE CSS
# =============================================================================
st.set_page_config(
    page_title="Video Research Dashboard",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global Dark Theme */
    html, body, .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #F8FAFC !important;
        background-color: #0B0F19 !important;
    }

    /* Preserve Streamlit Material Icon Font */
    [data-testid="stIconMaterial"],
    button[data-testid="stHeaderCollapseButton"] span,
    button[data-testid="stSidebarCollapseButton"] span,
    .material-symbols-rounded,
    .material-symbols-outlined {
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    }

    .main .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2.5rem;
        max-width: 1360px;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #080C14 !important;
        border-right: 1px solid #1E293B !important;
    }

    /* Hide standard radio circles in sidebar for clean custom menu look */
    div[data-testid="stRadio"] label div[role="radio"],
    div[data-testid="stRadio"] label input {
        display: none !important;
    }

    div[data-testid="stRadio"] label {
        background-color: transparent !important;
        border-radius: 6px !important;
        padding: 0.65rem 0.85rem !important;
        color: #94A3B8 !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        margin-bottom: 0.2rem !important;
        transition: all 0.15s ease !important;
    }

    div[data-testid="stRadio"] label:hover {
        background-color: #1E293B !important;
        color: #F8FAFC !important;
    }

    div[data-testid="stRadio"] label[aria-checked="true"] {
        background-color: #1E293B !important;
        color: #38BDF8 !important;
        font-weight: 600 !important;
    }

    /* Top Navigation Header Bar */
    .top-header-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
    }

    .page-title {
        font-size: 1.65rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.02em;
        margin: 0;
    }

    .top-user-area {
        display: flex;
        align-items: center;
        gap: 1.25rem;
    }

    .avatar-circle {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: #334155;
        border: 1px solid #475569;
    }

    /* Main Dashboard Panel */
    .dashboard-panel {
        background-color: #111827;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4);
    }

    .container-title {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #38BDF8;
        margin-bottom: 1.25rem;
    }

    /* 2x2 Step Card Grid */
    .steps-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1.25rem;
    }

    /* Step Card Base */
    .step-card-box {
        background-color: #0F172A;
        border-radius: 10px;
        padding: 1.25rem 1.35rem;
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 140px;
        overflow: hidden;
        transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.2s ease;
    }

    .step-card-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }

    .step-card-complete {
        border: 2px solid #10B981;
    }

    .step-card-inprogress {
        border: 2px solid #0284C7;
    }

    .step-card-queued {
        border: 1.5px solid #1E3A5F;
    }

    .step-card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }

    .step-card-title {
        font-size: 1rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.35;
        max-width: 70%;
    }

    .step-card-footer {
        font-size: 0.825rem;
        color: #94A3B8;
        font-weight: 500;
        margin-top: 1rem;
    }

    /* Progress bar along bottom edge */
    .card-progress-bar-75 {
        position: absolute;
        bottom: 0;
        left: 0;
        width: 75%;
        height: 3px;
        background-color: #38BDF8;
        border-radius: 0 0 0 10px;
    }

    .card-progress-bar-100 {
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background-color: #10B981;
        border-radius: 0 0 10px 10px;
    }

    /* Style Streamlit Form directly as the Right Panel Box */
    div[data-testid="stForm"] {
        background-color: #111827 !important;
        border: 1px solid #1E293B !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4) !important;
    }

    /* Input & Action Panel */
    div.stTextArea > div > div > textarea {
        background-color: #0F172A !important;
        border: 1.5px solid #0284C7 !important;
        border-radius: 8px !important;
        color: #F8FAFC !important;
        font-size: 0.9rem !important;
        padding: 0.85rem 1rem !important;
        resize: none !important;
        height: 140px !important;
    }

    div.stTextArea > div > div > textarea:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2) !important;
    }

    /* Execute Button Override */
    div.stButton > button {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        font-size: 0.925rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        border: none !important;
        width: 100% !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        transition: all 0.15s ease !important;
        margin-top: 0.5rem !important;
    }

    div.stButton > button:hover {
        background-color: #1D4ED8 !important;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.45) !important;
    }

    /* Video Preview Card */
    .video-preview-box {
        display: flex;
        flex-direction: column;
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 1.25rem;
    }

    .video-thumb-container {
        position: relative;
        width: 100%;
        height: 200px;
        overflow: hidden;
        background-color: #000;
    }

    .video-thumb-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 0.9;
        transition: transform 0.3s ease;
    }

    .video-thumb-container:hover .video-thumb-img {
        transform: scale(1.03);
    }

    .video-info-body {
        padding: 1rem 1.25rem;
    }

    .video-info-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 0.35rem;
    }

    .video-info-meta {
        font-size: 0.825rem;
        color: #38BDF8;
        font-weight: 500;
    }

    /* Responsive Breakpoints */
    @media (max-width: 1024px) {
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .steps-grid {
            grid-template-columns: 1fr !important;
        }
    }

    @media (max-width: 768px) {
        .top-header-bar {
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 0.75rem !important;
        }
    }

    /* Hide default menu & footer, but keep sidebar toggle button visible */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    button[data-testid="stHeaderCollapseButton"],
    button[data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        color: #38BDF8 !important;
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 6px !important;
        padding: 0.35rem !important;
    }
</style>
"""
st.html(CUSTOM_CSS)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_knowledge_base_files():
    kb = Path("knowledge_base")
    if not kb.exists():
        return []
    return sorted([f.name for f in kb.glob("*.txt")])


def read_transcript_content(filename):
    path = Path("knowledge_base") / filename
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"
    return "File not found."


def extract_youtube_video_id(url_or_text):
    match = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", str(url_or_text))
    return match.group(1) if match else None


# SVG Data URIs for guaranteed rendering in all Streamlit wrappers
ICON_1 = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='36' height='36' viewBox='0 0 24 24' fill='none' stroke='%2310B981' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><rect x='2' y='2' width='6' height='6' rx='1'/><rect x='16' y='2' width='6' height='6' rx='1'/><rect x='9' y='16' width='6' height='6' rx='1'/><path d='M5 8v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8'/><path d='M12 13v3'/></svg>"
ICON_2 = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='36' height='36' viewBox='0 0 24 24' fill='none' stroke='%2310B981' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><polyline points='14 2 14 8 20 8'/><line x1='16' y1='13' x2='8' y2='13'/><line x1='16' y1='17' x2='8' y2='17'/><path d='M10 9H8'/></svg>"
ICON_3 = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='36' height='36' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><rect x='2' y='2' width='20' height='20' rx='2.18' ry='2.18'/><line x1='7' y1='2' x2='7' y2='22'/><line x1='17' y1='2' x2='17' y2='22'/><line x1='2' y1='12' x2='22' y2='12'/><line x1='2' y1='7' x2='7' y2='7'/><line x1='2' y1='17' x2='7' y2='17'/><line x1='17' y1='17' x2='22' y2='17'/><line x1='17' y1='7' x2='22' y2='7'/><circle cx='12' cy='12' r='2.5'/></svg>"
ICON_4 = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='36' height='36' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><path d='M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2'/><rect x='8' y='2' width='8' height='4' rx='1' ry='1'/><path d='M9 12l2 2 4-4'/><path d='M9 17h6'/></svg>"
ICON_BELL = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%2394A3B8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9'/><path d='M13.73 21a2 2 0 0 1-3.46 0'/></svg>"
ICON_CHEVRON = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%2394A3B8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>"


# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================
with st.sidebar:
    st.html('<div style="font-size: 1.15rem; font-weight: 700; color: #FFFFFF; padding: 0.5rem 0.5rem 1rem 0.5rem;">Video Research AI</div>')

    nav_option = st.radio(
        "Navigation",
        options=["Research Projects", "Video Library", "Agent Status", "Insights"],
        label_visibility="collapsed"
    )

    st.html("<hr style='border:none; border-top:1px solid #1E293B; margin: 1.5rem 0;'>")

    st.html('<div style="font-size: 0.725rem; font-weight: 700; text-transform: uppercase; color: #64748B; letter-spacing: 0.05em; padding-left: 0.5rem; margin-bottom: 0.5rem;">EXECUTION PARAMETERS</div>')
    max_iter = st.slider("Max Loop Iterations", min_value=3, max_value=15, value=10, step=1)

    st.html("<hr style='border:none; border-top:1px solid #1E293B; margin: 1.5rem 0;'>")

    st.html('<div style="font-size: 0.725rem; font-weight: 700; text-transform: uppercase; color: #64748B; letter-spacing: 0.05em; padding-left: 0.5rem; margin-bottom: 0.5rem;">API STATUS</div>')
    serp_ok = bool(os.environ.get("SERPAPI_KEY"))
    groq_ok = bool(os.environ.get("GROQ_API_KEY"))

    st.html(
        f'<div style="font-size: 0.825rem; color: #94A3B8; padding-left: 0.5rem; margin-bottom: 0.35rem;">SerpApi Search: <span style="font-weight:600; color:{"#10B981" if serp_ok else "#EF4444"}">{"Active" if serp_ok else "Missing"}</span></div>'
    )
    st.html(
        f'<div style="font-size: 0.825rem; color: #94A3B8; padding-left: 0.5rem; margin-bottom: 0.35rem;">Groq LLM + Whisper: <span style="font-weight:600; color:{"#10B981" if groq_ok else "#EF4444"}">{"Active" if groq_ok else "Missing"}</span></div>'
    )

    st.html("<hr style='border:none; border-top:1px solid #1E293B; margin: 1.5rem 0;'>")
    st.html('<div style="font-size: 0.75rem; color: #475569; padding-left: 0.5rem;">Zero Emojis Engine v2.0</div>')


# =============================================================================
# TOP HEADER BAR
# =============================================================================
st.html(f'''
<div class="top-header-bar">
    <h1 class="page-title">Dashboard</h1>
    <div class="top-user-area">
        <div style="cursor: pointer; display: flex; align-items: center;">
            <img src="{ICON_BELL}" width="20" height="20" alt="Notification Bell" />
        </div>
        <div style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
            <div class="avatar-circle"></div>
            <img src="{ICON_CHEVRON}" width="14" height="14" alt="Chevron" />
        </div>
    </div>
</div>
''')


# =============================================================================
# INITIALIZE SESSION STATE
# =============================================================================
if "step1_status" not in st.session_state:
    st.session_state["step1_status"] = "100% Complete"
    st.session_state["step1_class"] = "step-card-complete"
    st.session_state["step1_progress"] = '<div class="card-progress-bar-100"></div>'

if "step2_status" not in st.session_state:
    st.session_state["step2_status"] = "100% Complete"
    st.session_state["step2_class"] = "step-card-complete"
    st.session_state["step2_progress"] = '<div class="card-progress-bar-100"></div>'

if "step3_status" not in st.session_state:
    st.session_state["step3_status"] = "75% In Progress"
    st.session_state["step3_class"] = "step-card-inprogress"
    st.session_state["step3_progress"] = '<div class="card-progress-bar-75"></div>'

if "step4_status" not in st.session_state:
    st.session_state["step4_status"] = "Queued"
    st.session_state["step4_class"] = "step-card-queued"
    st.session_state["step4_progress"] = ""

if "last_response" not in st.session_state:
    st.session_state["last_response"] = None

if "last_video_meta" not in st.session_state:
    st.session_state["last_video_meta"] = None

if "task_input_value" not in st.session_state:
    st.session_state["task_input_value"] = "how transformers work in AI"


# =============================================================================
# VIEW 1: RESEARCH PROJECTS (MAIN DASHBOARD)
# =============================================================================
if nav_option == "Research Projects":
    col_left, col_right = st.columns([2.2, 1], gap="medium")

    # --- LEFT PANEL: AGENT EXECUTION PROGRESS GRID ---
    with col_left:
        step_grid_html = textwrap.dedent(f'''
        <div class="dashboard-panel">
            <div class="container-title">AGENT EXECUTION PROGRESS</div>
            <div class="steps-grid">
                
                <div class="step-card-box {st.session_state["step1_class"]}">
                    <div class="step-card-header">
                        <div class="step-card-title">1. Ingesting Video Data</div>
                        <div class="step-card-icon">
                            <img src="{ICON_1}" width="36" height="36" alt="Step 1 Icon" />
                        </div>
                    </div>
                    <div class="step-card-footer">{st.session_state["step1_status"]}</div>
                    {st.session_state["step1_progress"]}
                </div>

                <div class="step-card-box {st.session_state["step2_class"]}">
                    <div class="step-card-header">
                        <div class="step-card-title">2. Generating Transcripts & Keywords</div>
                        <div class="step-card-icon">
                            <img src="{ICON_2}" width="36" height="36" alt="Step 2 Icon" />
                        </div>
                    </div>
                    <div class="step-card-footer">{st.session_state["step2_status"]}</div>
                    {st.session_state["step2_progress"]}
                </div>

                <div class="step-card-box {st.session_state["step3_class"]}">
                    <div class="step-card-header">
                        <div class="step-card-title">3. Identifying Key Scenes & Moments</div>
                        <div class="step-card-icon">
                            <img src="{ICON_3}" width="36" height="36" alt="Step 3 Icon" />
                        </div>
                    </div>
                    <div class="step-card-footer">{st.session_state["step3_status"]}</div>
                    {st.session_state["step3_progress"]}
                </div>

                <div class="step-card-box {st.session_state["step4_class"]}">
                    <div class="step-card-header">
                        <div class="step-card-title">4. Synthesizing Insights Report</div>
                        <div class="step-card-icon">
                            <img src="{ICON_4}" width="36" height="36" alt="Step 4 Icon" />
                        </div>
                    </div>
                    <div class="step-card-footer">{st.session_state["step4_status"]}</div>
                    {st.session_state["step4_progress"]}
                </div>

            </div>
        </div>
        ''')
        st.html(step_grid_html)

    # --- RIGHT PANEL: EXECUTION INPUT FORM & INTERACTIVE CHIPS ---
    with col_right:
        # Interactive Preset Prompt Chips
        st.markdown('<div style="font-size: 0.75rem; font-weight: 700; color: #64748B; letter-spacing: 0.05em; margin-bottom: 0.4rem;">INTERACTIVE PRESETS</div>', unsafe_allow_html=True)
        p1, p2, p3 = st.columns(3)
        if p1.button("Transformers", key="preset_tf"):
            st.session_state["task_input_value"] = "how transformers work in AI"
            st.rerun()
        if p2.button("Asyncio", key="preset_async"):
            st.session_state["task_input_value"] = "Python asyncio tutorial for beginners"
            st.rerun()
        if p3.button("Neural Nets", key="preset_nn"):
            st.session_state["task_input_value"] = "neural networks explained simple"
            st.rerun()

        with st.form(key="execute_task_form"):
            task_input = st.text_area(
                "Task Input",
                value=st.session_state["task_input_value"],
                placeholder="Enter video URLs or research topic...",
                height=130,
                label_visibility="collapsed"
            )
            submit_btn = st.form_submit_button("Execute Agent Task")

    # --- AGENT EXECUTION TRIGGER & DYNAMIC PROGRESS ---
    if submit_btn:
        if not task_input.strip():
            st.error("Please enter a research topic or video URL.")
        elif not (serp_ok and groq_ok):
            st.error("API keys missing. Please verify SERPAPI_KEY and GROQ_API_KEY in your .env file.")
        else:
            st.session_state["step1_status"] = "In Progress"
            st.session_state["step1_class"] = "step-card-inprogress"
            st.session_state["step1_progress"] = '<div class="card-progress-bar-75"></div>'
            
            st.session_state["step2_status"] = "Queued"
            st.session_state["step2_class"] = "step-card-queued"
            st.session_state["step2_progress"] = ""
            
            st.session_state["step3_status"] = "Queued"
            st.session_state["step3_class"] = "step-card-queued"
            st.session_state["step3_progress"] = ""

            st.session_state["step4_status"] = "Queued"
            st.session_state["step4_class"] = "step-card-queued"
            st.session_state["step4_progress"] = ""

            def agent_callback(event_type, payload):
                if event_type == "tool_start":
                    if payload["name"] == "search_video":
                        st.session_state["step1_status"] = "100% Complete"
                        st.session_state["step1_class"] = "step-card-complete"
                        st.session_state["step1_progress"] = '<div class="card-progress-bar-100"></div>'
                        st.session_state["step2_status"] = "In Progress"
                        st.session_state["step2_class"] = "step-card-inprogress"
                        st.session_state["step2_progress"] = '<div class="card-progress-bar-75"></div>'
                    elif payload["name"] == "transcribe_video":
                        st.session_state["step2_status"] = "100% Complete"
                        st.session_state["step2_class"] = "step-card-complete"
                        st.session_state["step2_progress"] = '<div class="card-progress-bar-100"></div>'
                        st.session_state["step3_status"] = "75% In Progress"
                        st.session_state["step3_class"] = "step-card-inprogress"
                        st.session_state["step3_progress"] = '<div class="card-progress-bar-75"></div>'
                elif event_type == "tool_end":
                    if payload["name"] == "search_video":
                        try:
                            parsed_res = json.loads(payload["result"])
                            st.session_state["last_video_meta"] = parsed_res
                        except Exception:
                            pass
                    elif payload["name"] == "transcribe_video":
                        st.session_state["step3_status"] = "100% Complete"
                        st.session_state["step3_class"] = "step-card-complete"
                        st.session_state["step3_progress"] = '<div class="card-progress-bar-100"></div>'
                        st.session_state["step4_status"] = "Synthesizing..."
                        st.session_state["step4_class"] = "step-card-inprogress"
                        st.session_state["step4_progress"] = '<div class="card-progress-bar-75"></div>'

            with st.spinner("Agent running autonomous task execution..."):
                response = run_agent(task_input, max_iterations=max_iter, status_callback=agent_callback)

            # Final states
            st.session_state["step1_status"] = "100% Complete"
            st.session_state["step1_class"] = "step-card-complete"
            st.session_state["step1_progress"] = '<div class="card-progress-bar-100"></div>'

            st.session_state["step2_status"] = "100% Complete"
            st.session_state["step2_class"] = "step-card-complete"
            st.session_state["step2_progress"] = '<div class="card-progress-bar-100"></div>'

            st.session_state["step3_status"] = "100% Complete"
            st.session_state["step3_class"] = "step-card-complete"
            st.session_state["step3_progress"] = '<div class="card-progress-bar-100"></div>'

            st.session_state["step4_status"] = "100% Complete"
            st.session_state["step4_class"] = "step-card-complete"
            st.session_state["step4_progress"] = '<div class="card-progress-bar-100"></div>'

            st.session_state["last_response"] = response
            st.rerun()

    # --- DISPLAY RESULTS & VIDEO THUMBNAIL CARD ---
    if st.session_state["last_response"] or st.session_state["last_video_meta"]:
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        
        # Check if video metadata with thumbnail is available
        vid_meta = st.session_state.get("last_video_meta")
        if not vid_meta and st.session_state.get("task_input_value"):
            vid_id = extract_youtube_video_id(st.session_state["task_input_value"])
            if vid_id:
                vid_meta = {
                    "title": "Selected Video Stream",
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "channel": "YouTube Video",
                    "thumbnail": f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"
                }

        if vid_meta and vid_meta.get("thumbnail"):
            thumb_url = vid_meta["thumbnail"]
            vid_title = vid_meta.get("title", "Video Result")
            vid_channel = vid_meta.get("channel", "Channel")
            vid_link = vid_meta.get("url", "#")

            thumb_card_html = textwrap.dedent(f'''
            <div class="video-preview-box">
                <div class="video-thumb-container">
                    <img src="{thumb_url}" class="video-thumb-img" alt="{vid_title}" />
                </div>
                <div class="video-info-body">
                    <div class="video-info-title">{vid_title}</div>
                    <div class="video-info-meta">Channel: {vid_channel} | <a href="{vid_link}" target="_blank" style="color:#38BDF8; text-decoration:underline;">Watch on YouTube</a></div>
                </div>
            </div>
            ''')
            st.html(thumb_card_html)

        st.markdown('<div class="container-title">SYNTHESIZED INSIGHTS REPORT</div>', unsafe_allow_html=True)
        if st.session_state["last_response"]:
            st.markdown(st.session_state["last_response"])
        st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# VIEW 2: VIDEO LIBRARY
# =============================================================================
elif nav_option == "Video Library":
    st.html('<div class="result-card"><div class="container-title">VIDEO TRANSCRIPT LIBRARY</div></div>')
    
    files = get_knowledge_base_files()
    if not files:
        st.info("No video transcript files found in knowledge_base/. Execute a task to save transcripts.")
    else:
        selected_file = st.selectbox("Select Transcript File", options=files)
        if selected_file:
            content = read_transcript_content(selected_file)
            st.markdown(f"**File**: `knowledge_base/{selected_file}` ({len(content.split())} words)")
            
            # Check for YouTube video ID in filename to show thumbnail
            v_id = extract_youtube_video_id(selected_file)
            if v_id:
                st.html(f'''
                <div style="margin: 1rem 0; width: 320px; border-radius: 8px; overflow: hidden; border: 1px solid #1E293B;">
                    <img src="https://img.youtube.com/vi/{v_id}/hqdefault.jpg" style="width: 100%; height: 180px; object-fit: cover;" alt="Transcript Thumbnail" />
                </div>
                ''')

            st.text_area("Transcript Content", value=content, height=400)


# =============================================================================
# VIEW 3: AGENT STATUS
# =============================================================================
elif nav_option == "Agent Status":
    st.html('<div class="result-card"><div class="container-title">AGENT SYSTEM DIAGNOSTICS</div></div>')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.html('<div class="metric-box"><div class="metric-val">Active</div><div class="metric-lbl">Groq LLaMA 3.3</div></div>')
    with col2:
        st.html('<div class="metric-box"><div class="metric-val">Whisper</div><div class="metric-lbl">Speech Engine</div></div>')
    with col3:
        st.html('<div class="metric-box"><div class="metric-val">SerpApi</div><div class="metric-lbl">YouTube Search</div></div>')

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Registered Tool Schemas:**")
    st.json(TOOL_SCHEMAS)


# =============================================================================
# VIEW 4: INSIGHTS
# =============================================================================
elif nav_option == "Insights":
    st.html('<div class="result-card"><div class="container-title">RESEARCH & ANALYTICS INSIGHTS</div></div>')
    
    if st.session_state["last_response"]:
        st.markdown(st.session_state["last_response"])
    else:
        st.write("No research insights currently generated. Run an agent task from the Research Projects menu.")
