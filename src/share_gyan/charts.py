"""Altair chart builders. Values are labelled on the chart itself; colors follow the active theme."""

from __future__ import annotations

import altair as alt
import pandas as pd

from share_gyan.theme import area_gradient, palette, style_chart


def _label_marks(p: dict, **kw) -> dict:
    # No stroke halo: Vega paints text strokes over the glyphs and hides them.
    return {"color": p["text"], "fontSize": 12, "fontWeight": 600, **kw}


def nepse_area(df: pd.DataFrame, height: int = 360):
    p = palette()
    lo, hi = float(df["Close"].min()), float(df["Close"].max())
    pad = (hi - lo) * 0.18 or 1.0
    long_range = len(df) > 90
    axis = (
        alt.Axis(format="%b %y", tickCount={"interval": "month", "step": 1}, labelFlush=False, title="Date")
        if long_range
        else alt.Axis(format="%d %b", labelFlush=False, title="Date")
    )
    base = alt.Chart(df).encode(
        x=alt.X("Date:T", axis=axis, scale=alt.Scale(padding=36)),
        y=alt.Y("Close:Q", title="NEPSE index (points)", scale=alt.Scale(domain=[lo - pad, hi + pad], clamp=True)),
        tooltip=[alt.Tooltip("Date:T", format="%d %b %Y"), alt.Tooltip("Close:Q", format=",.2f"), alt.Tooltip("High:Q", format=",.2f"), alt.Tooltip("Low:Q", format=",.2f")],
    )
    area = base.mark_area(line={"color": p["accent"], "strokeWidth": 2.4}, color=area_gradient(), interpolate="monotone", clip=True)
    hover = base.mark_circle(opacity=0, size=200)

    first, last = df.iloc[0], df.iloc[-1]
    change = (last["Close"] / first["Close"] - 1) * 100
    notes = pd.DataFrame(
        [
            {"Date": first["Date"], "Close": first["Close"], "Label": f'{first["Close"]:,.0f}', "Tone": "edge", "Dy": -12},
            {"Date": df.loc[df["Close"].idxmax(), "Date"], "Close": hi, "Label": f"High {hi:,.0f}", "Tone": "up", "Dy": -12},
            {"Date": df.loc[df["Close"].idxmin(), "Date"], "Close": lo, "Label": f"Low {lo:,.0f}", "Tone": "down", "Dy": 18},
            {"Date": last["Date"], "Close": last["Close"], "Label": f'{last["Close"]:,.0f} ({change:+.1f}%)', "Tone": "now", "Dy": -12},
        ]
    )
    colors = alt.Scale(domain=["edge", "up", "down", "now"], range=[p["muted"], p["up"], p["down"], p["accent"]])
    pts = alt.Chart(notes).encode(x="Date:T", y="Close:Q", color=alt.Color("Tone:N", scale=colors, legend=None))
    dots = pts.mark_point(filled=True, size=90, stroke=p["bg2"], strokeWidth=2)
    # edge labels are anchored away from the plot border so they never clip
    txt = alt.Chart(notes).encode(x="Date:T", y="Close:Q")
    labels = [
        txt.mark_text(**_label_marks(p, align="left", dx=6, dy=22)).encode(text="Label:N").transform_filter(alt.datum.Tone == "edge"),
        txt.mark_text(**_label_marks(p, align="center", dy=-14)).encode(text="Label:N").transform_filter(alt.datum.Tone == "up"),
        txt.mark_text(**_label_marks(p, align="center", dy=20)).encode(text="Label:N").transform_filter(alt.datum.Tone == "down"),
        txt.mark_text(**_label_marks(p, align="right", dx=-8, dy=22)).encode(text="Label:N").transform_filter(alt.datum.Tone == "now"),
    ]
    return style_chart(alt.layer(area, hover, dots, *labels), height)


