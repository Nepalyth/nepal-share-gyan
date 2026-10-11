"""Cached, failure-tolerant access to the scraped market data."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TypeVar

import pandas as pd
import streamlit as st

from share_gyan import scraper

T = TypeVar("T")
TTL = 300  # seconds

SOURCES = {
    "ShareSansar": "https://www.sharesansar.com/",
    "Merolagani": "https://eng.merolagani.com/Index.aspx",
    "Share Gyan Nepal": "https://www.sharegyannepal.com/",
}

LEARN_LINKS = [
    ("Beginner's guide, part 1", "Basics to start investing in the share market",
     "https://www.sharesansar.com/newsdetail/beginners-guide-part-1-basics-to-start-your-investment-in-share-market"),
    ("Beginner's guide, part 2", "Opening accounts, ASBA and applying for IPOs",
     "https://www.sharesansar.com/newsdetail/beginners-guide-part-2-basics-to-start-your-investment-in-share-market"),
    ("Beginner's guide, part 3", "Reading prices, orders and market depth",
     "https://www.sharesansar.com/newsdetail/beginners-guide-part-3-basics-to-start-your-investment-in-share-market"),
    ("Share Gyan Nepal on YouTube", "Mutual funds, hydropower and market policy explainers",
     "https://www.youtube.com/@ShareGyanNepal"),
]

PORTALS = [
    ("CDSC IPO result", "https://iporesult.cdsc.com.np/"),
    ("Meroshare", "https://meroshare.cdsc.com.np/"),
    ("SEBON", "https://www.sebon.gov.np/"),
    ("NEPSE", "https://www.nepalstock.com/"),
]


def _guard(label: str, fn: Callable[[], T], default: T) -> T:
    try:
        return fn()
    except Exception as exc:  # network or markup changes must not take the app down
        st.toast(f"Could not load {label} ({type(exc).__name__})", icon=":material/cloud_off:")
        return default


def _try(fn: Callable[[], T], default: T) -> T:
    try:
        return fn()
    except Exception:
        return default


# --------------------------------------------------------------------------- #
# Companies
# --------------------------------------------------------------------------- #


@st.cache_data(ttl=86400, show_spinner=False)
def _companies() -> pd.DataFrame:
    return scraper.sharesansar_companies()


def companies() -> pd.DataFrame:
    return _guard("company names", _companies, pd.DataFrame())


def with_names(df: pd.DataFrame, symbol: str = "Symbol") -> pd.DataFrame:
    """Add full company name, sector and page link keyed on the symbol column."""
    if df is None or df.empty or symbol not in df:
        return df
    out = df.copy()
    directory = companies()
    known = directory.set_index("Symbol") if not directory.empty else pd.DataFrame(columns=["Company", "Sector", "Url"])
    if "Company" not in out:
        out["Company"] = out[symbol].map(known["Company"]).fillna("")
    if "Sector" not in out:
        out["Sector"] = out[symbol].map(known["Sector"]).fillna("")
    if "Url" not in out:
        out["Url"] = out[symbol].map(known["Url"])
    if directory.empty:  # directory unavailable: fall back to ShareSansar's URL pattern
        out["Url"] = out["Url"].fillna(out[symbol].map(scraper.company_url))
    return out


# --------------------------------------------------------------------------- #
# Market
# --------------------------------------------------------------------------- #


@st.cache_data(ttl=TTL, show_spinner=False)
def _market() -> dict:
    snapshot = scraper.sharesansar_market()
    snapshot["summary"] = _try(scraper.merolagani_summary, {})
    snapshot["fetched_at"] = datetime.now()
    return snapshot


def market() -> dict | None:
    return _guard("market summary", _market, None)


@st.cache_data(ttl=TTL, show_spinner=False)
def _board() -> dict:
    as_of, df = scraper.sharesansar_board()
    span = (df["52W High"] - df["52W Low"]).where(lambda s: s > 0)
    df["52W Position"] = ((df["LTP"] - df["52W Low"]) / span * 100).clip(0, 100).round(1)
    return {"as_of": as_of, "df": df}


def board() -> dict | None:
    b = _guard("price board", _board, None)
    return None if b is None else {"as_of": b["as_of"], "df": with_names(b["df"])}


@st.cache_data(ttl=TTL, show_spinner=False)
def _sectors() -> pd.DataFrame:
    return scraper.sharesansar_sectors()


def sectors() -> pd.DataFrame:
    return _guard("sector indices", _sectors, pd.DataFrame())


@st.cache_data(ttl=TTL, show_spinner=False)
def _history() -> pd.DataFrame:
    return scraper.merolagani_history()


def history() -> pd.DataFrame:
    return _guard("NEPSE history", _history, pd.DataFrame())


def breadth(df: pd.DataFrame) -> tuple[int, int, int]:
    advanced = int((df["Change"] > 0).sum())
    declined = int((df["Change"] < 0).sum())
    return advanced, declined, len(df) - advanced - declined


def top_gainers(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return df[df["Change"] > 0].sort_values("% Change", ascending=False).head(n)


def top_losers(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return df[df["Change"] < 0].sort_values("% Change").head(n)


def top_turnover(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return df.sort_values("Turnover", ascending=False).head(n)


# --------------------------------------------------------------------------- #
# Issues
# --------------------------------------------------------------------------- #


@st.cache_data(ttl=TTL, show_spinner=False)
def _issues() -> dict[str, pd.DataFrame]:
    return scraper.sharesansar_all_issues()


def issues() -> dict[str, pd.DataFrame]:
    return _guard("share issues", _issues, {})


def ipos() -> pd.DataFrame:
    return issues().get("IPO", pd.DataFrame())


@st.cache_data(ttl=TTL, show_spinner=False)
def _upcoming() -> pd.DataFrame:
    return scraper.sharesansar_upcoming()


def upcoming() -> pd.DataFrame:
    return _guard("upcoming issues", _upcoming, pd.DataFrame())


# --------------------------------------------------------------------------- #
# Corporate actions
# --------------------------------------------------------------------------- #


@st.cache_data(ttl=TTL, show_spinner=False)
def _dividends() -> pd.DataFrame:
    return scraper.sharesansar_dividends()


def dividends() -> pd.DataFrame:
    return _guard("dividends", _dividends, pd.DataFrame())


@st.cache_data(ttl=TTL, show_spinner=False)
def _corporate() -> dict[str, pd.DataFrame]:
    return scraper.merolagani_corporate()


def corporate() -> dict[str, pd.DataFrame]:
    return {k: with_names(v) for k, v in _guard("AGM and rights", _corporate, {}).items()}


@st.cache_data(ttl=TTL, show_spinner=False)
def _mergers() -> pd.DataFrame:
    return scraper.sharesansar_mergers()


def mergers() -> pd.DataFrame:
    return _guard("mergers", _mergers, pd.DataFrame())


# --------------------------------------------------------------------------- #
# News
# --------------------------------------------------------------------------- #


@st.cache_data(ttl=TTL * 2, show_spinner=False)
def _news() -> pd.DataFrame:
    return scraper.news()


def news() -> pd.DataFrame:
    return _guard("news", _news, pd.DataFrame())


def refresh() -> None:
    st.cache_data.clear()
