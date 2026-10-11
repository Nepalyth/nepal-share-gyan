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

* ShareSansar: indices, sub-indices, full price board, company names and links, all issue types (IPO, Right, FPO, Mutual fund, Debenture), SEBON pipeline, dividends, mergers, news
* Merolagani: NEPSE price history, AGM and right-share calendar, news

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
