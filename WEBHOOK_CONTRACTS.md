# EKHO Demo — Webhook Contracts

**Version:** 1.0  
**Status:** Authoritative  
**Scope:** Demo only (single-tenant, synchronous, Make.com + OpenAI + Supabase)

This document is the single source of truth for the interface between Streamlit (frontend) and Make.com (backend). Both sides must conform exactly to the shapes defined here. Do not deviate without updating this document first.

---

## 1. Ingestion Webhook

### Purpose
Receives a document file from Streamlit, processes it through OCR, chunks the output, generates embeddings, and inserts all chunks into Supabase. Returns a confirmation once all rows are inserted.

### Endpoint
```
POST {MAKE_INGESTION_WEBHOOK_URL}
```
Placeholder in `app.py`: `YOUR_MAKE_INGESTION_WEBHOOK_URL`

---

### Request (Streamlit → Make.com)

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | binary | Yes | The raw file bytes. Filename and MIME type are included by the `requests` library automatically via the `files=` parameter. |
| `workspace_id` | string | Yes | The active workspace identifier. Current demo value: `demo-workspace-001`. |

**How Streamlit sends this:**
```python
requests.post(
    url="YOUR_MAKE_INGESTION_WEBHOOK_URL",
    files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
    data={"workspace_id": st.session_state.workspace_id},
    timeout=120
)
```

**Supported file types:** `.pdf`, `.docx`  
**Maximum file size:** 25MB (enforced in Streamlit before the request is sent)

---

### Response (Make.com → Streamlit)

**HTTP Status:** `200 OK`  
**Content-Type:** `application/json`

