import streamlit as st
import plotly.express as px

from lib import (
    sidebar_filters,
    load_geo_summary,
    format_currency,
    format_number,
    style_figure,
)


st.set_page_config(
    page_title="Geography - Housing Explorer",
    page_icon="🗺️",
    layout="wide",
)


st.title("🗺️ Geography")

st.write(
    "Compare transaction activity and housing prices "
    "across different geographical areas."
)


# FILTERS

start, end, type_codes, counties = sidebar_filters()


# GEOGRAPHIC LEVEL

geo = st.radio(
    "Geographical level",
    [
        "county",
        "district",
        "town_city",
    ],
    horizontal=True,
)


geo_labels = {
    "county": "County",
    "district": "District",
    "town_city": "Town / City",
}


geo_label = geo_labels[geo]


df = load_geo_summary(
    start,
    end,
    type_codes,
    counties,
    geo=geo,
)


if df.empty:
    st.warning(
        "No data is available for the selected filters."
    )
    st.stop()


# DISPLAY SETTINGS

measure = st.radio(
    "Compare regions by",
    [
        "Transaction volume",
        "Median price",
    ],
    horizontal=True,
)


top_n = st.slider(
    f"Number of {geo_label.lower()}s",
    min_value=5,
    max_value=30,
    value=10,
)


# RANKING

if measure == "Transaction volume":

    plot_df = (
        df
        .sort_values(
            "n",
            ascending=False,
        )
        .head(top_n)
        .sort_values(
            "n",
            ascending=True,
        )
    )

    fig = px.bar(
        plot_df,
        x="n",
        y="region",
        orientation="h",
        title=(
            f"Top {top_n} {geo_label}s "
            "by Transaction Volume"
        ),
        labels={
            "n": "Transactions",
            "region": geo_label,
        },
        text="n",
    )

    fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
    )

else:

    plot_df = (
        df
        .sort_values(
            "median_price",
            ascending=False,
        )
        .head(top_n)
        .sort_values(
            "median_price",
            ascending=True,
        )
    )

    fig = px.bar(
        plot_df,
        x="median_price",
        y="region",
        orientation="h",
        title=(
            f"Top {top_n} {geo_label}s "
            "by Median Price"
        ),
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


fig = style_figure(
    fig,
    height=550,
)


st.plotly_chart(
    fig,
    use_container_width=True,
)


# TABLE

st.markdown("---")

st.subheader(
    f"📊 {geo_label} comparison"
)


display_df = df.copy()


display_df["Median Price"] = (
    display_df["median_price"]
    .apply(format_currency)
)


display_df["Average Price"] = (
    display_df["avg_price"]
    .apply(format_currency)
)


display_df["Transactions"] = (
    display_df["n"]
    .apply(format_number)
)


display_df = display_df[
    [
        "region",
        "Transactions",
        "Median Price",
        "Average Price",
    ]
].rename(
    columns={
        "region": geo_label,
    }
)


st.dataframe(
    display_df.head(20),
    use_container_width=True,
    hide_index=True,
)


st.caption(
    f"Showing the first 20 {geo_label.lower()}s "
    "in the comparison table."
)