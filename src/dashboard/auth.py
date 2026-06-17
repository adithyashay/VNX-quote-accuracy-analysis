import hmac
import os

import streamlit as st

from src.settings import get_bool_env


def credentials_match(username, password, expected_username, expected_password):
    if not username or not password:
        return False

    if not expected_username or not expected_password:
        return False

    username_matches = hmac.compare_digest(username, expected_username)
    password_matches = hmac.compare_digest(password, expected_password)

    return username_matches and password_matches


def get_dashboard_secret(name):
    value = os.getenv(name)

    if value:
        return value

    try:
        return st.secrets.get(name, None)
    except Exception:
        return None


def require_dashboard_login():
    """
    Stop dashboard rendering unless the user is authenticated.

    Local development leaves auth disabled by default. Production should set
    DASHBOARD_AUTH_ENABLED=true plus DASHBOARD_USERNAME and DASHBOARD_PASSWORD.
    """

    auth_enabled = get_bool_env("DASHBOARD_AUTH_ENABLED", False)

    if not auth_enabled:
        return True

    expected_username = get_dashboard_secret("DASHBOARD_USERNAME")
    expected_password = get_dashboard_secret("DASHBOARD_PASSWORD")

    if not expected_username or not expected_password:
        st.error(
            "Dashboard authentication is enabled, but credentials are not configured."
        )
        st.stop()

    if st.session_state.get("dashboard_authenticated"):
        if st.sidebar.button("Log out"):
            st.session_state["dashboard_authenticated"] = False
            st.rerun()

        return True

    st.title("VNX Quote Accuracy Dashboard")
    st.caption("Sign in to access the dashboard.")

    with st.form("dashboard_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        if credentials_match(
            username,
            password,
            expected_username,
            expected_password,
        ):
            st.session_state["dashboard_authenticated"] = True
            st.rerun()

        st.error("Invalid username or password.")

    st.stop()
