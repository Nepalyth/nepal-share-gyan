"""Send a WhatsApp message (via Twilio) when a new IPO or debenture opens for application.

Run on a schedule, e.g. `uv run notify-ipo` from cron. Each opened issue is announced once.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import find_dotenv, load_dotenv

from share_gyan import scraper

TWILIO_MESSAGES = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
SANDBOX_FROM = "whatsapp:+14155238886"
ALERT_KINDS = ("IPO", "IPO (Local)", "Debenture")
ROOT = Path(__file__).resolve().parents[2]


def _load_env() -> None:
    load_dotenv(find_dotenv(usecwd=True))
    load_dotenv(ROOT / ".env")


def _state_path() -> Path:
    return Path(os.getenv("NOTIFY_STATE_FILE") or ROOT / ".notify_state.json")


def _read_seen(path: Path) -> set[str]:
    try:
        return set(json.loads(path.read_text()))
    except (OSError, ValueError):
        return set()


def _fmt_date(value) -> str:
    return pd.Timestamp(value).strftime("%d %b %Y") if pd.notna(value) else "TBA"


def open_ipos() -> pd.DataFrame:
    issues = scraper.sharesansar_all_issues()
    frames = [df.assign(Kind=kind) for kind, df in issues.items() if kind in ALERT_KINDS and not df.empty]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    return df[df["Status"] == "Open"].reset_index(drop=True)


def _key(row: pd.Series) -> str:
    return f'{row["Kind"]}|{row["Symbol"]}|{_fmt_date(row["Opens"])}'


def build_message(rows: pd.DataFrame) -> str:
    lines = ["Open for application" if len(rows) == 1 else f"{len(rows)} issues open for application", ""]
    for r in rows.itertuples():
        price = f"Rs {r.Price:,.0f}" if pd.notna(r.Price) else "price TBA"
        units = f"{r.Units:,.0f} units" if pd.notna(r.Units) else "units TBA"
        lines.append(f"{r.Symbol} - {r.Company}")
        lines.append(f"{r.Kind} | {price} | {units}")
        lines.append(f"Opens {_fmt_date(r.Opens)}, closes {_fmt_date(r.Closes)}")
        if r.Manager:
            lines.append(f"Manager: {r.Manager}")
        lines.append("")
    return "\n".join(lines).strip()


def _send_one(sid: str, token: str, sender: str, phone: str, text: str) -> None:
    try:
        resp = requests.post(
            TWILIO_MESSAGES.format(sid=sid),
            auth=(sid, token),
            data={"From": sender, "To": f"whatsapp:+{phone}", "Body": text},
            timeout=(5, 30),
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach Twilio ({type(exc).__name__}).") from None
    if resp.status_code >= 300:
        try:
            detail = resp.json().get("message", "")
        except ValueError:
            detail = ""
        raise RuntimeError(f"Twilio rejected the message (HTTP {resp.status_code}). {detail}".strip())


def send_whatsapp(text: str) -> None:
    """Send to every number in WHATSAPP_PHONE (comma-separated); raises if any send fails."""
    sid, token = os.getenv("TWILIO_ACCOUNT_SID", "").strip(), os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    phones = [p.strip().removeprefix("whatsapp:").lstrip("+") for p in os.getenv("WHATSAPP_PHONE", "").split(",")]
    phones = [p for p in phones if p]
    sender = os.getenv("TWILIO_WHATSAPP_FROM", "").strip() or SANDBOX_FROM
    if not (sid and token and phones):
        raise RuntimeError("Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and WHATSAPP_PHONE in .env.")
    failures = []
    for phone in phones:
        try:
            _send_one(sid, token, sender, phone, text)
        except RuntimeError as exc:
            failures.append(f"+{phone[:5]}...{phone[-2:]}: {exc}")
    if failures:
        raise RuntimeError(f"{len(failures)} of {len(phones)} send(s) failed, will retry next run. " + " | ".join(failures))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WhatsApp alert for newly opened IPOs and debentures.")
    parser.add_argument("--test", action="store_true", help="send a test message and exit")
    parser.add_argument("--dry-run", action="store_true", help="print the message instead of sending it, and do not record it")
    args = parser.parse_args(argv)
    _load_env()

    try:
        if args.test:
            send_whatsapp("Share Gyan: WhatsApp notifications are working.")
            print("Test message sent.")
            return 0

        current = open_ipos()
        path = _state_path()
        seen = _read_seen(path)
        new = current[~current.apply(_key, axis=1).isin(seen)] if not current.empty else current
        if new.empty:
            print("No new open IPOs or debentures.")
            return 0
        message = build_message(new)
        if args.dry_run:
            print(message)
            return 0
        send_whatsapp(message)
        path.write_text(json.dumps(sorted(seen | set(new.apply(_key, axis=1)))))
        print(f"Notified about {len(new)} issue(s).")
        return 0
    except (RuntimeError, requests.RequestException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