def sector_change_bars(df: pd.DataFrame, height: int = 420):
    p = palette()
    data = df.rename(columns={"% Change": "Pct"})
    base = alt.Chart(data).encode(y=alt.Y("Sector:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200)), x=alt.X("Pct:Q", title="% change today", scale=alt.Scale(padding=44)))
    bars = base.mark_bar(cornerRadiusEnd=8, size=16).encode(
        color=alt.condition(alt.datum.Pct >= 0, alt.value(p["up"]), alt.value(p["down"])),
        tooltip=["Sector", alt.Tooltip("Pct:Q", format="+.2f", title="% change"), alt.Tooltip("Index:Q", format=",.2f")],
    )
    pos = base.mark_text(**_label_marks(p, align="left", dx=6)).encode(text=alt.Text("Pct:Q", format="+.2f")).transform_filter(alt.datum.Pct >= 0)
    neg = base.mark_text(**_label_marks(p, align="right", dx=-6)).encode(text=alt.Text("Pct:Q", format="+.2f")).transform_filter(alt.datum.Pct < 0)
    return style_chart(alt.layer(bars, pos, neg), height)


def sector_turnover_bars(df: pd.DataFrame, height: int = 420):
    p = palette()
    data = df.assign(Crore=df["Turnover"] / 1e7)
    base = alt.Chart(data).encode(
        y=alt.Y("Sector:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200)),
        x=alt.X("Crore:Q", title="Turnover (Rs crore)", scale=alt.Scale(padding=36)),
    )
    bars = base.mark_bar(cornerRadiusEnd=8, size=16, color=p["accent"]).encode(tooltip=["Sector", alt.Tooltip("Crore:Q", format=",.2f", title="Rs crore")])
    text = base.mark_text(**_label_marks(p, align="left", dx=6)).encode(text=alt.Text("Crore:Q", format=",.1f"))
    return style_chart(alt.layer(bars, text), height)


def issue_size_bars(df: pd.DataFrame, height: int = 320):
    p = palette()
    order = df.sort_values("Closes", ascending=False)["Symbol"].tolist()
    base = alt.Chart(df).encode(
        x=alt.X("Symbol:N", sort=order, title="IPO (newest first)", axis=alt.Axis(labelAngle=-40)),
        y=alt.Y("Size:Q", title="Issue size (Rs crore)", scale=alt.Scale(padding=18)),
    )
    bars = base.mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, color=p["accent"]).encode(
        tooltip=["Symbol", "Company", alt.Tooltip("Units:Q", format=",.0f"), alt.Tooltip("Size:Q", format=",.2f", title="Rs crore")]
    )
    text = base.mark_text(**_label_marks(p, align="center", dy=-8)).encode(text=alt.Text("Size:Q", format=",.1f"))
    return style_chart(alt.layer(bars, text), height)


def dividend_stack(df: pd.DataFrame, height: int = 340):
    p = palette()
    order = df["Symbol"].tolist()
    long = df.melt(id_vars="Symbol", value_vars=["Cash %", "Bonus %"], var_name="Type", value_name="Percent").dropna()
    bars = (
        alt.Chart(long)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("Symbol:N", title="Company", sort=order, axis=alt.Axis(labelAngle=-40)),
            y=alt.Y("Percent:Q", title="Dividend (% of Rs 100 face value)", scale=alt.Scale(padding=18)),
            color=alt.Color("Type:N", scale=alt.Scale(domain=["Cash %", "Bonus %"], range=[p["accent"], p["accent2"]]), legend=alt.Legend(orient="top", title=None)),
            tooltip=["Symbol", "Type", alt.Tooltip("Percent:Q", format=".3f")],
        )
    )
    totals = (
        alt.Chart(df.assign(Total=df["Cash %"].fillna(0) + df["Bonus %"].fillna(0)))
        .mark_text(**_label_marks(p, align="center", dy=-8))
        .encode(x=alt.X("Symbol:N", sort=order), y="Total:Q", text=alt.Text("Total:Q", format=".1f"))
    )
    return style_chart(alt.layer(bars, totals), height)


def sip_growth(df: pd.DataFrame, height: int = 320):
    p = palette()
    long = df.melt(id_vars="Year", value_vars=["Invested", "Value"], var_name="Series", value_name="Rs")
    ends = long[long["Year"] == long["Year"].max()].assign(Label=lambda d: d["Rs"].map(lambda v: f"Rs {v:,.0f}"))
    base = alt.Chart(long).encode(
        x=alt.X("Year:Q", title="Years invested", axis=alt.Axis(tickMinStep=1, grid=False), scale=alt.Scale(domain=[0, int(long["Year"].max())], nice=False)),
        y=alt.Y("Rs:Q", title="Rupees", axis=alt.Axis(format="~s")),
        color=alt.Color("Series:N", scale=alt.Scale(domain=["Invested", "Value"], range=[p["muted"], p["accent"]]), legend=alt.Legend(orient="top", title=None)),
    )
    line = base.mark_line(strokeWidth=2.6, interpolate="monotone").encode(tooltip=["Series", "Year", alt.Tooltip("Rs:Q", format=",.0f")])
    labels = (
        alt.Chart(ends)
        .mark_text(**_label_marks(p, align="right", dx=-6, dy=-10))
        .encode(x="Year:Q", y="Rs:Q", text="Label:N")
    )
    return style_chart(alt.layer(line, labels), height)


def portfolio_bars(df: pd.DataFrame, height: int = 340):
    p = palette()
    top = df.sort_values("Value", ascending=False).head(15).rename(columns={"% Change": "Pct"})
    order = top["Symbol"].tolist()
    base = alt.Chart(top).encode(
        x=alt.X("Symbol:N", sort=order, title="Holding", axis=alt.Axis(labelAngle=-40)),
        y=alt.Y("Value:Q", title="Value at last price (Rs)", axis=alt.Axis(format="~s"), scale=alt.Scale(padding=18)),
    )
    bars = base.mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
        color=alt.condition(alt.datum.Change >= 0, alt.value(p["up"]), alt.value(p["down"])),
        tooltip=["Symbol", "Company", alt.Tooltip("Balance:Q", format=",.0f"), alt.Tooltip("Value:Q", format=",.0f"), alt.Tooltip("Pct:Q", format="+.2f")],
    )
    text = base.mark_text(**_label_marks(p, align="center", dy=-8)).encode(text=alt.Text("Value:Q", format="~s"))
    return style_chart(alt.layer(bars, text), height)
