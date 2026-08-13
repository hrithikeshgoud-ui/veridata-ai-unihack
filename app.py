import streamlit as st
import pypdf
import json
import google.generativeai as genai

# Streamlit Page Setup - Collapse Sidebar & Full Width Layout
st.set_page_config(
    page_title="VeriData AI — Product Intelligence Auditor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS to hide the sidebar toggle button completely
st.markdown(
    """
    <style>
        [data-testid="collapsedControl"] {display: none;}
        section[data-testid="stSidebar"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("⚡ VeriData AI: E-Commerce Product Intelligence")
st.subheader("Transform Unstructured Technical Datasheets into Verified Catalog Specs")
st.caption("Powered by **SWAG HACKERS** • Dual-agent framework for catalog enrichment & anti-hallucination verification")
st.markdown("---")

# Automatically retrieve API Key from Streamlit Secrets
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ Secrets Error: 'GEMINI_API_KEY' is missing in Streamlit Secrets setup. Please add it to Secrets Manager.")
    st.stop()

genai.configure(api_key=api_key)

# Dynamic Function: Dynamically fetch and pick the latest active Flash model available to your API key
@st.cache_resource
def get_latest_flash_model():
    try:
        available_models = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods and 'flash' in m.name.lower()
        ]
        if available_models:
            # Picks the newest/latest flash model returned by Google API
            latest_model_name = available_models[-1]
            return genai.GenerativeModel(latest_model_name)
    except Exception as e:
        pass
    
    # Fallback to standard active flash models if list_models fails
    for fallback in ['models/gemini-1.5-flash', 'gemini-1.5-flash', 'models/gemini-1.0-flash']:
        try:
            return genai.GenerativeModel(fallback)
        except Exception:
            continue
            
    return genai.GenerativeModel('gemini-1.5-flash')

model = get_latest_flash_model()

# Helper function to extract text from PDF
def extract_text_from_pdf(uploaded_file):
    pdf_reader = pypdf.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

# Main Ingestion Interface
uploaded_file = st.file_uploader("Upload Product Datasheet (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Extracting text from PDF..."):
        raw_text = extract_text_from_pdf(uploaded_file)
    
    st.success(f"Successfully loaded '{uploaded_file.name}'!")
    
    with st.expander("📄 View Raw Extracted Datasheet Text"):
        st.text(raw_text[:2000] + ("..." if len(raw_text) > 2000 else ""))

    if st.button("🚀 Process & Audit Product Specs"):
        col1, col2 = st.columns(2)

        # AGENT 1: Data Enrichment Generator
        with col1:
            st.markdown("### 🤖 Agent 1: Spec Generator")
            with st.spinner("Generating structured product specifications..."):
                gen_prompt = f"""
                You are an e-commerce product catalog specialist. Extract product specifications from this technical document into structured key-value pairs.
                
                Document Content:
                {raw_text[:4000]}
                
                Return ONLY a valid JSON object formatted as follows:
                {{
                    "product_name": "Name",
                    "category": "Category",
                    "specifications": {{
                        "Operating Voltage": "value",
                        "Dimensions": "value",
                        "Key Features": "value"
                    }}
                }}
                """
                
                try:
                    gen_response = model.generate_content(gen_prompt)
                    gen_text = gen_response.text.strip().replace("```json", "").replace("```", "")
                    parsed_specs = json.loads(gen_text)
                    st.json(parsed_specs)
                except Exception as e:
                    st.error(f"Generation error: {e}")
                    parsed_specs = None

        # AGENT 2: Anti-Hallucination Auditor
        with col2:
            st.markdown("### 🛡️ Agent 2: Verification Auditor")
            if parsed_specs:
                with st.spinner("Auditing generated specs against raw source text..."):
                    audit_prompt = f"""
                    You are a strict data auditor. Verify whether the following extracted product specifications are accurately supported by the raw source text.
                    
                    Raw Source Text:
                    {raw_text[:4000]}
                    
                    Extracted Specifications:
                    {json.dumps(parsed_specs)}
                    
                    Identify any hallucinated, ungrounded, or incorrect specs.
                    Return ONLY a JSON object:
                    {{
                        "faithfulness_score": 0.95,
                        "status": "APPROVED or FLAGGED",
                        "flagged_discrepancies": ["list any discrepancies or state None"],
                        "source_citations": ["quote exact supporting text from source"]
                    }}
                    """
                    try:
                        audit_response = model.generate_content(audit_prompt)
                        audit_text = audit_response.text.strip().replace("```json", "").replace("```", "")
                        audit_results = json.loads(audit_text)
                        
                        score = audit_results.get("faithfulness_score", 0.0)
                        
                        if score >= 0.85:
                            st.success(f"✅ Faithfulness Score: {score * 100:.1f}% — Verification Passed!")
                        else:
                            st.warning(f"⚠️ Faithfulness Score: {score * 100:.1f}% — Action Required!")
                            
                        st.json(audit_results)
                    except Exception as e:
                        st.error(f"Audit error: {e}")
