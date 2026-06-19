import streamlit as st
import pandas as pd
import plotly.express as px

DATA_FILE = "company_radar_output.xlsx"

st.set_page_config(
    page_title="AI Infrastructure Radar",
    layout="wide"
)

st.title("AI Infrastructure Company Radar")
st.caption("Momentum, returns, market cap and category rotation across selected AI infrastructure companies.")


@st.cache_data
def load_data():
    radar = pd.read_excel(DATA_FILE, sheet_name="company_radar")

    try:
        summary = pd.read_excel(DATA_FILE, sheet_name="category_summary")
    except Exception:
        summary = pd.DataFrame()

    return radar, summary


radar, summary = load_data()

required_cols = ["ticker", "ai_chain_category", "momentum_score", "return_ytd", "market_cap_usd"]

missing = [col for col in required_cols if col not in radar.columns]

if missing:
    st.error(f"Missing required columns in company_radar sheet: {missing}")
    st.stop()


# -----------------------------
# Sidebar filters
# -----------------------------

st.sidebar.header("Filters")

categories = sorted(radar["ai_chain_category"].dropna().unique())

selected_categories = st.sidebar.multiselect(
    "AI chain category",
    categories,
    default=categories
)

if "sub_category" in radar.columns:
    subcategories = sorted(radar["sub_category"].dropna().unique())
    selected_subcategories = st.sidebar.multiselect(
        "Sub-category",
        subcategories,
        default=subcategories
    )
else:
    selected_subcategories = None

if "market_cap_bucket" in radar.columns:
    buckets = sorted(radar["market_cap_bucket"].dropna().unique())
    selected_buckets = st.sidebar.multiselect(
        "Market cap bucket",
        buckets,
        default=buckets
    )
else:
    selected_buckets = None

min_momentum = st.sidebar.slider(
    "Minimum momentum score",
    min_value=0,
    max_value=100,
    value=0,
    step=5
)

min_ytd = st.sidebar.slider(
    "Minimum YTD return",
    min_value=-100,
    max_value=300,
    value=-100,
    step=10
) / 100


filtered = radar.copy()

filtered = filtered[filtered["ai_chain_category"].isin(selected_categories)]
filtered = filtered[filtered["momentum_score"] >= min_momentum]
filtered = filtered[filtered["return_ytd"] >= min_ytd]

if selected_subcategories is not None:
    filtered = filtered[filtered["sub_category"].isin(selected_subcategories)]

if selected_buckets is not None:
    filtered = filtered[filtered["market_cap_bucket"].isin(selected_buckets)]


# -----------------------------
# Helper functions
# -----------------------------

def format_table(df):
    percent_cols = [
        "return_1m",
        "return_3m",
        "return_6m",
        "return_ytd",
        "return_1y",
        "return_5y",
        "return_since_listing",
        "price_vs_sma_50",
        "price_vs_sma_200",
        "sma_50_vs_200",
        "distance_from_52w_high",
        "distance_from_52w_low",
        "avg_ytd_return",
        "median_ytd_return",
        "mcap_weighted_ytd_return",
        "avg_1y_return",
        "median_1y_return",
        "mcap_weighted_1y_return",
        "avg_5y_return",
        "median_5y_return",
        "mcap_weighted_5y_return",
        "pct_companies_above_80_momentum",
    ]

    format_dict = {
        col: "{:.0%}"
        for col in percent_cols
        if col in df.columns
    }

    number_cols = [
        "market_cap_usd",
        "market_cap_usd_bn",
        "total_market_cap_usd_bn",
        "avg_market_cap_usd_bn",
        "median_market_cap_usd_bn",
    ]

    for col in number_cols:
        if col in df.columns:
            format_dict[col] = "{:,.0f}"

    return df.style.format(format_dict)

