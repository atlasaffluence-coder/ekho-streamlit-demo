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

# --- Sidebar: Global Controls ---
with st.sidebar:
    st.header("Case Management")

    st.selectbox(
        label="Active Workspace",
        options=["demo-workspace-001"],
        key="workspace_id"
    )

    st.divider()

    st.subheader("Document Ingestion")

# --- Main Stage: Dual-Pane Layout ---
col_chat, col_evidence = st.columns([2, 3])

with col_chat:
    st.subheader("Query Interface")

with col_evidence:
    st.subheader("Evidence Panel")
    st.caption("Click a citation in the chat to view the source text.")
