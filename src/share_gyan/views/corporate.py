"""Corporate actions: dividends, AGMs, rights and mergers."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from share_gyan import charts, data
from share_gyan import theme as t
from share_gyan.views import common


def _dividends_tab() -> None:
    df = data.dividends()
    if df.empty:
        common.unavailable("Dividends")
        return
    top = df.head(15)
    yields = df.dropna(subset=["Cash Yield %"])
    left, right = st.columns([3, 2])
    with left:
        t.show_chart(charts.dividend_stack(top))
    with right:
        if not yields.empty:
            best = yields.sort_values("Cash Yield %", ascending=False).iloc[0]
            t.render(t.stat_card("Highest cash yield", f'{best["Symbol"]} · {best["Cash Yield %"]:.2f}%', note=f'{best["Company"]}: cash {best["Cash %"]:.2f}% at Rs {best["LTP"]:,.0f}'))
            st.write("")
        big = df.sort_values("Total %", ascending=False).iloc[0]
        t.render(t.stat_card("Biggest payout", big["Symbol"], note=f'{big["Company"]}: {big["Total %"]:.2f}% total, book close {big["Book close"] or "TBA"}'))
    t.render(
        t.data_table(
            df,
            [("Symbol", "Symbol", "symlink"), ("Company", "Company", "wrap"), ("Bonus %", "Bonus %", "num"), ("Cash %", "Cash %", "num"),
             ("Total %", "Total %", "num"), ("LTP", "LTP", "num"), ("Cash Yield %", "Cash yield %", "num"), ("Book close", "Book close", "text"), ("Year", "Fiscal year", "text")],
        )
    )
    st.caption("Percentages are on the Rs 100 face value. Cash yield is the cash dividend divided by the last traded price.")


def _agm_tab() -> None:
    agm = data.corporate().get("agm", pd.DataFrame())
    if agm.empty:
        common.unavailable("AGM calendar")
        return
    agm = agm.sort_values("AGM").copy()
    agm["Days"] = (agm["AGM"] - pd.Timestamp.today().normalize()).dt.days
    t.render(t.data_table(agm, [("Symbol", "Company", "sym"), ("Fiscal year", "Fiscal year", "text"), ("Book close", "Book close", "date"), ("AGM", "AGM", "date"), ("Days", "Days to AGM", "int")]))
    st.caption("Buy before the last trading day ahead of book close to qualify for the dividend.")


def _rights_tab() -> None:
    right = data.corporate().get("right", pd.DataFrame())
    if right.empty:
        common.unavailable("Right shares")
        return
    t.render(t.data_table(right, [("Symbol", "Company", "sym"), ("Fiscal year", "Fiscal year", "text"), ("Ratio", "Ratio (existing : new)", "text")]))


def _mergers_tab() -> None:
    merged = data.mergers()
    if merged.empty:
        common.unavailable("Mergers")
        return
    t.render(t.data_table(merged, [(c, c, "wrap" if i < 2 else "text") for i, c in enumerate(merged.columns)]))


def render() -> None:
    t.render(t.hero("Corporate", "actions", "What companies are paying, when to hold, and which shareholder meetings are coming up."))
    tabs = st.tabs(["Dividends", "AGM calendar", "Right shares", "Mergers"])
    for tab, fn in zip(tabs, (_dividends_tab, _agm_tab, _rights_tab, _mergers_tab)):
        with tab:
            fn()
    t.render(t.disclaimer())
