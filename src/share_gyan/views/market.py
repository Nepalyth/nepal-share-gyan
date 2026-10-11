"""Market trends: indices, sectors, movers and the full price board."""

from __future__ import annotations

import streamlit as st

from share_gyan import charts, data
from share_gyan import theme as t
from share_gyan.views import common


def _index_tab(m: dict) -> None:
    for col, r in zip(st.columns(4), m["indices"].itertuples(index=False)):
        with col:
            t.render(t.stat_card(r.Name, t.num(r.Close), r.Change, r.Pct, note=f"Day range {r.Low:,.2f} – {r.High:,.2f}"))
    st.write("")
    common.trend_chart("market-range", 380)


def _sector_tab() -> None:
    sec = data.sectors()
    if sec.empty:
        common.unavailable("Sector data")
        return
    t.render(t.heat_tiles(sec))
    left, right = st.columns(2)
    with left:
        t.render(t.section("Momentum", "% change today"))
        t.show_chart(charts.sector_change_bars(sec))
    with right:
        t.render(t.section("Money flow", "turnover"))
        t.show_chart(charts.sector_turnover_bars(sec))
    t.render(t.section("52-week position", "left is the yearly low, right is the yearly high"))
    t.render(
        t.data_table(
            sec.sort_values("52W Position", ascending=False),
            [("Sector", "Sector", "text"), ("Index", "Index", "num"), ("% Change", "Change", "pct"), ("Turnover", "Turnover", "money"),
             ("52W Low", "52W low", "num"), ("52W High", "52W high", "num"), ("52W Position", "Position", "range")],
        )
    )


def _movers_tab(board) -> None:
    g, l, v = st.columns(3)
    with g:
        t.render(t.section("Gainers"))
        t.render(t.mover_table(data.top_gainers(board, 15)))
    with l:
        t.render(t.section("Losers"))
        t.render(t.mover_table(data.top_losers(board, 15)))
    with v:
        t.render(t.section("Turnover"))
        t.render(t.mover_table(data.top_turnover(board, 15), "turnover"))


def _board_tab(board) -> None:
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    query = c1.text_input("Search symbol or company", placeholder="Search symbol or company, e.g. NABIL", label_visibility="collapsed")
    side = c2.selectbox("Show", ["All", "Gainers", "Losers", "Unchanged"], label_visibility="collapsed")
    sort = c3.selectbox("Sort", ["% Change", "Turnover", "Volume", "LTP", "Symbol"], label_visibility="collapsed")
    rows = c4.selectbox("Rows", [25, 50, 100, 400], index=1, format_func=lambda n: f"{n} rows", label_visibility="collapsed")

    df = board
    if query:
        q = query.strip()
        df = df[df["Symbol"].str.contains(q, case=False, regex=False) | df["Company"].str.contains(q, case=False, regex=False)]
    df = {"Gainers": df[df["Change"] > 0], "Losers": df[df["Change"] < 0], "Unchanged": df[df["Change"] == 0]}.get(side, df)
    df = df.sort_values(sort, ascending=sort == "Symbol" or (sort == "% Change" and side == "Losers"))
    t.render(
        t.data_table(
            df.head(rows),
            [("Symbol", "Symbol", "sym"), ("LTP", "LTP", "num"), ("Change", "Change", "chg"), ("% Change", "%", "pct"),
             ("Open", "Open", "num"), ("High", "High", "num"), ("Low", "Low", "num"), ("Volume", "Volume", "int"),
             ("Turnover", "Turnover", "money"), ("Trades", "Trades", "int"), ("52W Position", "52W range", "range")],
            "No scrip matches that search.",
        )
    )
    st.caption(f"Showing {min(rows, len(df))} of {len(df)} scrips from the latest trading day.")


def render() -> None:
    m, b = data.market(), data.board()
    if m is None or b is None:
        t.render(t.hero("Market", "trends"))
        common.unavailable("Market data")
        return

    t.render(
        t.hero(
            "Market", "trends",
            "Index direction, sector rotation, leaders and laggards from the latest NEPSE session.",
            [t.live_chip(f'Trading day {m["as_of"]}'), f'{(b["df"]["Change"] > 0).sum()} up · {(b["df"]["Change"] < 0).sum()} down'],
        )
    )
    index_tab, sector_tab, movers_tab, board_tab = st.tabs(["Indices", "Sectors", "Movers", "Price board"])
    with index_tab:
        _index_tab(m)
    with sector_tab:
        _sector_tab()
    with movers_tab:
        _movers_tab(b["df"])
    with board_tab:
        _board_tab(b["df"])
    t.render(t.disclaimer(m["fetched_at"]))
