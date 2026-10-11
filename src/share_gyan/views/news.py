"""News hub: headlines scraped from ShareSansar and Merolagani."""

from __future__ import annotations

import streamlit as st

from share_gyan import data
from share_gyan import theme as t
from share_gyan.views import common


def render() -> None:
    news = data.news()
    t.render(
        t.hero(
            "News", "hub",
            "Market wrap-ups, IPO and dividend announcements, economy and analysis from the sources.",
            [f"{len(news)} stories", *data.SOURCES],
        )
    )
    if news.empty:
        common.unavailable("News")
        return

    query = st.text_input("Search news", placeholder="Search headlines, e.g. dividend, SEBON, hydropower", label_visibility="collapsed")
    if query:
        news = news[news["Title"].str.contains(query.strip(), case=False, regex=False)]
    if news.empty:
        t.render(t.empty_state("No stories found", "Try a broader search term."))
        return

    top = news.iloc[0]
    t.render(
        f'<div class="card flat"><div class="news-meta">{t.tag("Top story")}{t.tag(top["Category"])}<span>{top["Date"]:%d %b %Y}</span></div>'
        f'<a href="{t.esc(top["Url"])}" target="_blank" rel="noopener noreferrer" style="display:block;font-size:1.3rem;font-weight:650;line-height:1.35;margin:10px 0 4px;color:var(--text)">{t.esc(top["Title"])}</a>'
        f'<div class="news-meta"><span>{t.esc(top["Source"])}</span></div></div>'
    )
    st.write("")

    categories = ["All", *sorted(news["Category"].unique())]
    for tab, cat in zip(st.tabs(categories), categories):
        with tab:
            t.render(t.news_list((news if cat == "All" else news[news["Category"] == cat]).head(25)))

    t.render(t.section("Sources"))
    for col, (name, url) in zip(st.columns(len(data.SOURCES)), data.SOURCES.items()):
        col.link_button(name, url, width="stretch")
    t.render(t.disclaimer())