def weighted_average(df, value_col, weight_col="market_cap_usd"):
    valid = df[[value_col, weight_col]].dropna()
    valid = valid[valid[weight_col] > 0]

    if valid.empty:
        return None

    return (valid[value_col] * valid[weight_col]).sum() / valid[weight_col].sum()


def fmt_pct(x):
    if pd.isna(x):
        return "n/a"
    return f"{x:.0%}"


def fmt_bn(x):
    if pd.isna(x):
        return "n/a"
    return f"${x / 1_000_000_000:,.1f}bn"


# -----------------------------
# KPI row
# -----------------------------

total_companies = len(filtered)
total_market_cap = filtered["market_cap_usd"].sum()
avg_momentum = filtered["momentum_score"].mean()
weighted_ytd = weighted_average(filtered, "return_ytd")
strong_momentum_pct = (filtered["momentum_score"] >= 80).mean() if len(filtered) > 0 else None

col1, col3, col4, col5 = st.columns(4)

col1.metric("Companies", f"{total_companies:,}")
#col2.metric("Total market cap Bn ", fmt_bn(total_market_cap))
col3.metric("Avg momentum", f"{avg_momentum:.1f}" if pd.notna(avg_momentum) else "n/a")
col4.metric("MCap-weighted YTD", fmt_pct(weighted_ytd))
col5.metric("% strong momentum", fmt_pct(strong_momentum_pct))


# -----------------------------
# Main charts
# -----------------------------

st.subheader("Market map")

chart_df = filtered.copy()
chart_df["market_cap_usd_bn"] = chart_df["market_cap_usd"] / 1_000_000_000

fig = px.scatter(
    chart_df,
    x="return_ytd",
    y="momentum_score",
    size="market_cap_usd_bn",
    color="ai_chain_category",
    hover_name="company_name",
    hover_data=[
        "company_name" if "company_name" in chart_df.columns else "ticker",
        "sub_category" if "sub_category" in chart_df.columns else "ai_chain_category",
        "market_cap_usd_bn",
        "return_1y" if "return_1y" in chart_df.columns else "return_ytd",
        "return_5y" if "return_5y" in chart_df.columns else "return_ytd",
        "distance_from_52w_high" if "distance_from_52w_high" in chart_df.columns else "return_ytd",
    ],
    labels={
        "return_ytd": "YTD return",
        "momentum_score": "Momentum score",
        "market_cap_usd_bn": "Market cap USD bn",
        "ai_chain_category": "AI chain category"
    },
    title="YTD return vs Momentum score"
)

fig.update_layout(
    xaxis_tickformat=".0%",
    height=650
)

st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# Category summary
# -----------------------------

if not summary.empty:
    st.subheader("Category rotation")

    summary_display = summary.copy()

    if "mcap_weighted_momentum_score" in summary_display.columns:
        sort_col = "mcap_weighted_momentum_score"
    elif "avg_momentum_score" in summary_display.columns:
        sort_col = "avg_momentum_score"
    else:
        sort_col = None

    if sort_col:
        summary_display = summary_display.sort_values(sort_col, ascending=False)

    col_a, col_b = st.columns(2)

    with col_a:
        if "mcap_weighted_momentum_score" in summary_display.columns:
            fig_cat_mom = px.bar(
                summary_display,
                x="mcap_weighted_momentum_score",
                y="ai_chain_category",
                orientation="h",
                title="Market-cap weighted momentum by category",
                labels={
                    "mcap_weighted_momentum_score": "MCap-weighted momentum",
                    "ai_chain_category": "Category"
                }
            )
            fig_cat_mom.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_cat_mom, use_container_width=True)

    with col_b:
        if "mcap_weighted_ytd_return" in summary_display.columns:
            fig_cat_ytd = px.bar(
                summary_display,
                x="mcap_weighted_ytd_return",
                y="ai_chain_category",
                orientation="h",
                title="Market-cap weighted YTD return by category",
                labels={
                    "mcap_weighted_ytd_return": "MCap-weighted YTD return",
                    "ai_chain_category": "Category"
                }
            )
            fig_cat_ytd.update_layout(
                xaxis_tickformat=".0%",
                yaxis={"categoryorder": "total ascending"}
            )
            st.plotly_chart(fig_cat_ytd, use_container_width=True)

    summary_cols = [
            "ai_chain_category",
            "companies",
            "total_market_cap_usd_bn",
            "avg_market_cap_usd_bn",
            "median_market_cap_usd_bn",

            "mcap_weighted_momentum_score",
            "avg_momentum_score",
            "median_momentum_score",
            "companies_above_80_momentum",
            "pct_companies_above_80_momentum",
            "momentum_breadth_label",

            "mcap_weighted_ytd_return",
            "avg_ytd_return",
            "median_ytd_return",

            "mcap_weighted_1y_return",
            "avg_1y_return",
            "median_1y_return",

            "mcap_weighted_5y_return",
            "avg_5y_return",
            "median_5y_return",

            "mcap_weighted_since_listing_return",
            "avg_since_listing_return",
            "median_since_listing_return",
        ]

    summary_cols = [c for c in summary_cols if c in summary_display.columns]

    st.dataframe(
                format_table(summary_display[summary_cols]),
                use_container_width=True,
                hide_index=True
    )


