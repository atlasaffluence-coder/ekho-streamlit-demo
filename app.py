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
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

with col_evidence:
    st.subheader("Evidence Panel")
    if st.session_state.active_citation:
        citation = st.session_state.active_citation
        st.markdown(f"**{citation.get('document', 'Document')}** — Page {citation.get('page', 'N/A')}")
        st.info(citation.get("snippet", "No text snippet available."))
    else:
        st.caption("Click a citation in the chat to view the source text.")

# --- Chat Input (root level — Streamlit constraint) ---
user_query = st.chat_input("Ask a question about your documents...")

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})

    with col_chat:
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.status("Searching case file...", expanded=True) as status:
            try:
                response = requests.post(
                    url="YOUR_MAKE_QUERY_WEBHOOK_URL",
                    json={
                        "query": user_query,
                        "workspace_id": st.session_state.workspace_id
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    payload = response.json()
                    answer = payload.get("answer", "")
                    fallback = payload.get("fallback", False)
                    citations = payload.get("citations", [])
                    chunks = payload.get("chunks", [])
                    confidence = payload.get("confidence", None)
                    status.update(label="Done.", state="complete")
                else:
                    answer = None
                    fallback = True
                    citations = []
                    chunks = []
                    confidence = None
                    status.update(label="Make.com returned an error.", state="error")

            except requests.exceptions.Timeout:
                answer = None
                fallback = True
                citations = []
                chunks = []
                confidence = None
                status.update(label="Query timed out.", state="error")
                st.error("The query took too long. Please try again.")

            except requests.exceptions.RequestException as e:
                answer = None
                fallback = True
                citations = []
                chunks = []
                confidence = None
                status.update(label="Connection error.", state="error")
                st.error(f"Could not reach Make.com: {e}")

        if answer is not None:
            with st.chat_message("assistant"):
                if fallback or not answer.strip():
                    display_text = answer if answer.strip() else "I couldn't find relevant information in the current document set."
                    st.warning(display_text)
                    st.session_state.messages.append({"role": "assistant", "content": display_text})
                else:
                    st.markdown(answer)
                    if confidence:
                        st.caption(f"Confidence: {confidence}")

                    st.session_state.messages.append({"role": "assistant", "content": answer})

                    if citations:
                        st.write("")
                        citation_cols = st.columns(len(citations))
                        for i, citation in enumerate(citations):
                            with citation_cols[i]:
                                label = citation.get("label", f"[{i+1}]")
                                if st.button(label, key=f"cite_{i}_{user_query[:10]}"):
                                    st.session_state.active_citation = citation

                    if chunks:
                        with st.expander("Audit Trail"):
                            for i, chunk in enumerate(chunks):
                                st.markdown(f"**Chunk {i+1}**")
                                st.text(chunk)
                                st.divider()
