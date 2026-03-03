"""Unified secrets access: Streamlit Cloud secrets -> .env -> os.environ fallback."""

import os


def get_secret(key, default=""):
    """Get a secret value. Checks Streamlit secrets first, then .env/os.environ."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    return os.getenv(key, default)