# -----------------------------
# Outlier views
# -----------------------------

st.subheader("Outlier screens")

tabs = st.tabs([
    "Top Momentum",
    "Top YTD",
    "Top 1Y",
    "Near 52W High",
    "Recent IPOs",
    "Full Table"
])

with tabs[0]:
    cols = [
        "company_name","return_ytd", "return_1y",  "ai_chain_category", "sub_category",
        "market_cap_usd", "momentum_score", "momentum_label",
        "distance_from_52w_high"
    ]
    cols = [c for c in cols if c in filtered.columns]
    st.dataframe(
        format_table(filtered.sort_values("momentum_score", ascending=False)[cols]),
        use_container_width=True,
        hide_index=True
    )

with tabs[1]:
    cols = [
        "company_name","return_ytd", "distance_from_52w_high", "ai_chain_category", "sub_category",
        "market_cap_usd", "momentum_score",
        
    ]
    cols = [c for c in cols if c in filtered.columns]
    st.dataframe(
        format_table(filtered.sort_values("return_ytd", ascending=False)[cols]),
        use_container_width=True,
        hide_index=True
    )

with tabs[2]:
    if "return_1y" in filtered.columns:
        cols = [
            "company_name","return_1y", "return_ytd", "ai_chain_category", "sub_category",
            "market_cap_usd",  "momentum_score"
        ]
        cols = [c for c in cols if c in filtered.columns]
        st.dataframe(
            format_table(filtered.sort_values("return_1y", ascending=False)[cols]),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("return_1y column not available.")

with tabs[3]:
    if "distance_from_52w_high" in filtered.columns:
        cols = [
            "company_name", "distance_from_52w_high","return_ytd","momentum_score",
            "ai_chain_category", "sub_category",
            "market_cap_usd", 
              "rsi_14"
        ]
        cols = [c for c in cols if c in filtered.columns]
        st.dataframe(
            format_table(filtered.sort_values("distance_from_52w_high", ascending=False)[cols]),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("distance_from_52w_high column not available.")

with tabs[4]:
    if "years_since_listing" in filtered.columns:
        recent = filtered[filtered["years_since_listing"] <= 5]
        cols = [
            "company_name", "listing_proxy_date", "years_since_listing","return_since_listing",
            "return_ytd", "momentum_score"
            "ai_chain_category", "sub_category",
            "market_cap_usd", 
            
        ]
        cols = [c for c in cols if c in recent.columns]
        st.dataframe(
            format_table(recent.sort_values("momentum_score", ascending=False)[cols]),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("years_since_listing column not available.")

with tabs[5]:
    st.dataframe(
        format_table(filtered),
        use_container_width=True,
        hide_index=True
    )