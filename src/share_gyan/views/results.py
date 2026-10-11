"""IPO results: your allotment status from MeroShare, plus recently closed IPOs and allotment news."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from share_gyan import data
from share_gyan import theme as t
from share_gyan.views import account


def summary_cards(apps: pd.DataFrame) -> None:
    status = apps["Result"].str.lower()
    cards = [
        t.stat_card("Applications", str(len(apps)), note="Most recent first"),
        t.stat_card("Allotted", str((status == "allotted").sum()), note="Shares received"),
        t.stat_card("Not allotted", str((status == "not allotted").sum()), note="Lottery or rejected"),
        t.stat_card("Pending", str((~status.isin(["allotted", "not allotted"])).sum()), note="No result yet"),
    ]
    for col, card in zip(st.columns(4), cards):
        with col:
            t.render(card)


def applications_table(apps: pd.DataFrame, form_status: bool = True) -> str:
    apps = apps.assign(Kind=apps["Type"].map(t.kind_for))
    cols = [("Symbol", "Scrip", "symlink"), ("Company", "Company", "wrap"), ("Kind", "Type", "kind"), ("Applied", "Applied units", "int"), ("Allotted", "Allotted units", "int")]
    if form_status:
        cols.append(("Form status", "Form status", "text"))
    cols += [("Result", "Result", "allot"), ("Remark", "Remark", "wrap")]
    return t.data_table(data.with_names(apps), cols)


def _my_results() -> None:
    state = account.ensure_state()
    if state is None:
        t.render(t.empty_state("Sign in to see your results", "Open the MeroShare page and sign in, or add your login to .env. Your allotment status appears here automatically."))
        return
    if state["error"]:
        st.error(state["error"])
        t.render('<div class="sub">Fix the login on the MeroShare page, then come back.</div>')
        return
    acc = state["account"]
    creds, _ = account.credentials()
    if st.button("Check again", icon=":material/refresh:", key="results-refresh") and creds:
        account.run_check(creds)
        st.rerun()

    if "applications" in acc.errors:
        st.warning(acc.errors["applications"])
        return
    if acc.applications.empty:
        t.render(t.empty_state("No applications found", "MeroShare returned no ASBA applications for this account."))
        return
    summary_cards(acc.applications)
    st.write("")
    t.render(applications_table(acc.applications, form_status=False))


def _steps() -> str:
    steps = [
        ("Sign in once", "Use the MeroShare page, or put your DP, username and password in .env."),
        ("We read your ASBA list", "Every application you made, with its latest status."),
        ("Allotment is checked", "Each application's report is read for allotted units."),
        ("Re-check anytime", "Use Check again after an allotment is published."),
    ]
    rows = "".join(
        f'<div class="step"><div class="n">{i}</div><div><b>{t.esc(title)}</b><div class="sub">{t.esc(body)}</div></div></div>'
        for i, (title, body) in enumerate(steps, 1)
    )
    return f'<div class="card flat"><div class="label">How it works</div>{rows}</div>'


def render() -> None:
    ipos = data.ipos()
    closed = ipos[ipos["Status"] == "Closed"].sort_values("Closes", ascending=False).head(12) if not ipos.empty else ipos

    t.render(t.hero("IPO", "results", "See whether you were allotted shares straight from your MeroShare account, without leaving the app."))
    left, right = st.columns([3, 2])
    with left:
        t.render(t.section("My allotment results", "from MeroShare"))
        _my_results()
    with right:
        t.render(t.section("Guide"))
        t.render(_steps())

    t.render(t.section("Recently closed IPOs", "with allotment and listing dates"))
    t.render(
        t.data_table(
            closed,
            [("Symbol", "Symbol", "symlink"), ("Company", "Company", "wrap"), ("Units", "Units", "int"), ("Closes", "Closed", "date"),
             ("Allotment", "Allotment", "date"), ("Listing", "Listed", "date"), ("Manager", "Manager", "text")],
            "IPO history is unavailable right now.",
        )
    )

    t.render(t.section("Allotment announcements", "latest from ShareSansar"))
    news = data.news()
    t.render(t.news_list(news[news["Category"] == "Allotment"].head(8) if not news.empty else news))
    t.render(t.disclaimer())
