"""
EKHO STREAMLIT UI — HARD CONSTRAINTS
This application is UI-ONLY.
It must NOT process documents, chunk text, query Supabase, or perform any AI reasoning.
All logic lives in Make.com. Streamlit only sends HTTP requests and renders responses.
"""

import streamlit as st
import requests

st.set_page_config(page_title="EKHO Demo", layout="wide")
st.title("EKHO Legal Intelligence")
# --- Session State Initialization ---
# Must run before any layout is defined.

if "workspace_id" not in st.session_state:
    st.session_state.workspace_id = "demo-workspace-001"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "active_citation" not in st.session_state:
    st.session_state.active_citation = None

if "doc_status" not in st.session_state:
    st.session_state.doc_status = {}
```

4. Scroll down to **"Commit changes"**.
5. In the commit message field, type:
```
   Add session state initialization
