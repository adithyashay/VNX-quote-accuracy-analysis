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
    Display dashboard header.
    """

    st.title("VNX Quote Accuracy Dashboard")

    st.caption(
        "PostgreSQL-backed dashboard for S&P 500 VNX quote cents difference, "
        "timestamp matching, observation counts, and matched data coverage."
    )


def render_methodology_note():
    """
    Display methodology note used across the dashboard.
    """

    with st.expander("Methodology"):
        st.markdown(
            """
            **Comparison logic:** VNX is the primary observation.  
            For each VNX quote, the system finds the closest delayed/reference quote for the same symbol.

            **Date filtering:** Date, week, and month filters are based on `vnx_time`.

            **Difference calculation:**

            ```text
            difference_cents = (vnx_price - delayed_price) * 100
            absolute_difference_cents = abs(difference_cents)
            normalized_difference_bps = absolute_percentage_error * 100
            ```

            Basis points are shown as the normalized view so high-priced and low-priced symbols can be compared more fairly.

            **Observation counts:** Time-bucket counts are grouped by `vnx_time`, so they represent matched quote snapshots collected inside each interval.

            **Pipeline timestamps:** Quote timestamps come from the source feed. Worker, matcher, and sync timestamps show when the automation last ran.

            **Timestamp window:** A match is treated as valid when the timestamp gap is within the selected window. Wide-gap matches are excluded from dashboard accuracy metrics because they mix market movement with quote error.
            """
        )
