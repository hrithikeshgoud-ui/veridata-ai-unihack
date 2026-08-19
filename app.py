import streamlit as st
import pandas as pd
import pypdf
import json
import io
import google.generativeai as genai

# Streamlit Page Configuration
st.set_page_config(
    page_title="VeriData AI — Multi-Format Catalog Auditor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS: Hide Sidebar & Clean Up UI
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
st.subheader("Multi-Format SKU Enrichment & Anti-Hallucination Audit Pipeline")
st.caption("Developed by **SWAG HACKERS** • Dual-Agent AI Framework for Unilog UniHack")
st.markdown("---")

# Retrieve API Key from Streamlit Secrets
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ Secrets Error: 'GEMINI_API_KEY' is missing in Streamlit Secrets setup.")
    st.stop()

genai.configure(api_key=api_key)

# Dynamic Free-Tier Flash Model Selector
@st.cache_resource
def get_latest_gemini_flash_model():
    try:
        all_models = genai.list_models()
        valid_flash_models = [
            m.name.replace("models/", "") for m in all_models 
            if 'generateContent' in m.supported_generation_methods 
            and 'flash' in m.name.lower()
            and not any(x in m.name.lower() for x in ['omni', 'experimental', 'exp', 'preview'])
        ]
        if valid_flash_models:
            valid_flash_models.sort(reverse=True)
            return genai.GenerativeModel(valid_flash_models[0])
    except Exception:
        pass

    for fallback in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash"]:
        try:
            return genai.GenerativeModel(fallback)
        except Exception:
            continue
            
    return genai.GenerativeModel("gemini-2.5-flash")

model = get_latest_gemini_flash_model()

# Helper: Extract text from PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = pypdf.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

# Ingestion Interface Supporting Excel, CSV, and PDF
uploaded_file = st.file_uploader(
    "Upload Product Document or Dataset (PDF, XLSX, or CSV)", 
    type=["pdf", "xlsx", "csv"]
)

if uploaded_file:
    file_type = uploaded_file.name.split(".")[-1].lower()

    # ----------------------------------------------------
    # MODE 1: EXCEL / CSV DATASET PROCESSING
    # ----------------------------------------------------
    if file_type in ["xlsx", "csv"]:
        if file_type == "csv":
            df_input = pd.read_csv(uploaded_file)
        else:
            df_input = pd.read_excel(uploaded_file)

        st.success(f"Successfully loaded dataset: '{uploaded_file.name}' ({len(df_input)} rows)")
        st.markdown("### 📋 Uploaded Dataset Preview")
        st.dataframe(df_input.head(5), use_container_width=True)

        if st.button("🚀 Run Dual-Agent Batch Enrichment"):
            output_rows = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, row in df_input.iterrows():
                row_dict = row.dropna().to_dict()
                status_text.text(f"Processing row {idx + 1} of {len(df_input)}...")

                # Agent 1: Spec Generator
                gen_prompt = f"""
                You are an expert e-commerce catalog taxonomist for B2B industrial products.
                Enrich the following minimal product information into standard technical commerce attributes.

                Input Data:
                {json.dumps(row_dict)}

                Extract and infer standard specifications.
                Return ONLY a valid JSON object:
                {{
                    "Standardized_Title": "Full descriptive title",
                    "Category": "Product Category",
                    "Key_Features": "Comma-separated key features",
                    "Specifications": {{
                        "Voltage / Power": "value or N/A",
                        "Dimensions / Size": "value or N/A",
                        "Material / Build": "value or N/A",
                        "Operating Temp": "value or N/A"
                    }}
                }}
                """
                try:
                    res1 = model.generate_content(gen_prompt)
                    gen_text = res1.text.strip().replace("```json", "").replace("```", "")
                    enriched = json.loads(gen_text)
                except Exception as e:
                    enriched = {"error": str(e)}

                # Agent 2: Auditor
                audit_prompt = f"""
                You are a data validation auditor. Verify the faithfulness and accuracy of the enriched catalog data against the initial product input.

                Input Data:
                {json.dumps(row_dict)}

                Enriched Data:
                {json.dumps(enriched)}

                Return ONLY a valid JSON object:
                {{
                    "Faithfulness_Score": 0.95,
                    "Audit_Status": "APPROVED or FLAGGED",
                    "Verification_Notes": "Short summary of verification"
                }}
                """
                try:
                    res2 = model.generate_content(audit_prompt)
                    audit_text = res2.text.strip().replace("```json", "").replace("```", "")
                    audit = json.loads(audit_text)
                except Exception as e:
                    audit = {"Faithfulness_Score": 0.0, "Audit_Status": "ERROR", "Verification_Notes": str(e)}

                # Combine row
                combined_row = {**row_dict}
                if "error" not in enriched:
                    combined_row["Standardized_Title"] = enriched.get("Standardized_Title", "")
                    combined_row["Category"] = enriched.get("Category", "")
                    combined_row["Key_Features"] = enriched.get("Key_Features", "")
                    
                    specs = enriched.get("Specifications", {})
                    for k, v in specs.items():
                        combined_row[f"Spec_{k}"] = v
                
                combined_row["Faithfulness_Score"] = audit.get("Faithfulness_Score", 0.0)
                combined_row["Audit_Status"] = audit.get("Audit_Status", "UNKNOWN")
                combined_row["Audit_Notes"] = audit.get("Verification_Notes", "")

                output_rows.append(combined_row)
                progress_bar.progress((idx + 1) / len(df_input))

            status_text.success("✅ Batch Enrichment & Verification Complete!")
            df_output = pd.DataFrame(output_rows)

            st.markdown("### 📊 Enriched & Audited Output")
            st.dataframe(df_output, use_container_width=True)

            # Export to Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_output.to_excel(writer, index=False, sheet_name='Enriched_Catalog')
            
            st.download_button(
                label="📥 Download Completed Expected Output Sheet (.xlsx)",
                data=buffer.getvalue(),
                file_name="Enriched_Product_Output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # ----------------------------------------------------
    # MODE 2: UNSTRUCTURED PDF DATASHEET PROCESSING
    # ----------------------------------------------------
    elif file_type == "pdf":
        with st.spinner("Extracting text from PDF..."):
            raw_text = extract_text_from_pdf(uploaded_file)
        
        st.success(f"Successfully loaded '{uploaded_file.name}'!")
        with st.expander("📄 View Raw Extracted Datasheet Text"):
            st.text(raw_text[:2000] + ("..." if len(raw_text) > 2000 else ""))

        if st.button("🚀 Process & Audit PDF Specs"):
            col1, col2 = st.columns(2)

            # Agent 1: Spec Generator
            with col1:
                st.markdown("### 🤖 Agent 1: Spec Generator")
                with st.spinner("Generating structured catalog specifications..."):
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

            # Agent 2: Verification Auditor
            with col2:
                st.markdown("### 🛡️ Agent 2: Verification Auditor")
                if parsed_specs:
                    with st.spinner("Auditing generated specs against raw text..."):
                        audit_prompt = f"""
                        You are a strict data auditor. Verify whether the following extracted product specifications are accurately supported by the raw source text.
                        
                        Raw Source Text:
                        {raw_text[:4000]}
                        
                        Extracted Specifications:
                        {json.dumps(parsed_specs)}
                        
                        Identify any hallucinated or ungrounded specs.
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
