from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px


DATA_FILE = "company_radar_output.xlsx"

st.set_page_config(
    page_title="AI Infrastructure Radar",
    layout="wide"
)


@st.cache_data
def load_data():
    radar = pd.read_excel(DATA_FILE, sheet_name="company_radar")


    try:
        summary = pd.read_excel(DATA_FILE, sheet_name="category_summary")

    except Exception:
        summary = pd.DataFrame()
    
    try:
        portfolio = pd.read_excel(
            DATA_FILE,
            sheet_name="selected_portfolio"
        )
    except Exception:
        portfolio = pd.DataFrame()

    try:
        portfolio_summary = pd.read_excel(
            DATA_FILE,
            sheet_name="portfolio_summary"
        )
    except Exception:
        portfolio_summary = pd.DataFrame()

    return radar, summary, portfolio, portfolio_summary


radar, summary, portfolio, portfolio_summary = load_data()

required_cols = ["ticker", "ai_chain_category", "momentum_score", "return_ytd", "market_cap_usd"]

missing = [col for col in required_cols if col not in radar.columns]

if missing:
    st.error(f"Missing required columns in company_radar sheet: {missing}")
    st.stop()

# -----------------------------
# Helper functions
# -----------------------------

def format_market_cap(value):
    if pd.isna(value):
        return "n/a"

    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.1f}tn"

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.0f}bn"

    if value >= 1_000_000:
        return f"${value / 1_000_000:.0f}mn"

    return f"${value:,.0f}"

def momentum_label(score):
    if score >= 80:
        return "Strong"
    elif score >= 60:
        return "Positive"
    elif score >= 40:
        return "Neutral"
    else:
        return "Weak"

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

def format_market_cap(value):
    if value is None or pd.isna(value):
        return "n/a"

    trillion = value / 1_000_000_000_000

    if trillion >= 1:
        return f"${trillion:,.1f}tn"

    billion = value / 1_000_000_000
    return f"${billion:,.0f}bn"


# --------------------------------------------------
# Header
# --------------------------------------------------

st.title("AI Infrastructure Radar")

st.markdown(
    """
    **A map of the publicly listed companies building the infrastructure
    behind artificial intelligence.**

    Explore where market momentum is concentrating across semiconductors,
    memory, networking, servers, data centers, energy and AI cloud services.
    """
)

st.caption(
    f"Dashboard generated on {datetime.now():%d %B %Y}"
)

st.divider()

tab_radar, tab_portfolio = st.tabs([
    "Company Radar",
    "Equal-Weight Portfolio",
])

