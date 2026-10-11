"""Dashboard: the at-a-glance overview."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from share_gyan import data
from share_gyan import theme as t
from share_gyan.views import common


def _quotes_card(m: dict) -> str:
    rows = []
    for r in m["bullion"].itertuples(index=False):
        rows.append(f'<div class="kv"><span>{t.esc(r.Name)}</span><span>Rs {r.Price:,.0f} {t.pill(r.Change, digits=0)}</span></div>')
    for r in m["forex"].head(4).itertuples(index=False):
        rows.append(f'<div class="kv"><span>{t.esc(r.Currency)} / NPR</span><span>{r.Buy:.2f} · {r.Sell:.2f}</span></div>')
    return f'<div class="card"><div class="label">Bullion and forex</div>{"".join(rows)}</div>'


def _agm_table() -> str:
    agm = data.corporate().get("agm", pd.DataFrame())
    if agm.empty:
        return t.empty_state("No AGMs listed", "Nothing scheduled right now.")
    agm = agm.sort_values("AGM").head(6).copy()
    agm["In"] = (agm["AGM"] - pd.Timestamp.today().normalize()).dt.days.map(lambda d: f"{d} d")
    return t.data_table(agm, [("Symbol", "Company", "sym"), ("AGM", "AGM", "date"), ("In", "In", "text")])


def render() -> None:
    m, b = data.market(), data.board()
    if m is None or b is None:
        t.render(t.hero("Market", "overview"))
        common.unavailable("Market data")
        return

    board, summary = b["df"], m["summary"]
    indices = m["indices"].set_index("Name")
    nepse = indices.loc["NEPSE"]
    hist = data.history()
    spark = hist["Close"].tail(14).tolist() if not hist.empty else None

    t.render(
        t.hero(
            "Nepal's market,", "at a glance",
            "Live index levels, movers, issues and headlines scraped from ShareSansar and Merolagani.",
            [t.live_chip(f'Trading day {m["as_of"]}'), f"{len(board)} scrips traded", f'{summary.get("transactions", 0):,.0f} transactions'],
        )
    )

    cards = [
        t.stat_card("NEPSE", t.num(nepse["Close"]), nepse["Change"], nepse["Pct"], spark=spark, xl=True),
        t.stat_card("Sensitive", t.num(indices.loc["Sensitive", "Close"]), indices.loc["Sensitive", "Change"], indices.loc["Sensitive", "Pct"]),
        t.stat_card("Float", t.num(indices.loc["Float", "Close"]), indices.loc["Float", "Change"], indices.loc["Float", "Pct"]),
        t.stat_card("Turnover", f'Rs {t.nepali_amount(summary.get("turnover", nepse["Turnover"]))}', note=f'{summary.get("shares", 0):,.0f} shares'),
        t.stat_card("Market cap", f'Rs {t.nepali_amount(summary.get("market_cap", 0))}', note=f'Float Rs {t.nepali_amount(summary.get("float_cap", 0))}'),
    ]
    for col, card in zip(st.columns(5), cards):
        with col:
            t.render(card)

    t.render(t.section("NEPSE trend", "daily close"))
    left, right = st.columns([2, 1])
    with left:
        common.trend_chart("dash-range")
    with right:
        t.render(t.breadth_card(*data.breadth(board)))
        st.write("")
        t.render(_quotes_card(m))

    t.render(t.section("Market movers", "top 8"))
    g, l, v = st.columns(3)
    with g:
        t.render('<div class="label" style="margin:0 0 8px">Top gainers</div>')
        t.render(t.mover_table(data.top_gainers(board, 8)))
    with l:
        t.render('<div class="label" style="margin:0 0 8px">Top losers</div>')
        t.render(t.mover_table(data.top_losers(board, 8)))
    with v:
        t.render('<div class="label" style="margin:0 0 8px">Top turnover</div>')
        t.render(t.mover_table(data.top_turnover(board, 8), "turnover"))

    t.render(t.section("Issues radar", "open now and coming soon"))
    live = common.live_issues().head(3)
    if live.empty:
        t.render(t.empty_state("No open or upcoming issues", "Check the IPO Center for SEBON-approved issues in the pipeline."))
    else:
        for col, (_, row) in zip(st.columns(3), live.iterrows()):
            with col:
                t.render(common.issue_card(row))

    sectors = data.sectors()
    if not sectors.empty:
        t.render(t.section("Sector heat", "% change by sub-index"))
        t.render(t.heat_tiles(sectors))

    t.render(t.section("Headlines and AGM calendar"))
    news_col, agm_col = st.columns([3, 2])
    with news_col:
        t.render(t.news_list(data.news().head(6)))
    with agm_col:
        t.render(_agm_table())

    t.render(t.disclaimer(m["fetched_at"]))
