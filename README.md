# VeriData AI — E-Commerce Data Enrichment & Anti-Hallucination Audit System

> Developed for UniHack 2026 (Unilog AI Hackathon)

VeriData AI is a dual-agent framework that transforms unstructured technical datasheets into verified, commerce-ready product intelligence with source attribution and hallucination detection.

## Key Features
- **Multi-Format Ingestion:** Extracts specs from PDFs, text, and unstructured Web URLs.
- **Dual-Agent Verification:** Generates product descriptions while an independent auditor agent cross-checks claims against source files.
- **Explainable AI:** Highlights exact source citations (page & paragraph) with confidence scores.
- **Human-in-the-Loop (HITL):** Low-confidence or conflicting data is automatically flagged for admin review.

## Quick Start
```bash
git clone https://github.com/hrithikeshgoud-ui/veridata-ai-unihack.git
cd veridata-ai-unihack
pip install -r requirements.txt
streamlit run frontend/app.py

