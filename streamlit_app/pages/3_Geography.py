import plotly.express as px
import streamlit as st

from lib import (
    format_currency,
    format_number,
    load_geo_movers,
    load_geo_summary,
    sidebar_filters,
    style_figure,
)

st.set_page_config(
    page_title="Geography - Housing Explorer",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Geography")
st.write("Compare housing prices and transaction activity across different areas.")

start, end, type_codes, counties = sidebar_filters()

geo = st.radio(
    "Geographical level",
    ["county", "district", "town_city"],
    horizontal=True,
)

geo_labels = {
    "county": "County",
    "district": "District",
    "town_city": "Town / City",
}

geo_label = geo_labels[geo]

df = load_geo_summary(
    start, end, type_codes, counties, geo
)

if df.empty:
    st.warning("No data is available for the selected filters.")
    st.stop()

measure = st.radio(
    "Rank areas by",
    ["Transaction volume", "Median price"],
    horizontal=True,
)

top_n = st.slider("Number of areas", 5, 30, 10)

if measure == "Transaction volume":
    plot_df = (
        df.sort_values("n", ascending=False)
        .head(top_n)
        .sort_values("n")
    )

    fig = px.bar(
        plot_df,
        x="n",
        y="region",
        orientation="h",
        labels={"n": "Transactions", "region": geo_label},
        text="n",
    )

    fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
    )

else:
    plot_df = (
        df.sort_values("median_price", ascending=False)
        .head(top_n)
        .sort_values("median_price")
    )

    fig = px.bar(
        plot_df,
        x="median_price",
        y="region",
        orientation="h",
        labels={
            "median_price": "Median price (£)",
            "region": geo_label,
        },
        text="median_price",
    )

    fig.update_traces(
        texttemplate="£%{text:,.0f}",
        textposition="outside",
    )

fig = style_figure(fig, 525)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.subheader("Recent price movers")

movers = load_geo_movers(
    start,
    end,
    type_codes,
    counties,
    geo=geo,
    min_transactions=100,
)

if movers.empty:
    st.info(
        "Select a date range covering at least two years to compare "
        "the latest 12 months with the previous 12 months."
    )

else:
    fastest = movers.nlargest(
        10, "price_change_pct"
    ).sort_values("price_change_pct").copy()

    slowest = movers.nsmallest(
        10, "price_change_pct"
    ).sort_values("price_change_pct", ascending=False).copy()

    # Pre-format labels so raw floating-point precision is never displayed.
    fastest["change_label"] = fastest["price_change_pct"].map(
        lambda x: f"{x:+.1f}%"
    )
    slowest["change_label"] = slowest["price_change_pct"].map(
        lambda x: f"{x:+.1f}%"
    )

    left, right = st.columns(2)

    with left:
        fig_up = px.bar(
            fastest,
            x="price_change_pct",
            y="region",
            orientation="h",
            title="Largest median price increases",
            labels={
                "price_change_pct": "Price change (%)",
                "region": geo_label,
            },
            text="change_label",
        )

        fig_up.update_traces(
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Price change: %{x:.1f}%<extra></extra>",
        )
        fig_up.update_xaxes(ticksuffix="%", tickformat=".1f")
        fig_up = style_figure(fig_up, 425)

        st.plotly_chart(fig_up, use_container_width=True)

    with right:
        fig_down = px.bar(
            slowest,
            x="price_change_pct",
            y="region",
            orientation="h",
            title="Lowest median price change",
            labels={
                "price_change_pct": "Price change (%)",
                "region": geo_label,
            },
            text="change_label",
        )

        fig_down.update_traces(
            textposition="inside",
            hovertemplate="<b>%{y}</b><br>Price change: %{x:.1f}%<extra></extra>",
        )
        fig_down.update_xaxes(ticksuffix="%", tickformat=".1f")
        fig_down = style_figure(fig_down, 425)

        st.plotly_chart(fig_down, use_container_width=True)

    st.caption(
        "Compares the latest 12 months with the preceding 12 months. "
        "Areas require at least 100 transactions in both periods."
    )

st.markdown("---")
st.subheader(f"{geo_label} comparison")

display_df = df.copy()
display_df["Transactions"] = display_df["n"].apply(format_number)
display_df["Median Price"] = display_df["median_price"].apply(format_currency)
display_df["Average Price"] = display_df["avg_price"].apply(format_currency)

display_df = display_df[
    ["region", "Transactions", "Median Price", "Average Price"]
].rename(columns={"region": geo_label})

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)