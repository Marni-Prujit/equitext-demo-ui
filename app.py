import streamlit as st
import requests
import re
import plotly.graph_objects as go
from st_copy_button import st_copy_button
import os

API_URL = st.secrets.get("API_URL", os.environ.get("API_URL"))
API_KEY = st.secrets.get("API_KEY", os.environ.get("API_KEY"))

if not API_URL or not API_KEY:
    st.error("Missing API_URL / API_KEY. Add them in Streamlit Secrets.")
    st.stop()

# --- HELPER FUNCTIONS ---
def split_sentences(text: str):
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]

def calc_bias_score(user_text: str, biased_sentences: list):
    total = len(split_sentences(user_text))
    biased = len(biased_sentences) if biased_sentences else 0
    if total == 0:
        return 0
    return round((biased / total) * 100)

def bias_gauge(score: int):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%"},
            title={"text": "Bias Score"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "rgba(157, 78, 221, 0.9)"},
                "steps": [
                    {"range": [0, 20], "color": "rgba(46, 204, 113, 0.25)"},   # green
                    {"range": [20, 50], "color": "rgba(241, 196, 15, 0.25)"}, # yellow
                    {"range": [50, 100], "color": "rgba(231, 76, 60, 0.25)"}  # red
                ],
            },
        )
    )
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
    )
    return fig

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="EquiText",
    page_icon="🟣",
    layout="centered"
)

# --- STATE MANAGEMENT ---
# We need this so the analysis doesn't vanish when you click a radio button
if 'api_data' not in st.session_state:
    st.session_state.api_data = None
if 'original_text' not in st.session_state:
    st.session_state.original_text = ""

