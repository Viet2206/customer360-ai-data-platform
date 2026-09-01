"""Professional Member 360 portfolio interface."""

from __future__ import annotations

import os
from datetime import datetime
from html import escape
from typing import Any

import httpx
import streamlit as st

API_URL = os.getenv("CUSTOMER360_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Member 360 | Insurance Intelligence",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _safe(value: Any) -> str:
    return escape(str(value if value not in (None, "") else "—"))


def _present(value: Any) -> Any:
    return "Restricted" if value == "***" else value


def _money(value: Any) -> str:
    return f"${float(value or 0):,.2f}"


def _pretty_date(value: Any) -> str:
    if value in (None, "", "***"):
        return "Restricted" if value == "***" else "—"
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").strftime("%b %d, %Y")
    except ValueError:
        return str(value)


def _initials(name: Any) -> str:
    if name in (None, "", "***"):
        return "M"
    parts = str(name).split()
    return "".join(part[0] for part in parts[:2]).upper()


def _member_label(member: dict[str, Any]) -> str:
    source_id = str(member.get("source_member_id", "Unknown"))
    name = member.get("full_name")
    suffix = "Restricted identity" if name == "***" else str(name or "Unknown member")
    return f"{source_id}  ·  {suffix}"


@st.cache_data(ttl=10, show_spinner=False)
def _load_members(api_url: str, role: str) -> list[dict[str, Any]]:
    response = httpx.get(f"{api_url}/api/v1/members", headers={"X-Role": role}, timeout=10)
    response.raise_for_status()
    return list(response.json())


def _ask_assistant(api_url: str, question: str) -> dict[str, Any]:
    response = httpx.post(f"{api_url}/api/v1/assistant", json={"question": question}, timeout=30)
    if response.status_code == 503:
        return {"unavailable": True}
    response.raise_for_status()
    return dict(response.json())


def _metric_card(label: str, value: str, note: str, accent: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card" style="--metric-accent:{accent}">
          <div class="metric-label">{escape(label)}</div>
          <div class="metric-value">{escape(value)}</div>
          <div class="metric-note">{escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
    :root {
      --ink: #102a43;
      --muted: #627d98;
      --line: #d9e2ec;
      --surface: #ffffff;
      --canvas: #f3f6fa;
      --navy: #0b2139;
      --blue: #1268b3;
      --cyan: #0f8fa8;
      --green: #14845f;
      --amber: #c17618;
      --purple: #6849ad;
    }

    .stApp { background: var(--canvas); color: var(--ink); }
    header[data-testid="stHeader"] { background: transparent; height: 0; }
    #MainMenu, footer, [data-testid="stAppDeployButton"] { display: none; }
    .block-container { max-width: 1480px; padding: 2.1rem 2.8rem 4rem; }

    [data-testid="stSidebar"] {
      background: linear-gradient(175deg, #0b2139 0%, #102f50 100%);
      border-right: 0;
    }
    [data-testid="stSidebar"] > div { padding-top: 1.35rem; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: #eef6ff !important; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
      color: #9fc2df !important; font-size: .69rem; font-weight: 700;
      letter-spacing: .11em; text-transform: uppercase;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
      background: rgba(255,255,255,.09); border-color: rgba(255,255,255,.16); color: #fff;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.12); }

    .brand-lockup { display:flex; align-items:center; gap:.8rem; margin: .25rem 0 1.8rem; }
    .brand-mark {
      width:42px; height:42px; border-radius:12px; display:grid; place-items:center;
      background:linear-gradient(145deg,#2e8ad0,#1ab0a2); color:white; font-weight:800;
      box-shadow:0 9px 24px rgba(0,0,0,.2);
    }
    .brand-name { color:#fff; font-size:1rem; font-weight:750; letter-spacing:.01em; }
    .brand-sub { color:#9fc2df; font-size:.72rem; margin-top:.12rem; }
    .sidebar-section {
      color:#7fa8c8; font-size:.67rem; font-weight:750; letter-spacing:.13em;
      text-transform:uppercase; margin:1.4rem 0 .65rem;
    }
    .status-stack { display:grid; gap:.55rem; margin-top:.4rem; }
    .status-row {
      display:flex; justify-content:space-between; align-items:center; color:#cfe1f1;
      font-size:.76rem; padding:.55rem .65rem; border:1px solid rgba(255,255,255,.1);
      border-radius:10px; background:rgba(255,255,255,.04);
    }
    .status-dot { width:7px; height:7px; border-radius:50%; background:#4fd1a5; box-shadow:0 0 0 4px rgba(79,209,165,.12); }
    .sidebar-foot { color:#7fa8c8; font-size:.68rem; line-height:1.55; margin-top:1.5rem; }

    .workspace-header { display:flex; justify-content:space-between; align-items:flex-start; gap:2rem; margin:.2rem 0 1.35rem; }
    .eyebrow { color:var(--blue); font-size:.7rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; }
    .workspace-title { color:var(--ink); font-size:2.05rem; line-height:1.12; margin:.35rem 0 .28rem; font-weight:780; letter-spacing:-.035em; }
    .workspace-subtitle { color:var(--muted); font-size:.92rem; margin:0; }
    .header-badges { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:.5rem; padding-top:.25rem; }
    .soft-badge { padding:.42rem .68rem; border-radius:999px; font-size:.68rem; font-weight:750; white-space:nowrap; }
    .soft-badge.blue { color:#155d96; background:#e4f1fb; border:1px solid #c9e1f5; }
    .soft-badge.green { color:#116a4c; background:#e5f5ee; border:1px solid #c8e8da; }
    .soft-badge.amber { color:#8b5514; background:#fff3de; border:1px solid #f2d7a8; }

    .member-hero {
      position:relative; overflow:hidden; display:flex; justify-content:space-between; gap:2rem;
      padding:1.45rem 1.6rem; border-radius:18px; color:#fff;
      background:linear-gradient(118deg,#0b2947 0%,#104a76 62%,#0e7181 100%);
      box-shadow:0 14px 38px rgba(25,55,85,.16); margin-bottom:1rem;
    }
    .member-hero::after { content:""; position:absolute; width:260px; height:260px; border-radius:50%; right:-75px; top:-128px; background:rgba(255,255,255,.07); }
    .member-primary { display:flex; align-items:center; gap:1rem; position:relative; z-index:1; }
    .avatar { width:58px; height:58px; border-radius:17px; display:grid; place-items:center; background:rgba(255,255,255,.15); border:1px solid rgba(255,255,255,.18); font-size:1.2rem; font-weight:800; }
    .member-kicker { color:#a8d7ee; font-size:.66rem; font-weight:750; letter-spacing:.12em; text-transform:uppercase; }
    .member-name { font-size:1.45rem; font-weight:760; letter-spacing:-.02em; margin:.15rem 0 .25rem; }
    .member-meta { color:#d7ebf6; font-size:.78rem; }
    .member-secondary { display:flex; align-items:center; gap:2.2rem; position:relative; z-index:1; text-align:right; }
    .hero-detail-label { color:#9fcce3; font-size:.63rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; }
    .hero-detail-value { color:#fff; font-size:.88rem; font-weight:650; margin-top:.2rem; }
    .active-pill { display:inline-flex; align-items:center; gap:.42rem; padding:.4rem .64rem; border-radius:999px; background:rgba(79,209,165,.16); color:#bdf4df; font-size:.7rem; font-weight:750; border:1px solid rgba(114,231,191,.22); }
    .active-pill::before { content:""; width:7px; height:7px; border-radius:50%; background:#57d5aa; }

    .metric-card { background:var(--surface); border:1px solid #e1e8f0; border-top:3px solid var(--metric-accent); border-radius:15px; padding:1rem 1.05rem .92rem; min-height:122px; box-shadow:0 6px 18px rgba(31,59,88,.055); }
    .metric-label { color:var(--muted); font-size:.67rem; font-weight:750; letter-spacing:.08em; text-transform:uppercase; }
    .metric-value { color:var(--ink); font-size:1.55rem; line-height:1.15; font-weight:780; letter-spacing:-.035em; margin:.52rem 0 .28rem; }
    .metric-note { color:#829ab1; font-size:.7rem; }

    .stTabs [data-baseweb="tab-list"] { gap:.2rem; border-bottom:1px solid var(--line); margin-top:.65rem; }
    .stTabs [data-baseweb="tab"] { height:3rem; padding:0 1.05rem; color:#627d98; font-weight:650; font-size:.82rem; }
    .stTabs [aria-selected="true"] { color:var(--blue) !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color:var(--blue); height:3px; }
    .stTabs [data-baseweb="tab-panel"] { padding-top:1.15rem; }

    .detail-grid { display:grid; grid-template-columns:1.15fr .85fr; gap:1rem; }
    .panel { background:#fff; border:1px solid #e1e8f0; border-radius:16px; padding:1.15rem 1.25rem; box-shadow:0 5px 18px rgba(31,59,88,.045); }
    .panel-title { color:var(--ink); font-size:.88rem; font-weight:760; margin-bottom:.2rem; }
    .panel-subtitle { color:#829ab1; font-size:.7rem; margin-bottom:.85rem; }
    .info-grid { display:grid; grid-template-columns:1fr 1fr; gap:.75rem 1.1rem; }
    .info-item { padding:.68rem 0; border-bottom:1px solid #edf1f5; }
    .info-label { color:#829ab1; font-size:.63rem; font-weight:720; letter-spacing:.07em; text-transform:uppercase; }
    .info-value { color:#243b53; font-size:.82rem; font-weight:620; margin-top:.24rem; overflow-wrap:anywhere; }
    .allocation { display:flex; align-items:center; gap:1.15rem; margin-top:.55rem; }
    .donut { width:112px; height:112px; flex:0 0 112px; border-radius:50%; display:grid; place-items:center; background:conic-gradient(#1674bd 0 var(--plan-pct),#21a179 var(--plan-pct) 100%); position:relative; }
    .donut::before { content:""; width:74px; height:74px; border-radius:50%; background:#fff; position:absolute; }
    .donut-center { position:relative; z-index:1; text-align:center; color:var(--ink); font-size:1rem; font-weight:780; }
    .donut-center span { display:block; color:#829ab1; font-size:.57rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em; }
    .legend { display:grid; gap:.65rem; width:100%; }
    .legend-row { display:grid; grid-template-columns:9px 1fr auto; align-items:center; gap:.5rem; color:#486581; font-size:.72rem; }
    .legend-dot { width:9px; height:9px; border-radius:3px; }
    .legend-value { color:var(--ink); font-weight:700; }

    .coverage-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:.8rem; }
    .coverage-item { background:#fff; border:1px solid #e1e8f0; border-radius:14px; padding:1rem; }
    .coverage-label { color:#829ab1; font-size:.62rem; font-weight:750; text-transform:uppercase; letter-spacing:.08em; }
    .coverage-value { color:var(--ink); font-size:.9rem; font-weight:700; margin-top:.4rem; }
    .financial-bar { height:11px; width:100%; background:#dfe7ef; border-radius:999px; overflow:hidden; margin:.95rem 0 .65rem; display:flex; }
    .financial-bar .plan { background:#1674bd; }
    .financial-bar .member { background:#21a179; }
    .bar-labels { display:flex; justify-content:space-between; gap:1rem; color:#627d98; font-size:.7rem; }

    .assistant-hero { background:linear-gradient(120deg,#f0f5ff,#ecfbf8); border:1px solid #d5e6f4; border-radius:16px; padding:1.2rem 1.3rem; margin-bottom:.8rem; }
    .assistant-icon { display:inline-grid; place-items:center; width:34px; height:34px; border-radius:10px; background:#176cb0; color:#fff; font-weight:800; margin-right:.55rem; }
    .assistant-title { color:var(--ink); font-weight:760; font-size:1rem; }
    .assistant-copy { color:#627d98; font-size:.77rem; line-height:1.55; margin:.65rem 0 0; max-width:760px; }
    .answer-card { background:#fff; border:1px solid #cbe4d9; border-left:4px solid var(--green); border-radius:13px; padding:1rem 1.1rem; color:#243b53; font-size:.82rem; line-height:1.65; margin-top:.8rem; }
    .offline-card { background:#fff9ed; border:1px solid #efd6a8; border-left:4px solid var(--amber); border-radius:13px; padding:1rem 1.1rem; color:#7a4c14; font-size:.79rem; line-height:1.55; margin-top:.8rem; }

    .journey { display:grid; grid-template-columns:repeat(4,1fr); gap:.55rem; margin:.65rem 0 1rem; }
    .journey-step { position:relative; background:#fff; border:1px solid #e1e8f0; border-radius:13px; padding:.9rem; min-height:94px; }
    .journey-num { color:var(--blue); font-size:.61rem; font-weight:800; letter-spacing:.1em; }
    .journey-title { color:var(--ink); font-size:.8rem; font-weight:730; margin:.28rem 0 .2rem; }
    .journey-copy { color:#829ab1; font-size:.66rem; line-height:1.45; }
    .mono { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.69rem; overflow-wrap:anywhere; }
    .trust-note { display:flex; gap:.65rem; align-items:flex-start; padding:.85rem 1rem; background:#eaf3fb; border-radius:12px; color:#486581; font-size:.72rem; line-height:1.5; }
    .trust-note strong { color:#174f7c; }
    .page-foot { display:flex; justify-content:space-between; gap:1rem; color:#829ab1; font-size:.65rem; border-top:1px solid #dfe7ef; padding-top:.8rem; margin-top:1.4rem; }

    div[data-testid="stForm"] { background:#fff; border:1px solid #e1e8f0; border-radius:15px; padding:.35rem .8rem .65rem; }
    div[data-testid="stForm"] button { background:#176cb0; color:#fff; border:0; font-weight:700; }
    div[data-testid="stForm"] button:hover { background:#105a94; color:#fff; }

    @media (max-width: 900px) {
      .block-container { padding:1.25rem 1rem 3rem; }
      .workspace-header, .member-hero { flex-direction:column; }
      .header-badges { justify-content:flex-start; }
      .member-secondary { width:100%; text-align:left; justify-content:space-between; gap:1rem; }
      .detail-grid { grid-template-columns:1fr; }
      .coverage-grid { grid-template-columns:1fr 1fr; }
      .journey { grid-template-columns:1fr 1fr; }
    }
    @media (max-width: 520px) {
      .workspace-title { font-size:1.65rem; }
      .member-primary { align-items:flex-start; }
      .member-secondary { flex-wrap:wrap; }
      .info-grid, .coverage-grid, .journey { grid-template-columns:1fr; }
      .allocation { align-items:flex-start; flex-direction:column; }
      .page-foot { flex-direction:column; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.sidebar.markdown(
    """
    <div class="brand-lockup">
      <div class="brand-mark">360</div>
      <div><div class="brand-name">Member 360</div><div class="brand-sub">AI data platform</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

profile = st.sidebar.selectbox(
    "Access profile",
    ["Member services", "Analytics (masked)"],
    help="Analytics masks direct member identifiers at the API boundary.",
)
role = "analyst" if profile == "Member services" else "analytics"

try:
    members = _load_members(API_URL, role)
except (httpx.HTTPError, ValueError) as exc:
    st.markdown(
        '<div class="workspace-header"><div><div class="eyebrow">Platform status</div>'
        '<div class="workspace-title">Member 360 is unavailable</div>'
        '<p class="workspace-subtitle">The API could not return the trusted serving projection.</p>'
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.error(f"API connection failed: {exc}")
    st.stop()

if not members:
    st.warning("The serving projection is connected but contains no members.")
    st.stop()

selected = st.sidebar.selectbox("Member record", members, format_func=_member_label)

st.sidebar.markdown('<div class="sidebar-section">Platform status</div>', unsafe_allow_html=True)
st.sidebar.markdown(
    """
    <div class="status-stack">
      <div class="status-row"><span>Trusted API</span><span class="status-dot"></span></div>
      <div class="status-row"><span>Member projection</span><span class="status-dot"></span></div>
      <div class="status-row"><span>Gold lineage</span><span class="status-dot"></span></div>
    </div>
    <div class="sidebar-foot">Synthetic data only<br/>Local portfolio environment · v0.1.0</div>
    """,
    unsafe_allow_html=True,
)

name = selected.get("full_name")
display_name = "Restricted member" if name == "***" else str(name)
status = str(selected.get("coverage_status", "unknown")).title()
allowed = float(selected.get("total_allowed_amount") or 0)
member_responsibility = float(selected.get("total_member_responsibility") or 0)
plan_paid = max(allowed - member_responsibility, 0)
plan_percent = (plan_paid / allowed * 100) if allowed else 0
member_percent = 100 - plan_percent if allowed else 0
masked = role == "analytics"

st.markdown(
    f"""
    <div class="workspace-header">
      <div>
        <div class="eyebrow">Operations / Member intelligence</div>
        <div class="workspace-title">Member 360 workspace</div>
        <p class="workspace-subtitle">A governed view of identity, coverage, claims, and trusted AI evidence.</p>
      </div>
      <div class="header-badges">
        <span class="soft-badge blue">◆ Gold projection</span>
        <span class="soft-badge green">● API connected</span>
        <span class="soft-badge amber">Synthetic data</span>
      </div>
    </div>
    <div class="member-hero">
      <div class="member-primary">
        <div class="avatar">{_safe(_initials(name))}</div>
        <div>
          <div class="member-kicker">Selected member</div>
          <div class="member-name">{_safe(display_name)}</div>
          <div class="member-meta">{_safe(selected.get("source_member_id"))} &nbsp;·&nbsp; {_safe(selected.get("plan_name"))}</div>
        </div>
      </div>
      <div class="member-secondary">
        <div><div class="hero-detail-label">Policy</div><div class="hero-detail-value">{_safe(_present(selected.get("policy_number")))}</div></div>
        <div><div class="hero-detail-label">Coverage through</div><div class="hero-detail-value">{_safe(_pretty_date(selected.get("coverage_end")))}</div></div>
        <div><span class="active-pill">{escape(status)}</span></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_columns = st.columns(4)
with metric_columns[0]:
    _metric_card(
        "Annual deductible",
        _money(selected.get("annual_deductible")),
        "Current plan design",
        "#1268b3",
    )
with metric_columns[1]:
    _metric_card("Claims", str(selected.get("claim_count", 0)), "Aggregated in Gold", "#6849ad")
with metric_columns[2]:
    _metric_card("Total allowed", _money(allowed), "Across member claims", "#14845f")
with metric_columns[3]:
    _metric_card(
        "Member responsibility",
        _money(member_responsibility),
        f"{member_percent:.1f}% of allowed",
        "#c17618",
    )

overview_tab, coverage_tab, assistant_tab, lineage_tab = st.tabs(
    ["Overview", "Coverage & claims", "AI assistant", "Lineage & governance"]
)

with overview_tab:
    st.markdown(
        f"""
        <div class="detail-grid">
          <section class="panel">
            <div class="panel-title">Member profile</div>
            <div class="panel-subtitle">Direct identifiers respect the selected access profile.</div>
            <div class="info-grid">
              <div class="info-item"><div class="info-label">Date of birth</div><div class="info-value">{_safe(_pretty_date(selected.get("date_of_birth")))}</div></div>
              <div class="info-item"><div class="info-label">Golden member ID</div><div class="info-value mono">{_safe(selected.get("member_id"))}</div></div>
              <div class="info-item"><div class="info-label">Email</div><div class="info-value">{_safe(_present(selected.get("email")))}</div></div>
              <div class="info-item"><div class="info-label">Phone</div><div class="info-value">{_safe(_present(selected.get("phone")))}</div></div>
              <div class="info-item"><div class="info-label">Source member ID</div><div class="info-value">{_safe(selected.get("source_member_id"))}</div></div>
              <div class="info-item"><div class="info-label">Latest claim status</div><div class="info-value">{_safe(str(selected.get("latest_claim_status", "—")).title())}</div></div>
            </div>
          </section>
          <section class="panel">
            <div class="panel-title">Claim financial allocation</div>
            <div class="panel-subtitle">Derived from allowed amount and member responsibility.</div>
            <div class="allocation">
              <div class="donut" style="--plan-pct:{plan_percent:.2f}%"><div class="donut-center">{plan_percent:.0f}%<span>plan share</span></div></div>
              <div class="legend">
                <div class="legend-row"><span class="legend-dot" style="background:#1674bd"></span><span>Estimated plan paid</span><span class="legend-value">{_money(plan_paid)}</span></div>
                <div class="legend-row"><span class="legend-dot" style="background:#21a179"></span><span>Member responsibility</span><span class="legend-value">{_money(member_responsibility)}</span></div>
                <div class="legend-row"><span class="legend-dot" style="background:#dfe7ef"></span><span>Total allowed</span><span class="legend-value">{_money(allowed)}</span></div>
              </div>
            </div>
          </section>
        </div>
        """,
        unsafe_allow_html=True,
    )

with coverage_tab:
    st.markdown(
        f"""
        <div class="coverage-grid">
          <div class="coverage-item"><div class="coverage-label">Plan</div><div class="coverage-value">{_safe(selected.get("plan_name"))}</div></div>
          <div class="coverage-item"><div class="coverage-label">Plan ID</div><div class="coverage-value mono">{_safe(selected.get("plan_id"))}</div></div>
          <div class="coverage-item"><div class="coverage-label">Coverage starts</div><div class="coverage-value">{_safe(_pretty_date(selected.get("coverage_start")))}</div></div>
          <div class="coverage-item"><div class="coverage-label">Coverage ends</div><div class="coverage-value">{_safe(_pretty_date(selected.get("coverage_end")))}</div></div>
        </div>
        <section class="panel" style="margin-top:1rem">
          <div class="panel-title">Aggregate claims snapshot</div>
          <div class="panel-subtitle">Financial values reconcile to the current Gold serving record.</div>
          <div class="financial-bar"><span class="plan" style="width:{plan_percent:.2f}%"></span><span class="member" style="width:{member_percent:.2f}%"></span></div>
          <div class="bar-labels"><span>Plan share · {_money(plan_paid)}</span><span>Member share · {_money(member_responsibility)}</span></div>
          <div class="info-grid" style="margin-top:.8rem">
            <div class="info-item"><div class="info-label">Claim count</div><div class="info-value">{_safe(selected.get("claim_count"))}</div></div>
            <div class="info-item"><div class="info-label">Latest status</div><div class="info-value">{_safe(str(selected.get("latest_claim_status", "—")).title())}</div></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

with assistant_tab:
    st.markdown(
        """
        <div class="assistant-hero">
          <span class="assistant-icon">AI</span><span class="assistant-title">Ask trusted insurance evidence</span>
          <p class="assistant-copy">Questions are routed to the versioned knowledge index. Answers are returned with source metadata, or the assistant explicitly abstains when evidence is insufficient.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("assistant_query", clear_on_submit=False):
        question = st.text_input(
            "Question",
            placeholder="Example: What does the plan documentation say about deductibles?",
        )
        submitted = st.form_submit_button("Search trusted evidence")

    if submitted:
        if len(question.strip()) < 3:
            st.warning("Enter a question with at least three characters.")
        else:
            try:
                with st.spinner("Searching versioned evidence…"):
                    st.session_state["assistant_result"] = _ask_assistant(API_URL, question)
            except httpx.HTTPError as exc:
                st.session_state["assistant_result"] = {"error": str(exc)}

    assistant_result = st.session_state.get("assistant_result")
    if assistant_result:
        if assistant_result.get("unavailable"):
            st.markdown(
                """
                <div class="offline-card"><strong>Knowledge index not configured for this runtime.</strong><br/>
                Start the optional AI profile and publish the document index before querying. The member-serving experience remains available.</div>
                """,
                unsafe_allow_html=True,
            )
        elif assistant_result.get("error"):
            st.error(f"Assistant request failed: {assistant_result['error']}")
        else:
            grounded = bool(assistant_result.get("grounded"))
            answer = _safe(assistant_result.get("text"))
            label = "Grounded answer" if grounded else "Assistant abstained"
            st.markdown(
                f'<div class="answer-card"><strong>{label}</strong><br/>{answer}</div>',
                unsafe_allow_html=True,
            )
            citations = list(assistant_result.get("citations") or [])
            if citations:
                with st.expander(f"Evidence sources · {len(citations)}"):
                    for citation in citations:
                        st.markdown(
                            f"**{_safe(citation.get('title'))} — {_safe(citation.get('section'))}**  "
                            f"\n`{_safe(citation.get('source'))}` · version {_safe(citation.get('version'))}"
                        )

with lineage_tab:
    st.markdown(
        f"""
        <section class="panel">
          <div class="panel-title">Trusted data journey</div>
          <div class="panel-subtitle">Each serving record can be rebuilt and traced to a specific Gold pipeline run.</div>
          <div class="journey">
            <div class="journey-step"><div class="journey-num">01 · BRONZE</div><div class="journey-title">Source aligned</div><div class="journey-copy">Immutable ingestion metadata and reconciliation.</div></div>
            <div class="journey-step"><div class="journey-num">02 · SILVER</div><div class="journey-title">Conformed</div><div class="journey-copy">Typed domains with quality quarantine.</div></div>
            <div class="journey-step"><div class="journey-num">03 · IDENTITY</div><div class="journey-title">Resolved</div><div class="journey-copy">Weighted evidence and deterministic survivor.</div></div>
            <div class="journey-step"><div class="journey-num">04 · GOLD</div><div class="journey-title">Published</div><div class="journey-copy">Canonical Member 360 serving projection.</div></div>
          </div>
          <div class="info-grid">
            <div class="info-item"><div class="info-label">Golden member ID</div><div class="info-value mono">{_safe(selected.get("member_id"))}</div></div>
            <div class="info-item"><div class="info-label">Gold pipeline run</div><div class="info-value mono">{_safe(selected.get("gold_run_id"))}</div></div>
            <div class="info-item"><div class="info-label">Source member ID</div><div class="info-value mono">{_safe(selected.get("source_member_id"))}</div></div>
            <div class="info-item"><div class="info-label">Access projection</div><div class="info-value">{"Masked analytics" if masked else "Member services"}</div></div>
          </div>
        </section>
        <div class="trust-note" style="margin-top:.85rem"><span>◆</span><div><strong>Trust boundary:</strong> Delta Gold is the analytical system of record. PostgreSQL is a rebuildable serving projection, and FastAPI applies the access profile before data reaches this interface.</div></div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="page-foot"><span>Customer 360 AI Data Platform · Member intelligence</span><span>Synthetic portfolio data · Not for production or clinical use</span></div>
    """,
    unsafe_allow_html=True,
)