with tab_radar:
    # --------------------------------------------------
    # Filters
    # --------------------------------------------------

    st.sidebar.header("Explore the universe")

    categories = sorted(
        radar["ai_chain_category"]
        .dropna()
        .unique()
    )

    selected_categories = st.sidebar.multiselect(
        "AI infrastructure category",
        options=categories,
        default=categories
    )

    filtered = radar[
        radar["ai_chain_category"].isin(
            selected_categories
        )
    ].copy()


    if "market_cap_bucket" in filtered.columns:
        buckets = sorted(
            filtered["market_cap_bucket"]
            .dropna()
            .unique()
        )

        selected_buckets = st.sidebar.multiselect(
            "Company size",
            options=buckets,
            default=buckets
        )

        filtered = filtered[
            filtered["market_cap_bucket"].isin(
                selected_buckets
            )
        ]


    minimum_momentum = st.sidebar.slider(
        "Minimum momentum score",
        min_value=0,
        max_value=100,
        value=0,
        step=5
    )

    filtered = filtered[
        filtered["momentum_score"] >= minimum_momentum
    ]





    # --------------------------------------------------
    # KPIs
    # --------------------------------------------------

    total_companies = len(filtered)
    total_market_cap = filtered["market_cap_usd"].sum()
    average_momentum = filtered["momentum_score"].mean()

    weighted_ytd = weighted_average(
        filtered,
        "return_ytd"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Companies",
        f"{total_companies:,}"
    )

    col2.metric(
        "Combined market cap",
        format_market_cap(total_market_cap)
    )

    col3.metric(
        "MCap-weighted YTD",
        fmt_pct(weighted_ytd)
    )

    col4.metric(
        "Average momentum",
        (
            f"{average_momentum:.0f}/100"
            if pd.notna(average_momentum)
            else "n/a"
        )
    )

    st.divider()

    # --------------------------------------------------
    # Category chart
    # --------------------------------------------------

    st.subheader("Where is momentum concentrating?")

    category_view = summary.copy()

    if selected_categories:
        category_view = category_view[
            category_view["ai_chain_category"].isin(
                selected_categories
            )
        ]

    category_view = category_view.sort_values(
        "mcap_weighted_momentum_score",
        ascending=True
    )

    fig_categories = px.bar(
        category_view,
        x="mcap_weighted_momentum_score",
        y="ai_chain_category",
        orientation="h",
        labels={
            "mcap_weighted_momentum_score":
                "Market-cap weighted momentum",
            "ai_chain_category":
                ""
        },
        hover_data={
            "companies": True,
            "mcap_weighted_ytd_return": ":.0%",
            "median_ytd_return": ":.0%",
        }
    )

    fig_categories.update_layout(
        height=550,
        showlegend=False,
        margin=dict(l=10, r=20, t=20, b=20),
        xaxis_range=[0, 100]
    )

    st.plotly_chart(
        fig_categories,
        use_container_width=True
    )

    # Other subheader
    #
    #

    category_summary = pd.read_excel(
    "company_radar_output.xlsx",
    sheet_name="category_summary")

    st.subheader("YTD Return by sector")

    fig_sector_ytd = px.bar(
        category_summary.sort_values("mcap_weighted_ytd_return", ascending=True),
        x="mcap_weighted_ytd_return",
        y="ai_chain_category",
        orientation="h",
        text="mcap_weighted_ytd_return",
        title="YTD return by sector"
    )

    fig_sector_ytd.update_traces(
        texttemplate="%{text:.1%}",
        textposition="outside"
    )

    fig_sector_ytd.update_layout(
        xaxis_title="YTD Return",
        yaxis_title="",
        xaxis_tickformat=".0%",
        showlegend=False,
        height=max(400, len(category_summary) * 45)
    )

    st.plotly_chart(fig_sector_ytd, use_container_width=True)

    # --------------------------------------------------
    # Company map
    # --------------------------------------------------

    st.subheader("Company map")

    st.caption(
        """
        Bubble size represents market capitalisation.
        Companies further to the right have delivered higher YTD returns;
        companies higher on the chart have stronger momentum.
        """
    )

    chart_df = filtered.dropna(
        subset=[
            "return_ytd",
            "momentum_score",
            "market_cap_usd"
        ]
    ).copy()

    chart_df["market_cap_usd_bn"] = (
        chart_df["market_cap_usd"]
        / 1_000_000_000
    )

    fig_map = px.scatter(
        chart_df,
        x="return_ytd",
        y="momentum_score",
        size="market_cap_usd_bn",
        color="ai_chain_category",
        hover_name="company_name",
        hover_data={
            "company_name": False,
            "sub_category": False,
            "market_cap_usd_bn": ":,.0f",
            "return_ytd": ":.0%",
            "return_1y": ":.0%",
            "momentum_score": ":.0f",
        },
        labels={
            "return_ytd": "YTD return",
            "momentum_score": "Momentum score",
            "ai_chain_category": "Category",
            "market_cap_usd_bn": "Market cap ($bn)",
            "company_name": "Company",
        }
    )

    fig_map.update_layout(
        height=650,
        xaxis_tickformat=".0%",
        yaxis_range=[0, 105],
        legend_title_text="AI category",
        margin=dict(l=10, r=20, t=20, b=20)
    )

    fig_map.add_hline(
        y=80,
        line_dash="dot",
        annotation_text="Strong momentum"
    )

    fig_map.add_vline(
        x=0,
        line_dash="dot"
    )

    st.plotly_chart(
        fig_map,
        use_container_width=True
    )

    # --------------------------------------------------
    # Company table
    # --------------------------------------------------

    st.subheader("Explore the companies")
    # 1. Copiamos primero todas las columnas
    table = filtered.copy()
    # 2. Creamos las columnas de visualización
    table["momentum_label_display"] = table["momentum_score"].apply(
        momentum_label
    )

    table["market_cap_display"] = table["market_cap_usd"].apply(
        format_market_cap
    )
    table["return_ytd_display"] = table["return_ytd"] * 100
    table["return_1y_display"] = table["return_1y"] * 100
    table["market_cap_bn"] = table["market_cap_usd"] / 1_000_000_000
    # 3. Ordenamos mientras momentum_score todavía existe
    table = table.sort_values(
        "momentum_score",
        ascending=False
    )
    # 4. Definimos las columnas finales y su orden
    table_columns = [
        "company_name",
        "ai_chain_category",
        "return_ytd_display",
        "return_1y_display",
        "momentum_label_display",
        "sub_category",
        "market_cap_bn",
        "distance_from_52w_high",
        "index_memberships"
    ]

    # 5. Nos quedamos solo con las columnas existentes
    table_columns = [
        column
        for column in table_columns
        if column in table.columns
    ]

    # 6. Mostramos la tabla
    st.dataframe(
        table[table_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "company_name": st.column_config.TextColumn(
                "Company"
            ),
            "ai_chain_category": st.column_config.TextColumn(
                "AI category"
            ),
            "sub_category": st.column_config.TextColumn(
                "Subcategory"
            ),
            "market_cap_bn": st.column_config.NumberColumn(
                "Market cap ($bn)",
                format="$%.0f"
            ),
            "return_ytd_display": st.column_config.NumberColumn(
                "YTD",
                format="%.0f%%"
            ),
            "return_1y_display": st.column_config.NumberColumn(
                "1 year",
                format="%.0f%%"
            ),
            "momentum_label_display": st.column_config.TextColumn(
                "Momentum",
            ),  
            "distance_from_52w_high":
                st.column_config.NumberColumn(
                    "From 52W high",
                    format="percent"
                ),
        }
    )


    # --------------------------------------------------
    # Methodology
    # --------------------------------------------------

    with st.expander("Methodology and limitations"):
        st.markdown(
            """
            **Universe**

            This dashboard contains a curated selection of publicly listed
            companies with direct or indirect exposure to AI infrastructure.

            **Classification**

            Companies are classified according to their principal role in the
            AI value chain. Some companies operate across several categories,
            so the classification necessarily involves judgement.

            **Momentum**

            The momentum score combines recent returns, moving-average signals,
            distance from 52-week highs and relative trading volume.

            **Market-cap weighted metrics**

            Larger companies receive a greater weight. Consequently, some
            category results may be dominated by one or two mega-cap companies.

            **Limitations**

            The dashboard is educational and does not constitute investment
            advice. Momentum does not measure valuation, competitive advantage
            or future expected returns.
            """
        )

