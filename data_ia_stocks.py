import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

INPUT_FILE = "input_companies.xlsx"
OUTPUT_FILE = "company_radar_output.xlsx"

def weighted_average(group, value_col, weight_col="market_cap_usd"):
    valid = group[[value_col, weight_col]].dropna()

    valid = valid[valid[weight_col] > 0]

    if valid.empty:
        return np.nan

    return np.average(
        valid[value_col],
        weights=valid[weight_col]
    )


def get_fx_to_usd(currency):
    """
    Returns FX conversion rate from local currency to USD.
    Example:
    EUR -> USD
    JPY -> USD
    USD -> USD
    """
    if currency is None or pd.isna(currency):
        return np.nan

    currency = str(currency).upper()

    if currency == "USD":
        return 1.0

    fx_ticker = f"{currency}USD=X"

    try:
        fx = yf.Ticker(fx_ticker)
        hist = fx.history(period="5d", auto_adjust=True)

        if hist.empty:
            return np.nan

        return hist["Close"].dropna().iloc[-1]

    except Exception:
        return np.nan


def get_returns(prices):
    last = prices.iloc[-1]

    def ret_since(days):
        if len(prices) <= days:
            return np.nan
        return last / prices.iloc[-days] - 1

    ytd_start = prices[prices.index >= f"{datetime.now().year}-01-01"]
    ytd_return = last / ytd_start.iloc[0] - 1 if len(ytd_start) > 0 else np.nan

    return {
        "return_1m": ret_since(21),
        "return_3m": ret_since(63),
        "return_6m": ret_since(126),
        "return_1y": ret_since(252),
        "return_5y": ret_since(252 * 5),
        "return_ytd": ytd_return,
        "return_since_listing": last / prices.iloc[0] - 1,
    }

def classify_market_cap_usd(market_cap_usd):
    if pd.isna(market_cap_usd):
        return "Unknown"
    elif market_cap_usd >= 200_000_000_000:
        return "Mega cap"
    elif market_cap_usd >= 10_000_000_000:
        return "Large cap"
    elif market_cap_usd >= 2_000_000_000:
        return "Mid cap"
    elif market_cap_usd >= 300_000_000:
        return "Small cap"
    else:
        return "Micro cap"


def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]


def calculate_momentum_score(row):
    score = 0

    if pd.notna(row.get("return_6m")) and row["return_6m"] > 0:
        score += 25

    if pd.notna(row.get("return_3m")) and row["return_3m"] > 0:
        score += 25

    if pd.notna(row.get("price_vs_sma_200")) and row["price_vs_sma_200"] > 0:
        score += 20

    if pd.notna(row.get("sma_50_vs_200")) and row["sma_50_vs_200"] > 0:
        score += 15

    if pd.notna(row.get("distance_from_52w_high")) and row["distance_from_52w_high"] > -0.10:
        score += 10

    if pd.notna(row.get("volume_vs_avg")) and row["volume_vs_avg"] > 1:
        score += 5

    return score


def classify_momentum(score):
    if score >= 80:
        return "Strong momentum"
    elif score >= 60:
        return "Positive momentum"
    elif score >= 40:
        return "Neutral"
    elif score >= 20:
        return "Weak momentum"
    else:
        return "Very weak momentum"


def analyze_ticker(input_row):
    ticker = str(input_row["ticker"]).strip().upper()

    stock = yf.Ticker(ticker)
    hist = stock.history(period="max", auto_adjust=True)

    if hist.empty:
        return {
            **input_row.to_dict(),
            "error": "No historical price data found"
        }

    close = hist["Close"].dropna()
    volume = hist["Volume"].dropna()

    info = stock.info

    returns = get_returns(close)

    last_price = close.iloc[-1]

    sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else np.nan
    sma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else np.nan

    high_52w = close.tail(252).max()
    low_52w = close.tail(252).min()

    volume_avg_50 = volume.rolling(50).mean().iloc[-1] if len(volume) >= 50 else np.nan
    last_volume = volume.iloc[-1] if len(volume) > 0 else np.nan

    market_cap_local = info.get("marketCap")
    market_cap_currency = info.get("currency")
    fx_to_usd = get_fx_to_usd(market_cap_currency)
    
    market_cap_usd = (
        market_cap_local * fx_to_usd
        if pd.notna(market_cap_local) and pd.notna(fx_to_usd)
        else np.nan
    )

    row = {
        **input_row.to_dict(),

        "yahoo_company_name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency"),
        "market_cap_local": market_cap_local,
        "market_cap_currency": market_cap_currency,
        "fx_to_usd": fx_to_usd,
        "market_cap_usd": market_cap_usd,
        "market_cap_bucket": classify_market_cap_usd(market_cap_usd),

        "listing_proxy_date": close.index[0].date(),
        "years_since_listing": round(
            (datetime.now().date() - close.index[0].date()).days / 365.25, 1
        ),

        "last_price": last_price,
        "sma_50": sma_50,
        "sma_200": sma_200,

        "price_vs_sma_50": last_price / sma_50 - 1 if pd.notna(sma_50) else np.nan,
        "price_vs_sma_200": last_price / sma_200 - 1 if pd.notna(sma_200) else np.nan,
        "sma_50_vs_200": sma_50 / sma_200 - 1 if pd.notna(sma_50) and pd.notna(sma_200) else np.nan,

        "high_52w": high_52w,
        "low_52w": low_52w,
        "distance_from_52w_high": last_price / high_52w - 1,
        "distance_from_52w_low": last_price / low_52w - 1,

        "rsi_14": calculate_rsi(close) if len(close) >= 14 else np.nan,
        "last_volume": last_volume,
        "avg_volume_50d": volume_avg_50,
        "volume_vs_avg": last_volume / volume_avg_50 if pd.notna(volume_avg_50) and volume_avg_50 != 0 else np.nan,

        **returns,

        "error": ""
    }

    row["momentum_score"] = calculate_momentum_score(row)
    row["momentum_label"] = classify_momentum(row["momentum_score"])

    return row


