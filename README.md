# Automotive Web Research Tool MVP

## Features
- Paste an OEM / official distributor URL
- Extract candidate model links
- Select model pages and scan common spec fields
- Export Excel with source URLs

## Local
pip install -r requirements.txt
streamlit run streamlit_app.py

## Multi-user deployment
Upload these files to a GitHub repository, then deploy `streamlit_app.py` on Streamlit Community Cloud and share the generated URL.

## Limitation
This is a research-assistance MVP. JavaScript-only pages, anti-bot protection, PDFs, configurators, and unusual OEM structures can require site-specific adapters.
