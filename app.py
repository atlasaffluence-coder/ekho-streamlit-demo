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
    
    uploaded_file = st.file_uploader(
        label="Upload a document",
        type=["pdf", "docx"],
        help="Maximum file size: 25MB"
    )

    if uploaded_file is not None:
        if uploaded_file.size > 25 * 1024 * 1024:
            st.error("File exceeds the 25MB limit. Please upload a smaller file.")
            uploaded_file = None
    
    if uploaded_file is not None:
        if st.button("Process Document"):
            with st.status("Processing document...", expanded=True) as status:
                try:
                    response = requests.post(
                        url="YOUR_MAKE_INGESTION_WEBHOOK_URL",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                        data={"workspace_id": st.session_state.workspace_id},
                        timeout=120
                    )
                    if response.status_code == 200:
                        st.session_state.doc_status[uploaded_file.name] = "Indexed"
                        status.update(label="Document indexed successfully.", state="complete")
                    else:
                        status.update(label="Make.com returned an error. Check your webhook.", state="error")
                        st.error(f"Error {response.status_code}: {response.text}")
                except requests.exceptions.Timeout:
                    status.update(label="Request timed out after 2 minutes.", state="error")
                    st.error("The document took too long to process. Try a smaller file or check Make.com.")
                except requests.exceptions.RequestException as e:
                    status.update(label="Connection error.", state="error")
                    st.error(f"Could not reach Make.com: {e}")

    if st.session_state.doc_status:
        st.divider()
        st.subheader("Indexed Documents")
        for doc_name, doc_state in st.session_state.doc_status.items():
            st.success(f"✅ {doc_name}")

# --- Main Stage: Dual-Pane Layout ---
col_chat, col_evidence = st.columns([2, 3])

with col_chat:
    st.subheader("Query Interface")

with col_evidence:
    st.subheader("Evidence Panel")
    st.caption("Click a citation in the chat to view the source text.")
