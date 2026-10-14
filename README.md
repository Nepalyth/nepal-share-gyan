# Share-Gyan

A simple Streamlit app for the share information where you can get the daily market stock information.

## Setup

* prerequisite:

> Install [uv](https://docs.astral.sh/uv/):

* Create and activate venv

```bash
uv venv
source .venv/bin/activate
```

* Install Dependencies

```bash
uv sync
```

## Run

```bash
uv run app
```

This starts the Streamlit server and opens the app in your browser.

## Data

Everything is scraped live (cached for 5 minutes; the refresh button in the header re-scrapes):

* `ShareSansar`: indices, sub-indices, full price board, company names and links, all issue types (IPO, Right, FPO, Mutual fund, Debenture), SEBON pipeline, dividends, mergers, news
* `Merolagani`: NEPSE price history, AGM and right-share calendar, news

Share Gyan Nepal renders client-side through a private, header-gated API, so it is linked but not scraped.

The light/dark switch in the header is stored in the URL (`?theme=dark`).

## IPO results from your MeroShare account

The MeroShare page signs in to your account and shows your details, portfolio and ASBA applications with allotment results (also summarised on IPO Results). Either fill in the sign-in form (kept in memory for the browser session only) or use a `.env` file:

```bash
cp .env.example .env   # then fill in MEROSHARE_DP, MEROSHARE_USERNAME, MEROSHARE_PASSWORD
```

* `.env` is git-ignored. Restart the app after editing it.
* The login goes only to `webbackend.cdsc.com.np`, is never logged or displayed, and nothing is stored on disk.
* The server is bound to `127.0.0.1` (see `.streamlit/config.toml`) because the page shows private account data. Do not expose it publicly.

## Screenshots

> ### Dashboard

<table>
  <tr>
    <td align="center"><b>Dark</b><br><img src="docs/screenshots/dashboard.png" alt="Dashboard (dark)"></td>
    <td align="center"><b>Light</b><br><img src="docs/screenshots/dashboard_light.png" alt="Dashboard (light)"></td>
  </tr>
</table>

> ### Market Trend

<table>
  <tr>
    <td align="center"><b>Dark</b><br><img src="docs/screenshots/market_trend.png" alt="Market Trend (dark)"></td>
    <td align="center"><b>Light</b><br><img src="docs/screenshots/market_trends_light.png" alt="Market Trend (light)"></td>
  </tr>
</table>

> ### IPO Info

<table>
  <tr>
    <td align="center"><b>Dark</b><br><img src="docs/screenshots/ipo_info.png" alt="IPO Info (dark)"></td>
    <td align="center"><b>Light</b><br><img src="docs/screenshots/ipo_center_light.png" alt="IPO Info (light)"></td>
  </tr>
</table>

> ### IPO Results

<table>
  <tr>
    <td align="center"><b>Dark</b><br><img src="docs/screenshots/ipo_results.png" alt="IPO Results (dark)"></td>
    <td align="center"><b>Light</b><br><img src="docs/screenshots/ipo_results_light.png" alt="IPO Results (light)"></td>
  </tr>
</table>

> ### MeroShare

<table>
  <tr>
    <td align="center"><b>Dark</b><br><img src="docs/screenshots/meroshare.png" alt="MeroShare (dark)"></td>
    <td align="center"><b>Light</b><br><img src="docs/screenshots/meroshare_light.png" alt="MeroShare (light)"></td>
  </tr>
</table>

> ### News Hub

<table>
  <tr>
    <td align="center"><b>Dark</b><br><img src="docs/screenshots/news_hub.png" alt="News Hub (dark)"></td>
    <td align="center"><b>Light</b><br><img src="docs/screenshots/news_light.png" alt="News Hub (light)"></td>
  </tr>
</table>

> ### Corporate Actions

<table>
  <tr>
    <td align="center"><b>Dark</b><br><img src="docs/screenshots/corporate_actions.png" alt="Corporate Actions (dark)"></td>
    <td align="center"><b>Light</b><br><img src="docs/screenshots/corporate_actions_light.png" alt="Corporate Actions (light)"></td>
  </tr>
</table>

> ### Tools

<table>
  <tr>
    <td align="center"><b>Dark</b><br><img src="docs/screenshots/tools.png" alt="Tools (dark)"></td>
    <td align="center"><b>Light</b><br><img src="docs/screenshots/tools_light.png" alt="Tools (light)"></td>
  </tr>
</table>