with tab_portfolio:

    st.header("My AI Infrastructure Portfolio")

    st.caption(
        "Equal-weight model portfolio. "
        "Each company starts with the same weight."
    )

    if portfolio.empty:
        st.warning(
            "No portfolio data found. "
            "Add selected_portfolio = 1 to the chosen companies "
            "and rerun data_ia_stocks.py."
        )

    else:
        number_of_companies = len(portfolio)
        equal_weight = 1 / number_of_companies

        portfolio_ytd = (
            portfolio["return_ytd"].mean()
            if "return_ytd" in portfolio.columns
            else None
        )

        portfolio_1y = (
            portfolio["return_1y"].mean()
            if "return_1y" in portfolio.columns
            else None
        )

        best_company = None
        worst_company = None

        if "return_ytd" in portfolio.columns:
            valid_ytd = portfolio.dropna(
                subset=["return_ytd"]
            )

            if not valid_ytd.empty:
                best_company = valid_ytd.loc[
                    valid_ytd["return_ytd"].idxmax()
                ]

                worst_company = valid_ytd.loc[
                    valid_ytd["return_ytd"].idxmin()
                ]

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Companies",
            number_of_companies,
        )

        col2.metric(
            "Weight per company",
            f"{equal_weight:.1%}",
        )

        col3.metric(
            "Portfolio YTD",
            (
                f"{portfolio_ytd:.1%}"
                if portfolio_ytd is not None
                and pd.notna(portfolio_ytd)
                else "n/a"
            ),
        )

        col4.metric(
            "Portfolio 1Y",
            (
                f"{portfolio_1y:.1%}"
                if portfolio_1y is not None
                and pd.notna(portfolio_1y)
                else "n/a"
            ),
        )

        st.divider()

        if best_company is not None:
            col1, col2 = st.columns(2)

            col1.metric(
                "Best YTD",
                best_company.get(
                    "company_name",
                    best_company["ticker"],
                ),
                f"{best_company['return_ytd']:.1%}",
            )

            col2.metric(
                "Worst YTD",
                worst_company.get(
                    "company_name",
                    worst_company["ticker"],
                ),
                f"{worst_company['return_ytd']:.1%}",
            )

        st.subheader("Portfolio positions")

        portfolio_table = portfolio.copy()

        portfolio_table["weight_display"] = (
            portfolio_table["portfolio_weight"] * 100
        )

        portfolio_table["return_ytd_display"] = (
            portfolio_table["return_ytd"] * 100
        )

        portfolio_table["return_1y_display"] = (
            portfolio_table["return_1y"] * 100
        )

        portfolio_table["ytd_contribution_display"] = (
            portfolio_table[
                "ytd_contribution"
            ] * 100
        )

        portfolio_columns = [
            "company_name",
            "ticker",
            "weight_display",
            "return_ytd_display",
            "return_1y_display",
            "ytd_contribution_display",
            "momentum_score",
        ]

        portfolio_columns = [
            column
            for column in portfolio_columns
            if column in portfolio_table.columns
        ]

        st.dataframe(
            portfolio_table[portfolio_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                "company_name":
                    st.column_config.TextColumn(
                        "Company"
                    ),
                "ticker":
                    st.column_config.TextColumn(
                        "Ticker"
                    ),
                "weight_display":
                    st.column_config.NumberColumn(
                        "Initial weight",
                        format="%.1f%%",
                    ),
                "return_ytd_display":
                    st.column_config.NumberColumn(
                        "YTD",
                        format="%.1f%%",
                    ),
                "return_1y_display":
                    st.column_config.NumberColumn(
                        "1 year",
                        format="%.1f%%",
                    ),
                "ytd_contribution_display":
                    st.column_config.NumberColumn(
                        "YTD contribution",
                        format="%.1f%%",
                    ),
                "momentum_score":
                    st.column_config.NumberColumn(
                        "Momentum",
                        format="%.0f",
                    ),
            },
        )

        st.divider()

        st.subheader("YTD return by company")

        chart_data = portfolio.dropna(
            subset=["return_ytd"]
        ).copy()

        chart_data = chart_data.sort_values(
            "return_ytd",
            ascending=True,
        )

        fig_returns = px.bar(
            chart_data,
            x="return_ytd",
            y="company_name",
            orientation="h",
            labels={
                "return_ytd": "YTD return",
                "company_name": "",
            },
            hover_data={
                "ticker": True,
                "return_ytd": ":.1%",
            },
        )

        fig_returns.update_layout(
            height=500,
            showlegend=False,
            xaxis_tickformat=".0%",
            margin=dict(
                l=10,
                r=20,
                t=20,
                b=20,
            ),
        )

        fig_returns.add_vline(
            x=0,
            line_dash="dot",
        )

        st.plotly_chart(
            fig_returns,
            use_container_width=True,
        )

        st.subheader("Contribution to portfolio YTD")

        contribution_data = portfolio.dropna(
            subset=["ytd_contribution"]
        ).copy()

        contribution_data = contribution_data.sort_values(
            "ytd_contribution",
            ascending=True,
        )

        fig_contribution = px.bar(
            contribution_data,
            x="ytd_contribution",
            y="company_name",
            orientation="h",
            labels={
                "ytd_contribution":
                    "Contribution to portfolio",
                "company_name": "",
            },
            hover_data={
                "ticker": True,
                "ytd_contribution": ":.1%",
            },
        )

        fig_contribution.update_layout(
            height=500,
            showlegend=False,
            xaxis_tickformat=".0%",
            margin=dict(
                l=10,
                r=20,
                t=20,
                b=20,
            ),
        )

        fig_contribution.add_vline(
            x=0,
            line_dash="dot",
        )

        st.plotly_chart(
            fig_contribution,
            use_container_width=True,
        )