# --- CUSTOM CSS ---
st.markdown("""
<style>
/* 1. Main Background */
.stApp {
    background: radial-gradient(circle at 50% 10%, #4a0e78 0%, #10002b 40%, #05010a 100%);
    color: #ffffff;
}

/* 2. Glassmorphism Input */
.stTextArea > div > div > textarea {
    background-color: rgba(255, 255, 255, 0.05);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    font-size: 16px;
}
.stTextArea > div > div > textarea:focus {
    border-color: #9d4edd;
    box-shadow: 0 0 15px rgba(157, 78, 221, 0.4);
}

/* 3. Button Styling */
.stButton > button {
    background: linear-gradient(90deg, #7b2cbf, #9d4edd);
    color: white;
    border: none;
    border-radius: 50px;
    padding: 12px 30px;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 600;
    width: 100%;
    transition: all 0.3s ease;
}
.stButton > button:hover {
    transform: scale(1.02);
    box-shadow: 0 0 20px rgba(157, 78, 221, 0.6);
}

/* 4. Headers */
.hero-title {
    font-family: 'Helvetica Neue', sans-serif;
    font-weight: 800;
    font-size: 3rem;
    text-align: center;
    background: -webkit-linear-gradient(left, #e0aa3e, #9d4edd, #e0aa3e);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 10px;
}
.hero-subtitle {
    font-family: 'Arial', sans-serif;
    font-weight: 300;
    font-size: 1.2rem;
    text-align: center;
    color: #e0e0e0;
    letter-spacing: 1px;
    margin-bottom: 40px;
}

/* 5. Custom Card for Biased Sentence */
.bias-card {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 20px;
}
.detected-label {
    color: #ff9f43;
    font-weight: bold;
    font-size: 0.9em;
    text-transform: uppercase;
    margin-bottom: 5px;
}

/* 6. Final Result Box */
.final-result-box {
    background-color: rgba(46, 204, 113, 0.1);
    border: 1px solid #2ecc71;
    color: #ffffff;
    padding: 20px;
    border-radius: 10px;
    margin-top: 20px;
    line-height: 1.6;
}
            
/* --- Final Result (st.code) clean + copy button space --- */
div[data-testid="stCodeBlock"] {
    background-color: rgba(46, 204, 113, 0.10) !important;
    border: 1px solid #2ecc71 !important;
    border-radius: 14px !important;
    padding: 0px !important;                 /* we'll control padding on inner elements */
    overflow: hidden !important;
}

/* The actual text area */
div[data-testid="stCodeBlock"] pre {
    margin: 0 !important;
    padding: 18px 72px 18px 18px !important; /* IMPORTANT: right padding reserves space for copy icon */
    background: transparent !important;
    font-size: 18px !important;
    line-height: 1.6 !important;
    white-space: pre-wrap !important;        /* wrap long lines */
    word-break: break-word !important;
    overflow-wrap: anywhere !important;
}

/* Make the code font look normal (not monospace if you prefer) */
div[data-testid="stCodeBlock"] code {
    font-family: inherit !important;         /* looks like normal text */
    color: #ffffff !important;
}

/* Position the copy button neatly */
div[data-testid="stCodeBlock"] button {
    top: 12px !important;
    right: 12px !important;
    border-radius: 10px !important;
}
                    
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown('<div class="hero-title">EquiText</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Exclusively Inclusive 😉</div>', unsafe_allow_html=True)

# --- MAIN INPUT ---
# Using session state to allow the text area to persist text
user_text = st.text_area(
    "Input", 
    placeholder="Enter your text here to analyse...", 
    height=150, 
    label_visibility="collapsed",
    key="jd_text"
)

WORD_LIMIT = 1000
# Always read the latest text from session state
current_text = st.session_state.get("jd_text", "")
words = re.findall(r"\S+", current_text.strip())
word_count = len(words)

st.caption(f"Word count: {word_count} / {WORD_LIMIT}")

over_limit = word_count > WORD_LIMIT
if over_limit:
    st.error(f"Word limit exceeded. Please reduce to {WORD_LIMIT} words or less.")

st.markdown("<br>", unsafe_allow_html=True)

# Center the button
col1, col2, col3 = st.columns([3, 2, 3])
with col2:
    analyze_clicked = st.button("Analyse", use_container_width=True, disabled=over_limit or len(current_text.strip()) == 0)

# --- LOGIC ---
if analyze_clicked:
    if not user_text.strip():
        st.warning("Please enter some text first.")
    else:
        with st.spinner("Processing..."):
            try:
                headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
                response = requests.post(API_URL, json={"sentence": user_text}, headers=headers)
                
                if response.status_code == 200:
                    # STORE DATA IN SESSION STATE
                    st.session_state.api_data = response.json()
                    st.session_state.original_text = user_text
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"Connection Failed: {e}")

# --- DISPLAY RESULTS (From Session State) ---
if st.session_state.api_data:
    data = st.session_state.api_data
    original_full_text = st.session_state.original_text
    
    st.markdown("---")
    
    # 1. Bias Score
    biased_list = data.get("biased_sentences", [])
    score = calc_bias_score(original_full_text, biased_list)
    
    st.markdown("## Overall Bias Level")
    if score == 0:
        st.success("✅ 0% biased — looks inclusive overall.")
    else:
        st.plotly_chart(bias_gauge(score), use_container_width=True)
    
    st.markdown("---")
    st.markdown("## Review & Select")

    rewrite_items = data.get("rewrite_options", [])
    
    # We will build the final text by starting with original and replacing parts
    final_output_text = original_full_text

    # Dictionary to hold user choices (Original vs Option 1, 2, 3)
    user_choices = {}

    if not rewrite_items:
        st.info("No bias detected to replace.")
    else:
        # Loop through each biased sentence found
        for idx, item in enumerate(rewrite_items, start=1):
            sentence = item.get("sentence", "")
            labels = item.get("labels", [])
            options = item.get("options", [])
            
            # Create a card for this issue
            st.markdown(f"""
            <div class="bias-card">
                <div class="detected-label">Issue {idx}: {', '.join(labels).title() if labels else 'Detected Bias'}</div>
                <div style="font-style: italic; color: #ffcccc; margin-bottom: 10px;">"{sentence}"</div>
            </div>
            """, unsafe_allow_html=True)

            # Prepare radio options
            # We add "Keep Original" as the first option
            radio_options = ["Keep Original"] + options
            
            # Display Radio Button
            # Key is important so Streamlit differentiates the buttons
            choice = st.radio(
                f"Choose replacement for Sentence {idx}:",
                radio_options,
                key=f"radio_{idx}"
            )
            
            # Logic: If user selected something other than "Keep Original", perform replacement
            if choice != "Keep Original":
                # We replace the *exact* biased sentence string with the chosen option
                # Note: This simple replacement assumes the sentence text is unique in the JD.
                final_output_text = final_output_text.replace(sentence, choice)

            st.markdown("---")

    # --- FINAL RESULT DISPLAY ---
    st.markdown("## Final Result")
    st.caption("Copy your updated job description below.")

    # Normal textbox look (read-only)
    # Normal textbox look (read-only)
    st.text_area(
        "",
        value=final_output_text,
        height=220,
        label_visibility="collapsed"    
    )

    # Real copy button (one click copies the full text)
    st_copy_button(
        text=final_output_text,
        before_copy_label="Copy to clipboard",
        after_copy_label="✅ Copied!",
        show_text=False
    )