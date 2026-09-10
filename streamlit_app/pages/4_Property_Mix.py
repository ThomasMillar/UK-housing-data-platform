import plotly.express as px
import streamlit as st

from lib import (
    format_currency,
    format_number,
    load_build_status_summary,
    load_property_mix,
    load_tenure_summary,
    pct_change,
    sidebar_filters,
    style_figure,
)


st.set_page_config(
    page_title="Property Mix - Housing Explorer",
    page_icon="🏘️",
    layout="wide",
)

st.title("🏘️ Property Mix")
st.write(
    "Compare property types, new and existing homes, and freehold versus leasehold sales."
)

start, end, type_codes, counties = sidebar_filters()

df = load_property_mix(start, end, type_codes, counties)

if df.empty:
    st.warning("No data is available for the selected filters.")
    st.stop()

total_transactions = df["n"].sum()
df["share"] = df["n"] / total_transactions * 100

highest_volume = df.loc[df["n"].idxmax()]
highest_price = df.loc[df["median_price"].idxmax()]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Most common property type", highest_volume["Property"])

with col2:
    st.metric(
        "Highest-priced property type",
        highest_price["Property"],
        help=f"Median price: {format_currency(highest_price['median_price'])}",
    )

with col3:
    st.metric("Transactions", format_number(total_transactions))

st.markdown("---")

left, right = st.columns(2)

with left:
    volume_df = df.sort_values("n")

    fig_volume = px.bar(
        volume_df,
        x="n",
        y="Property",
        orientation="h",
        title="Transactions by property type",
        labels={"n": "Transactions", "Property": "Property type"},
        text="n",
    )

    fig_volume.update_traces(texttemplate="%{text:,.0f}", textposition="inside")
    fig_volume = style_figure(fig_volume, 425)
    st.plotly_chart(fig_volume, use_container_width=True)

with right:
    price_df = df.sort_values("median_price")

    fig_price = px.bar(
        price_df,
        x="median_price",
        y="Property",
        orientation="h",
        title="Median price by property type",
        labels={"median_price": "Median price (£)", "Property": "Property type"},
        text="median_price",
    )

    fig_price.update_traces(texttemplate="£%{text:,.0f}", textposition="inside")
    fig_price = style_figure(fig_price, 425)
    st.plotly_chart(fig_price, use_container_width=True)

st.markdown("---")
st.subheader("New build vs existing properties")

build_df = load_build_status_summary(start, end, type_codes, counties)

if not build_df.empty:
    new_build = build_df[build_df["old_new"] == "Y"]
    existing = build_df[build_df["old_new"] == "N"]

    new_price = new_build["median_price"].iloc[0] if not new_build.empty else None
    existing_price = existing["median_price"].iloc[0] if not existing.empty else None
    new_build_difference = pct_change(existing_price, new_price)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("New-build median", format_currency(new_price))

    with col2:
        st.metric("Existing-property median", format_currency(existing_price))

    with col3:
        value = (
            f"{new_build_difference:+.1f}%"
            if new_build_difference is not None
            else "—"
        )
        st.metric("New-build price difference", value)

    fig_build = px.bar(
        build_df,
        x="build_status",
        y="median_price",
        labels={"build_status": "", "median_price": "Median price (£)"},
        text="median_price",
    )

    fig_build.update_traces(texttemplate="£%{text:,.0f}", textposition="inside")
    fig_build.update_yaxes(tickprefix="£", tickformat=",")
    fig_build = style_figure(fig_build, 350)
    st.plotly_chart(fig_build, use_container_width=True)

st.markdown("---")
st.subheader("Freehold vs leasehold")

tenure_df = load_tenure_summary(start, end, type_codes, counties)

if not tenure_df.empty:
    freehold = tenure_df[tenure_df["duration"] == "F"]
    leasehold = tenure_df[tenure_df["duration"] == "L"]

    freehold_price = freehold["median_price"].iloc[0] if not freehold.empty else None
    leasehold_price = leasehold["median_price"].iloc[0] if not leasehold.empty else None
    tenure_difference = pct_change(leasehold_price, freehold_price)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Freehold median", format_currency(freehold_price))

    with col2:
        st.metric("Leasehold median", format_currency(leasehold_price))

    with col3:
        value = (
            f"{tenure_difference:+.1f}%"
            if tenure_difference is not None
            else "—"
        )
        st.metric("Freehold price difference", value)

    fig_tenure = px.bar(
        tenure_df,
        x="tenure",
        y="median_price",
        labels={"tenure": "", "median_price": "Median price (£)"},
        text="median_price",
    )

    fig_tenure.update_traces(texttemplate="£%{text:,.0f}", textposition="inside")
    fig_tenure.update_yaxes(tickprefix="£", tickformat=",")
    fig_tenure = style_figure(fig_tenure, 350)
    st.plotly_chart(fig_tenure, use_container_width=True)

    st.caption(
        "This is a descriptive comparison. Property type differs substantially "
        "between freehold and leasehold transactions, so the gap should not be "
        "interpreted as the effect of tenure alone."
    )