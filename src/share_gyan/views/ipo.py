"""IPO Center: open, upcoming, pipeline and past issues."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from share_gyan import charts, data
from share_gyan import theme as t
from share_gyan.views import common


def _cards(df: pd.DataFrame, empty_title: str, empty_msg: str) -> None:
    if df.empty:
        t.render(t.empty_state(empty_title, empty_msg))
        return
    rows = list(df.iterrows())
    for start in range(0, len(rows), 3):
        for col, (_, row) in zip(st.columns(3), rows[start : start + 3]):
            with col:
                t.render(common.issue_card(row))
        st.write("")


def _live_tab(issues: pd.DataFrame) -> None:
    if issues.empty:
        common.unavailable("Share issues")
        return
    live = common.live_issues()
    for status, title, sub, empty in (
        ("Open", "Open now", "accepting applications", "Nothing is open right now. New issues show up here as soon as they open."),
        ("Upcoming", "Opening soon", "with announced dates", "No issue has an announced opening date."),
        ("Coming soon", "Approved, date pending", "waiting for a date", "Nothing is waiting for a date."),
    ):
        part = live[live["Status"] == status]
        t.render(t.section(title, f"{len(part)} {sub}"))
        _cards(part, "Nothing here", empty)


def _pipeline_tab(up: pd.DataFrame) -> None:
    if up.empty:
        common.unavailable("SEBON pipeline")
        return
    query = st.text_input("Search pipeline", placeholder="Search company, sector or issue manager", label_visibility="collapsed", key="pipe-q")
    df = up
    if query:
        q = query.strip().lower()
        df = df[df[["Symbol", "Company", "Sector", "Manager"]].apply(lambda c: c.str.lower().str.contains(q, regex=False)).any(axis=1)]
    df = df.assign(Size=df["Amount"])
    t.render(
        t.data_table(
            df.head(30),
            [("Symbol", "Symbol", "symlink"), ("Company", "Company", "wrap"), ("Sector", "Sector", "text"), ("Units", "Units", "int"),
             ("Size", "Issue size", "money"), ("Manager", "Manager", "text"), ("SEBON", "Approved", "date")],
            "No pipeline issue matches that search.",
        )
    )
    st.caption(f"{len(df)} SEBON-approved issues waiting for an opening date. Showing the first {min(30, len(df))}.")


def _past_tab(ipos: pd.DataFrame) -> None:
    if ipos.empty:
        common.unavailable("IPO history")
        return
    past = ipos[ipos["Status"] == "Closed"].copy()
    past["Size"] = past["Units"] * past["Price"] / 1e7
    c1, c2 = st.columns([3, 2])
    query = c1.text_input("Search IPO", placeholder="Search symbol, company or manager", label_visibility="collapsed", key="past-q")
    order = c2.selectbox("Sort", ["Newest first", "Largest issue", "Oldest first"], label_visibility="collapsed", key="past-sort")
    if query:
        q = query.strip().lower()
        past = past[past[["Symbol", "Company", "Manager"]].apply(lambda c: c.str.lower().str.contains(q, regex=False)).any(axis=1)]
    col, asc = {"Newest first": ("Closes", False), "Largest issue": ("Size", False), "Oldest first": ("Closes", True)}[order]
    past = past.sort_values(col, ascending=asc)
    if past.empty:
        t.render(t.empty_state("No matches", "Try a different symbol or company name."))
        return
    t.show_chart(charts.issue_size_bars(past.head(14).dropna(subset=["Closes"])))
    t.render(
        t.data_table(
            past.head(40),
            [("Symbol", "Symbol", "symlink"), ("Company", "Company", "wrap"), ("Units", "Units", "int"), ("Size", "Size (Rs Cr)", "num"),
             ("Opens", "Opened", "date"), ("Closes", "Closed", "date"), ("Allotment", "Allotment", "date"), ("Listing", "Listed", "date"), ("Manager", "Manager", "text")],
        )
    )
    st.caption(f"{len(past)} closed IPOs. Showing the first {min(40, len(past))}.")


def _other_tab(kinds: dict[str, pd.DataFrame]) -> None:
    names = [k for k, df in kinds.items() if k != "IPO" and not df.empty]
    if not names:
        common.unavailable("Other issues")
        return
    kind = st.radio("Issue type", names, horizontal=True, label_visibility="collapsed")
    t.render(f'<div class="legend">{t.kind_tag(kind)}</div>')
    t.render(
        t.data_table(
            kinds[kind].head(25),
            [("Symbol", "Symbol", "symlink"), ("Company", "Company", "wrap"), ("Units", "Units", "int"), ("Opens", "Opens", "date"),
             ("Closes", "Closes", "date"), ("Manager", "Manager", "text"), ("Status", "Status", "status")],
        )
    )


def render() -> None:
    kinds, ipos, up = data.issues(), data.ipos(), data.upcoming()
    issues = common.all_issues()
    is_ipo = issues["Kind"].isin(common.IPO_KINDS) if not issues.empty else pd.Series(dtype=bool)
    ipo_open = int(((issues["Status"] == "Open") & is_ipo).sum()) if not issues.empty else 0
    other_open = int(((issues["Status"] == "Open") & ~is_ipo).sum()) if not issues.empty else 0
    soon_n = int(((issues["Status"] == "Upcoming") & is_ipo).sum()) if not issues.empty else 0
    closed_n = int((ipos["Status"] == "Closed").sum()) if not ipos.empty else 0

    t.render(
        t.hero(
            "IPO", "center",
            "What is open for application, what is about to open, what SEBON has approved and how past issues went. Issue data comes from ShareSansar.",
            [t.live_chip(f"{ipo_open} IPOs open"), f"{other_open} other issues open", f"{len(up)} in SEBON pipeline"],
        )
    )
    for col, card in zip(
        st.columns(4),
        [
            t.stat_card("IPOs open", str(ipo_open), note="Accepting applications"),
            t.stat_card("Other issues open", str(other_open), note="Right, FPO, debenture, fund"),
            t.stat_card("IPOs opening soon", str(soon_n), note="Dates announced"),
            t.stat_card("SEBON pipeline", str(len(up)), note=f"{closed_n} past IPOs on record"),
        ],
    ):
        with col:
            t.render(card)

    st.write("")
    t.render(t.kind_legend())
    live_tab, pipeline_tab, past_tab, other_tab = st.tabs(["Open and upcoming", "IPO pipeline", "Past IPOs", "Other issues"])
    with live_tab:
        _live_tab(issues)
    with pipeline_tab:
        _pipeline_tab(up)
    with past_tab:
        _past_tab(ipos)
    with other_tab:
        _other_tab(kinds)
    t.render(t.disclaimer())
