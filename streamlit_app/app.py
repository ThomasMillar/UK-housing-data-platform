import streamlit as st


st.set_page_config(
    page_title="Home - England & Wales Housing Explorer",
    page_icon="🏠",
    layout="wide",
)


st.title("🏠 Home")

st.markdown(
    """
    ## England & Wales Housing Explorer

    Explore residential property transactions recorded by HM Land Registry
    across England and Wales.

    Use the navigation on the left to explore **market trends, geography,
    property types, price distribution and the underlying transaction data**.
    """
)

st.markdown("---")


col1, col2, col3 = st.columns(3)


with col1:
    st.subheader("📈 Market Trends")

    st.write(
        "Track how median transaction prices and housing activity "
        "have changed over time."
    )


with col2:
    st.subheader("🗺️ Geography")

    st.write(
        "Compare housing markets across counties, districts "
        "and towns or cities."
    )


with col3:
    st.subheader("🏘️ Property & Prices")

    st.write(
        "Explore differences between property types and understand "
        "the distribution of recorded transaction prices."
    )


st.markdown("---")


st.subheader("📊 About the data")

st.write(
    """
    **Source:** HM Land Registry Price Paid Data

    **Coverage:** England and Wales

    **Measure:** Recorded residential property transactions

    Prices represent recorded transaction values rather than asking prices
    or current property valuations.
    """
)


st.info(
    "Use the navigation in the sidebar to begin exploring the data. "
    "The dashboard filters can be applied consistently across the analytical pages."
)