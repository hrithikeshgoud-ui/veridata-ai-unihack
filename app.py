import streamlit as st
import pypdf
import json
import google.generativeai as genai

# Streamlit Page Setup
st.set_page_config(
    page_title="VeriData AI — Product Intelligence Auditor",
    page_icon="⚡",
    layout="wide"
)

# Sidebar - API Key Configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.info("Obtain a free API key from Google AI Studio.")
    st.markdown("---")
    st.markdown("### About VeriData AI")
    st.write("Dual-agent framework for e-commerce catalog enrichment and anti-hallucination verification.")

st.title("⚡ VeriData AI: E-Commerce Product Intelligence")
st.subheader("Transform Unstructured Technical Datasheets into Verified Catalog Specs")

# Helper function to extract text from PDF
def extract_text_from_pdf(uploaded_file):
    pdf_reader = pypdf.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

# Main Ingestion Interface
uploaded_file = st.file_uploader("Upload Product Datasheet (PDF)", type=["pdf"])

if uploaded_file and api_key:
    genai.configure(api_key=api_key)
    
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
                    model = genai.GenerativeModel('gemini-1.5-flash')
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

elif not api_key:
    st.info("👈 Enter your Gemini API Key in the sidebar to start processing.")
