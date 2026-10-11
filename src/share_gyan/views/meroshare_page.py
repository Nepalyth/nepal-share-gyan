"""My MeroShare: profile, portfolio and ASBA applications with allotment results."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from share_gyan import charts, data, meroshare
from share_gyan import theme as t
from share_gyan.views import account
from share_gyan.views.results import applications_table, summary_cards

_ENV_SNIPPET = (
    'MEROSHARE_DP="11200"          # 5-digit DP code or exact DP name\n'
    'MEROSHARE_USERNAME="your-username"\n'
    'MEROSHARE_PASSWORD="your-password"'
)


def _sign_in_view(error: str | None) -> None:
    t.render(t.hero("My", "MeroShare", "Sign in to see your profile, portfolio and ASBA applications, and whether your IPOs were allotted."))
    if error:
        st.error(error)
    left, right = st.columns([2, 3])
    with left:
        t.render(t.section("Sign in"))
        account.login_form()
    with right:
        t.render(t.section("Or use a .env file"))
        t.render('<div class="card flat"><div class="sub">Create a <b>.env</b> file in the project folder and restart the app. The app then signs in by itself.</div></div>')
        st.code(_ENV_SNIPPET, language="bash")


def _details_tab(acc: meroshare.Account) -> None:
    d = acc.details
    show = st.toggle("Show full BOID and account numbers", key="ms-reveal")
    boid = d["BOID"] if show else meroshare.mask(d["BOID"])
    cards = [
        t.stat_card("Name", d["Name"] or "—", note=d["Username"]),
        t.stat_card("BOID", boid or "—", note=d["Depository participant"]),
        t.stat_card("Demat expiry", d["Demat expiry"] or "—", note=f'Renewed {d["Renewed on"] or "—"}'),
        t.stat_card("Client code", d["Client code"] or "—", note="Used for ASBA and portfolio"),
    ]
    for col, card in zip(st.columns(4), cards):
        with col:
            t.render(card)
    st.write("")
    rows = [("Email", d["Email"]), ("Contact", d["Contact"]), ("Address", d["Address"]), ("Gender", d["Gender"])]
    kv = "".join(f'<div class="kv"><span>{t.esc(k)}</span><span>{t.esc(v or "—")}</span></div>' for k, v in rows)
    t.render(f'<div class="card flat"><div class="label">Personal details</div>{kv}</div>')

    t.render(t.section("Linked bank accounts"))
    if "banks" in acc.errors:
        st.warning(acc.errors["banks"])
    banks = acc.banks.copy()
    if banks.empty:
        t.render(t.empty_state("No bank accounts", "MeroShare returned no linked banks."))
        return
    if not show:
        banks["Account number"] = banks["Account number"].map(meroshare.mask)
    t.render(t.data_table(banks, [("Bank", "Bank", "wrap"), ("Account number", "Account number", "text"), ("Branch", "Branch", "text")]))


def _portfolio_tab(acc: meroshare.Account) -> None:
    if "portfolio" in acc.errors:
        st.warning(acc.errors["portfolio"])
    if acc.portfolio.empty:
        t.render(t.empty_state("No holdings", "Your demat account holds no shares right now."))
        return
    tot = acc.totals
    pct = tot["change"] / tot["prev_value"] * 100 if tot["prev_value"] else 0
    cards = [
        t.stat_card("Portfolio value", f'Rs {t.nepali_amount(tot["value"])}', note="At last transaction price"),
        t.stat_card("Previous close value", f'Rs {t.nepali_amount(tot["prev_value"])}'),
        t.stat_card("Day change", f'Rs {abs(tot["change"]):,.0f}', change=tot["change"], pct=pct),
        t.stat_card("Holdings", str(tot["scrips"]), note="Distinct scrips"),
    ]
    for col, card in zip(st.columns(4), cards):
        with col:
            t.render(card)
    st.write("")
    t.show_chart(charts.portfolio_bars(acc.portfolio))
    t.render(
        t.data_table(
            data.with_names(acc.portfolio),
            [("Symbol", "Symbol", "sym"), ("Balance", "Units", "int"), ("Prev close", "Prev close", "num"), ("LTP", "LTP", "num"),
             ("Value", "Value", "num"), ("Change", "Day change", "chg"), ("% Change", "%", "pct")],
        )
    )


def _asba_tab(acc: meroshare.Account) -> None:
    if "applications" in acc.errors:
        st.warning(acc.errors["applications"])
    apps = acc.applications
    if apps.empty:
        t.render(t.empty_state("No ASBA applications", "MeroShare returned no applications for this account."))
        return
    allotted = apps[apps["Result"].str.lower() == "allotted"]
    if not allotted.empty:
        lines = ", ".join(f'{r.Symbol} ({r.Allotted:,.0f} units)' if pd.notna(r.Allotted) else r.Symbol for r in allotted.itertuples())
        t.render(f'<div class="card kc ipo"><div class="label">Allotted</div><div class="value up" style="white-space:normal">{t.esc(lines)}</div></div>')
        st.write("")
    summary_cards(apps)
    st.write("")
    t.render(t.kind_legend())
    t.render(applications_table(apps))


def render() -> None:
    state = account.ensure_state()
    if state is None or state["error"]:
        _sign_in_view(state["error"] if state else None)
        return

    acc: meroshare.Account = state["account"]
    _, source = account.credentials()
    t.render(t.hero("My", "MeroShare", "Your profile, portfolio and ASBA applications, read directly from your MeroShare account."))
    account.status_bar(source, state["at"], acc.details["Name"])

    refresh, sign_out, _ = st.columns([1, 1, 4])
    creds, _src = account.credentials()
    if refresh.button("Refresh", icon=":material/refresh:", key="ms-refresh") and creds:
        account.run_check(creds)
        st.rerun()
    if source == "sign-in form" and sign_out.button("Sign out", icon=":material/logout:", key="ms-signout"):
        account.sign_out()
        st.rerun()

    details_tab, portfolio_tab, asba_tab = st.tabs(["My details", "Portfolio", "My ASBA"])
    with details_tab:
        _details_tab(acc)
    with portfolio_tab:
        _portfolio_tab(acc)
    with asba_tab:
        _asba_tab(acc)
    t.render(t.disclaimer())
