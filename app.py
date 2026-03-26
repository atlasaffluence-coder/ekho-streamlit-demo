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
```

4. Scroll down to **"Commit new file"**.
5. In the commit message field, type:
```
   Add app.py skeleton