```json
{
  "status": "indexed",
  "document_id": "<uuid>",
  "chunk_count": 14
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | string | Yes | Must be the literal string `"indexed"` on success. |
| `document_id` | string (UUID) | Yes | The UUID of the row inserted into the `documents` table. |
| `chunk_count` | integer | Yes | The number of chunk rows inserted into `document_chunks`. Used for verification. |

**What Streamlit does with this response:**  
Streamlit currently checks only `response.status_code == 200`. A `200` triggers the "Document indexed successfully" status update and adds the filename to `st.session_state.doc_status`. The response body fields (`document_id`, `chunk_count`) are not yet consumed by the UI but must be present for future steps.

**Error response (any non-200):**  
Make.com should return a non-200 status code if any step in the pipeline fails. Streamlit will display the raw `response.text` in an error banner. No specific error body shape is required — plain text is acceptable.

---

### Chunking Parameters (Fixed — Do Not Deviate)

| Parameter | Value |
|---|---|
| Chunk size | 1000 characters |
| Overlap | 200 characters |
| Split boundary | Whitespace (do not split mid-word) |

These parameters must be applied consistently in Make.com's text splitting step. Changing them after data is inserted requires a full table wipe and re-ingestion.

---

### Supabase Insert Target

Each chunk must produce one row in `document_chunks` with the following fields populated:

| Column | Source |
|---|---|
| `document_id` | UUID of the parent document row |
| `workspace_id` | String from the webhook 'workspace_id' field — dedicated column |
| `chunk_index` | Integer, 0-based, incrementing per chunk |
| `page_number` | `null` on all inserts |
| `content` | The raw text of the chunk |
| `embedding` | Float array of length 1536 from OpenAI `text-embedding-3-small` |
| `created_at` | Auto-populated by Supabase default |


**Supabase insert headers required:**
```
apikey: {SUPABASE_SERVICE_ROLE_KEY}
Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}
Content-Type: application/json
Prefer: return=minimal
```

> ⚠️ Use the **service role key**, not the anon key. The anon key will be blocked by RLS on insert unless policies are explicitly configured to allow it.

---

## 2. Query Webhook

### Purpose
Receives a natural-language question and a workspace ID from Streamlit. Embeds the query, runs a vector similarity search against `document_chunks`, assembles context, calls the OpenAI chat completion API, and returns a structured response with the answer, citations, raw chunks, and a confidence indicator.

### Endpoint
```
POST {MAKE_QUERY_WEBHOOK_URL}
```
Placeholder in `app.py`: `YOUR_MAKE_QUERY_WEBHOOK_URL`

---

### Request (Streamlit → Make.com)

**Content-Type:** `application/json`

```json
{
  "query": "What are the termination conditions in clause 12?",
  "workspace_id": "demo-workspace-001"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | The raw user question as typed into the chat input. |
| `workspace_id` | string | Yes | The active workspace. Used to filter `document_chunks` so retrieval is scoped to the correct document set. |

**How Streamlit sends this:**
```python
requests.post(
    url="YOUR_MAKE_QUERY_WEBHOOK_URL",
    json={
        "query": user_query,
        "workspace_id": st.session_state.workspace_id
    },
    timeout=60
)
```

---

### Response (Make.com → Streamlit)

**HTTP Status:** `200 OK`  
**Content-Type:** `application/json`

```json
{
  "answer": "Clause 12 permits termination with 30 days written notice by either party in the event of a material breach.",
  "fallback": false,
  "confidence": 0.87,
  "citations": [
    {
      "label": "Contract A, p.4",
      "document": "Contract A",
      "page": 4,
      "snippet": "Either party may terminate this agreement upon 30 days written notice following a material breach that remains uncured..."
    }
  ],
  "chunks": [
    "Either party may terminate this agreement upon 30 days written notice following a material breach that remains uncured for a period of 14 days after written notification of such breach.",
    "Termination shall not relieve either party of obligations incurred prior to the effective date of termination."
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `answer` | string | Yes | The LLM-generated answer. Must be an empty string `""` (not null) if no answer can be produced. |
| `fallback` | boolean | Yes | Set to `true` if no relevant chunks were found or the LLM could not produce a grounded answer. Streamlit renders a warning instead of a normal response when this is `true`. |
| `confidence` | float | Yes | A value between `0.0` and `1.0`. Can be derived from the top chunk's cosine similarity score. Pass `null` if not calculable — Streamlit will simply not render the confidence caption. |
| `citations` | array | Yes | Array of citation objects (see below). Pass an empty array `[]` if no citations are available. Must not be `null`. |
| `chunks` | array | Yes | Array of raw chunk strings — all chunks retrieved from Supabase, regardless of whether the LLM cited them. Used in the Audit Trail expander. Pass an empty array `[]` if none. Must not be `null`. |

---

### Citation Object Shape

Each object in the `citations` array must conform exactly to this shape:

```json
{
  "label": "Contract A, p.4",
  "document": "Contract A",
  "page": 4,
  "snippet": "Raw text excerpt from the source chunk..."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Short display string shown on the citation button in the UI. Format: `"{document name}, p.{page}"`. |
| `document` | string | Yes | The source document name. Used in the Evidence Panel header. |
| `page` | integer | Yes | Page number. Use `0` if unknown — Streamlit will display `"p.0"` rather than crash. Do not pass `null`. |
| `snippet` | string | Yes | The raw text excerpt shown in the Evidence Panel `st.info()` block. Should be the full content of the source chunk, not a truncated version. |

**What Streamlit does with citations:**  
Each citation renders as an `st.button`. Clicking a button sets `st.session_state.active_citation` to that citation object and forces a rerun, which populates the Evidence Panel on the right with `document`, `page`, and `snippet`.

---

### Fallback Behaviour

When `fallback: true`, Streamlit renders a `st.warning()` with either:
- The `answer` string if it is non-empty (e.g., `"I couldn't find relevant information for this query."`)
- A hardcoded fallback: `"I couldn't find relevant information in the current document set."`

Make.com should set `fallback: true` when:
- The vector search returns zero chunks for the given `workspace_id`
- All retrieved chunks have cosine similarity below a minimum threshold (suggested: `< 0.3`)
- The LLM returns a response indicating it cannot answer from the provided context

---

### Vector Search Parameters

| Parameter | Value |
|---|---|
| Embedding model | `text-embedding-3-small` |
| Similarity metric | Cosine (`<=>` operator in pgvector) |
| Top-k chunks retrieved | 5 |
| Workspace filter | `WHERE workspace_id = {workspace_id}` — mandatory |

> ⚠️ The `<=>` cosine similarity operator cannot be used directly in a PostgREST REST filter. A Postgres RPC function is required. See note below.

**Required Supabase RPC function (run once in Supabase SQL editor):**
```sql
CREATE OR REPLACE FUNCTION match_chunks(
  query_embedding VECTOR(1536),
  match_workspace_id TEXT,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  document_id UUID,
  content TEXT,
  chunk_index INTEGER,
  page_number INTEGER,
  similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
  SELECT
    dc.id,
    dc.document_id,
    dc.content,
    dc.chunk_index,
    dc.page_number,
    1 - (dc.embedding <=> query_embedding) AS similarity
  FROM document_chunks dc
  WHERE dc.workspace_id = match_workspace_id
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
$$;
```

**Make.com RPC call:**
```
POST {SUPABASE_URL}/rest/v1/rpc/match_chunks
Headers:
  apikey: {SUPABASE_SERVICE_ROLE_KEY}
  Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}
  Content-Type: application/json

Body:
{
  "query_embedding": [0.012, -0.034, ...],  // 1536 floats from OpenAI
  "match_workspace_id": "demo-workspace-001",
  "match_count": 5
}
```

---

## 3. Shared Constraints

| Constraint | Value |
|---|---|
| LLM model | `gpt-4o-mini` (or `gpt-4o` — do not use `gpt-3.5-turbo`) |
| Embedding model | `text-embedding-3-small` |
| Embedding dimensions | 1536 |
| Workspace isolation | Enforced at query time via `workspace_id` filter — never return chunks from a different workspace |
| Make.com timeout | Ingestion scenario: configure max execution time to match Streamlit's `timeout=120`. Query scenario: must complete within Streamlit's `timeout=60`. |
| Streamlit ingestion timeout | 120 seconds |
| Streamlit query timeout | 60 seconds |

---

## 4. What Make.com Must Never Do

- Return `null` for `citations`, `chunks`, or `answer` — use empty arrays `[]` and empty string `""` respectively
- Return a `200` status before all chunk inserts are confirmed
- Mix chunks from different `workspace_id` values in a single query response
- Return a response body that omits any field listed as Required in this document

---

## 5. Resolved Decisions

| Decision | Resolution |
|---|---|
| Timeout strategy | Synchronous — demo files assumed to complete within 40s |
| LlamaParse file delivery | Upload file to Supabase Storage first, pass public URL to LlamaParse |
| `page_number` availability | Set to `null` on all inserts |
