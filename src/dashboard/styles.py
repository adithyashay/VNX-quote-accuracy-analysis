import streamlit as st


def apply_page_config():
    """
    Apply Streamlit page configuration.
    """

    st.set_page_config(
        page_title="VNX Quote Accuracy Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def apply_custom_styles():
    """
    Apply custom CSS for a cleaner dashboard.
    """

    st.markdown(
        """
        <style>
        .main {
            padding-top: 1rem;
        }

        h1 {
            font-size: 2.2rem;
            font-weight: 700;
        }

        h2 {
            font-size: 1.5rem;
            margin-top: 1.5rem;
        }

        h3 {
            font-size: 1.15rem;
            margin-top: 1rem;
        }

        .small-note {
            font-size: 0.9rem;
            color: #666666;
        }

        .section-divider {
            margin-top: 1rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid #E5E5E5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    """
    Render dashboard header.
    """

    st.title("VNX Quote Accuracy Dashboard")

    st.caption(
        "PostgreSQL-backed dashboard for S&P 500 VNX quote accuracy, "
        "timestamp matching, symbol-level analysis, and raw data coverage."
    )


def render_methodology_note():
    """
    Render methodology note used across the dashboard.
    """

    with st.expander("Methodology"):
        st.markdown(
            """
            **Comparison logic:** VNX is the primary observation.  
            For each VNX quote, the system finds the closest delayed/reference quote for the same symbol.

            **Date filtering:** Date, week, and month filters are based on `vnx_time`.

            **Error calculation:**

            ```text
            percentage_error = (vnx_price - delayed_price) / delayed_price * 100
            absolute_percentage_error = abs(percentage_error)
            ```

            **Timestamp window:** A match is treated as valid when the timestamp gap is within the selected window.
            """
        )