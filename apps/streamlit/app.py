"""Minimal Member 360 portfolio interface."""

import os

import httpx
import streamlit as st

API_URL = os.getenv("CUSTOMER360_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Member 360", layout="wide")
st.title("Member 360 AI Data Platform")
st.caption("Synthetic data only — portfolio demonstration")

role = st.selectbox("Persona", ["analyst", "analytics"])
response = httpx.get(f"{API_URL}/api/v1/members", headers={"X-Role": role}, timeout=10)
if response.is_success:
    members = response.json()
    selected = st.selectbox(
        "Member", members, format_func=lambda member: str(member["source_member_id"])
    )
    st.subheader("Trusted serving projection")
    st.json(selected)
else:
    st.error(f"API unavailable: {response.status_code} {response.text}")