def main():
    input_path = Path(INPUT_FILE)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    input_df = pd.read_excel(INPUT_FILE)

    required_columns = ["ticker"]

    missing_columns = [
        col for col in required_columns
        if col not in input_df.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    results = []

    for _, input_row in input_df.iterrows():
        try:
            result = analyze_ticker(input_row)
            results.append(result)
        except Exception as e:
            results.append({
                **input_row.to_dict(),
                "error": str(e)
            })

    output_df = pd.DataFrame(results)

    sort_columns = ["ai_chain_category", "momentum_score"]

    existing_sort_columns = [
        col for col in sort_columns
        if col in output_df.columns
    ]

    if existing_sort_columns:
        output_df = output_df.sort_values(
            existing_sort_columns,
            ascending=[True, False][:len(existing_sort_columns)]
        )

    percentage_columns = [
        "return_1m",
        "return_3m",
        "return_6m",
        "return_1y",
        "return_5y",
        "return_ytd",
        "return_since_listing",
        "price_vs_sma_50",
        "price_vs_sma_200",
        "sma_50_vs_200",
        "distance_from_52w_high",
        "distance_from_52w_low",
    ]

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        output_df.to_excel(writer, sheet_name="company_radar", index=False)

        if "market_cap_usd" in output_df.columns:
            output_df["market_cap_usd_bn"] = output_df["market_cap_usd"] / 1_000_000_000

        if "ai_chain_category" in output_df.columns:
            summary = (
                output_df
                .groupby("ai_chain_category")
                .apply(
                    lambda g: pd.Series({
                        "companies": g["ticker"].count(),

                        "total_market_cap_usd_bn": g["market_cap_usd"].sum() / 1_000_000_000,
                        "avg_market_cap_usd_bn": g["market_cap_usd_bn"].mean(),
                        "median_market_cap_usd_bn": g["market_cap_usd_bn"].median(),

                        "avg_momentum_score": g["momentum_score"].mean(),
                        "median_momentum_score": g["momentum_score"].median(),
                        "mcap_weighted_momentum_score": weighted_average(g, "momentum_score"),

                        "companies_above_80_momentum": (g["momentum_score"] >= 80).sum(),
                        "pct_companies_above_80_momentum": (g["momentum_score"] >= 80).mean(),

                        "avg_ytd_return": g["return_ytd"].mean(),
                        "median_ytd_return": g["return_ytd"].median(),
                        "mcap_weighted_ytd_return": weighted_average(g, "return_ytd"),

                        "avg_1y_return": g["return_1y"].mean(),
                        "median_1y_return": g["return_1y"].median(),
                        "mcap_weighted_1y_return": weighted_average(g, "return_1y"),

                        "avg_5y_return": g["return_5y"].mean(),
                        "median_5y_return": g["return_5y"].median(),
                        "mcap_weighted_5y_return": weighted_average(g, "return_5y"),

                        "avg_since_listing_return": g["return_since_listing"].mean(),
                        "median_since_listing_return": g["return_since_listing"].median(),
                        "mcap_weighted_since_listing_return": weighted_average(g, "return_since_listing"),
                    })
                )
                .reset_index()
            )

            summary["momentum_breadth_label"] = np.select(
                [
                    summary["pct_companies_above_80_momentum"] >= 0.70,
                    summary["pct_companies_above_80_momentum"] >= 0.40,
                    summary["pct_companies_above_80_momentum"] >= 0.20,
                ],
                [
                    "Broad strong momentum",
                    "Moderate breadth",
                    "Narrow momentum",
                ],
                default="Weak breadth"
            )

            summary = summary.sort_values(
                ["mcap_weighted_momentum_score", "pct_companies_above_80_momentum"],
                ascending=[False, False]
            )

            summary.to_excel(writer, sheet_name="category_summary", index=False)

    print(f"Created output file: {OUTPUT_FILE}")
    print("Sheets written:")
    print("- company_radar")

    if "ai_chain_category" in output_df.columns:
        print("- category_summary")
    else:
        print("category_summary not written: missing ai_chain_category column")


if __name__ == "__main__":
    main()
