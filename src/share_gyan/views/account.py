"""Shared MeroShare session handling for the MeroShare and IPO Results pages."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from share_gyan import meroshare
from share_gyan import theme as t

_CREDS = "ms_creds"  # credentials typed into the form; held in memory for this browser session only
_STATE = "ms_state"


@st.cache_data(ttl=86400, show_spinner=False)
def _dps() -> list[dict]:
    return meroshare.depository_participants()


def credentials() -> tuple[meroshare.Credentials | None, str]:
    """Form credentials win over .env; returns (credentials, source)."""
    if st.session_state.get(_CREDS):
        return st.session_state[_CREDS], "sign-in form"
    env = meroshare.load_credentials()
    return (env, ".env file") if env else (None, "")


def state() -> dict | None:
    return st.session_state.get(_STATE)


def run_check(creds: meroshare.Credentials) -> None:
    try:
        with st.spinner("Signing in to MeroShare and reading your account..."):
            account = meroshare.fetch_account(creds)
        st.session_state[_STATE] = {"account": account, "error": None, "at": datetime.now()}
    except meroshare.MeroshareError as exc:
        st.session_state[_STATE] = {"account": None, "error": str(exc), "at": datetime.now()}


def ensure_state() -> dict | None:
    """Sign in once per session. After a failure only an explicit action retries, so a wrong password is never hammered."""
    creds, _ = credentials()
    if creds is None:
        return None
    if _STATE not in st.session_state:
        run_check(creds)
    return st.session_state[_STATE]


def sign_out() -> None:
    st.session_state.pop(_CREDS, None)
    st.session_state.pop(_STATE, None)


def login_form() -> None:
    try:
        participants = _dps()
    except meroshare.MeroshareError as exc:
        st.error(str(exc))
        return
    labels = {p["code"]: f'{p["name"]} ({p["code"]})' for p in participants}
    codes = list(labels)
    preset = meroshare.env_dp()
    index = codes.index(preset) if preset in codes else None

    with st.form("ms-login", border=False):
        dp = st.selectbox("Depository participant", codes, index=index, format_func=labels.get, placeholder="Type to search your DP")
        username = st.text_input("Username", autocomplete="username")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Sign in to MeroShare", width="stretch")
    st.caption("Your login is sent only to MeroShare, kept in memory for this session and never written to disk. Add it to .env to skip this form.")

    if not submitted:
        return
    if not (dp and username.strip() and password):
        st.error("Choose your depository participant and enter your username and password.")
        return
    st.session_state[_CREDS] = meroshare.Credentials(dp, username.strip(), password)
    run_check(st.session_state[_CREDS])
    st.rerun()


def status_bar(source: str, at: datetime, name: str = "") -> None:
    who = f"Signed in as {name}" if name else "Not signed in"
    t.render(
        f'<div class="chips" style="margin-bottom:12px"><span class="chip"><span class="dot"></span>{t.esc(who)}</span>'
        f'<span class="chip">Login from {t.esc(source)}</span><span class="chip">Checked {at:%d %b, %H:%M}</span></div>'
    )
