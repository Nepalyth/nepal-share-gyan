"""Read-only MeroShare client: the signed-in user's profile, portfolio and ASBA applications.

Credentials come from the environment (.env) or the sign-in form and are only sent to CDSC's MeroShare API.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from http.cookiejar import DefaultCookiePolicy
from pathlib import Path

import pandas as pd
import requests
from dotenv import find_dotenv, load_dotenv

API = "https://webbackend.cdsc.com.np/api/meroShare"
VIEW_API = "https://webbackend.cdsc.com.np/api/meroShareView"
ENV_VARS = ("MEROSHARE_DP", "MEROSHARE_USERNAME", "MEROSHARE_PASSWORD")
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://meroshare.cdsc.com.np",
    "Referer": "https://meroshare.cdsc.com.np/",
}
_TIMEOUT = (5, 20)


class MeroshareError(Exception):
    """A failure that is safe to show to the user (never contains credentials)."""


@dataclass(frozen=True)
class Credentials:
    dp: str
    username: str
    password: str = field(repr=False)


@dataclass
class Account:
    details: dict
    banks: pd.DataFrame
    portfolio: pd.DataFrame
    totals: dict
    applications: pd.DataFrame
    errors: dict[str, str] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)


def _load_env() -> None:
    load_dotenv(find_dotenv(usecwd=True))
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def missing_vars() -> list[str]:
    _load_env()
    return [v for v in ENV_VARS if not os.getenv(v, "").strip()]


def load_credentials() -> Credentials | None:
    if missing_vars():
        return None
    return Credentials(os.environ["MEROSHARE_DP"].strip(), os.environ["MEROSHARE_USERNAME"].strip(), os.environ["MEROSHARE_PASSWORD"])


def env_dp() -> str:
    _load_env()
    return os.getenv("MEROSHARE_DP", "").strip()


def mask(value: str, keep: int = 4) -> str:
    value = str(value or "")
    return f"{value[:keep]}{'•' * max(len(value) - 2 * keep, 0)}{value[-keep:]}" if len(value) > 2 * keep else value


def _fail(resp: requests.Response, action: str) -> MeroshareError:
    try:
        body = resp.json()
        detail = body.get("message") if isinstance(body, dict) else None
    except ValueError:
        detail = None
    return MeroshareError(f"{action} failed ({resp.status_code}){': ' + detail.rstrip('. ') if detail else ''}.")


def _json(resp: requests.Response, action: str):
    try:
        return resp.json()
    except ValueError:
        raise MeroshareError(f"{action} failed: MeroShare returned an unreadable response (it may be blocking automated requests).") from None


def _request(session: requests.Session, method: str, path: str, action: str, base: str = API, **kwargs):
    try:
        resp = session.request(method, f"{base}/{path}", timeout=_TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise MeroshareError(f"Could not reach MeroShare ({type(exc).__name__}).") from None
    if resp.status_code != 200:
        raise _fail(resp, action)
    return resp


def _new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(_HEADERS)
    # The API authenticates with a token header; MeroShare's firewall rejects replayed cookies.
    session.cookies.set_policy(DefaultCookiePolicy(allowed_domains=[]))
    return session


def depository_participants() -> list[dict]:
    """Public list of DPs: [{code, id, name}], sorted by name."""
    session = _new_session()
    capitals = _json(_request(session, "GET", "capital/", "Loading depository participants"), "Loading depository participants")
    return sorted(capitals, key=lambda c: c["name"])


def _resolve_dp(session: requests.Session, dp: str) -> dict:
    """Match the DP by its 5-digit code first, then by name."""
    capitals = _json(_request(session, "GET", "capital/", "Loading depository participants"), "Loading depository participants")
    wanted = dp.strip().upper()
    for c in capitals:
        if str(c["code"]) == wanted:
            return c
    hits = [c for c in capitals if c["name"].upper() == wanted] or [c for c in capitals if wanted in c["name"].upper()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise MeroshareError("The depository participant was not found. Use the 5-digit DP code or the exact name.")
    raise MeroshareError("That name matches several depository participants. Use the 5-digit DP code.")


def _login(creds: Credentials) -> tuple[requests.Session, dict]:
    session = _new_session()
    dp = _resolve_dp(session, creds.dp)
    resp = _request(session, "POST", "auth/", "Login", json={"clientId": int(dp["id"]), "username": creds.username, "password": creds.password})
    token = resp.headers.get("Authorization")
    if not token:
        raise MeroshareError("Login succeeded but MeroShare returned no session token.")
    session.headers["Authorization"] = token
    return session, dp


def _normalise(status: str) -> str:
    key = (status or "").strip().lower()
    if "not" in key and ("allot" in key or "alot" in key):
        return "Not allotted"
    if "allot" in key or "alot" in key:
        return "Allotted"
    return (status or "").strip() or "Pending"


def _first(d: dict, *keys, default=""):
    for k in keys:
        if d.get(k) not in (None, ""):
            return d[k]
    return default


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #


def _details(own: dict, dp: dict, username: str) -> dict:
    return {
        "Name": _first(own, "name"),
        "Username": _first(own, "username", default=username),
        "Depository participant": f'{dp["name"]} ({dp["code"]})',
        "BOID": str(_first(own, "demat", "boid")),
        "Client code": str(_first(own, "clientCode")),
        "Email": _first(own, "email"),
        "Contact": str(_first(own, "contact")),
        "Address": _first(own, "address"),
        "Gender": _first(own, "gender"),
        "Demat expiry": str(_first(own, "dematExpiryDate", "expiredDate"))[:10],
        "Renewed on": str(_first(own, "renewedDate"))[:10],
    }


def _banks(session: requests.Session) -> pd.DataFrame:
    rows = []
    for bank in _json(_request(session, "GET", "bank/", "Loading banks"), "Loading banks"):
        accounts = _json(_request(session, "GET", f"bank/{bank['id']}", "Loading bank accounts"), "Loading bank accounts")
        for acc in accounts if isinstance(accounts, list) else [accounts]:
            rows.append({"Bank": bank.get("name", ""), "Account number": str(acc.get("accountNumber", "")), "Branch": str(acc.get("branchName") or acc.get("branchId") or "")})
    return pd.DataFrame(rows, columns=["Bank", "Account number", "Branch"])


def _portfolio(session: requests.Session, own: dict) -> tuple[pd.DataFrame, dict]:
    body = {"sortBy": "script", "demat": [str(_first(own, "demat"))], "clientCode": str(_first(own, "clientCode")), "page": 1, "size": 200, "sortAsc": True}
    data = _json(_request(session, "POST", "myPortfolio/", "Loading your portfolio", base=VIEW_API, json=body), "Loading your portfolio")
    rows = []
    for item in data.get("meroShareMyPortfolio", []):
        balance = float(item.get("currentBalance") or 0)
        prev, last = float(item.get("previousClosingPrice") or 0), float(item.get("lastTransactionPrice") or 0)
        rows.append(
            {
                "Symbol": item.get("script", ""),
                "Company": item.get("scriptDesc", ""),
                "Balance": balance,
                "Prev close": prev,
                "LTP": last,
                "Value": float(item.get("valueOfLastTransPrice") or balance * last),
                "Prev value": float(item.get("valueOfPrevClosingPrice") or balance * prev),
            }
        )
    df = pd.DataFrame(rows, columns=["Symbol", "Company", "Balance", "Prev close", "LTP", "Value", "Prev value"])
    df["Change"] = df["Value"] - df["Prev value"]
    df["% Change"] = (df["Change"] / df["Prev value"].where(df["Prev value"] > 0) * 100).fillna(0).round(2)
    totals = {"value": float(df["Value"].sum()), "prev_value": float(df["Prev value"].sum()), "scrips": len(df)}
    totals["change"] = totals["value"] - totals["prev_value"]
    return df, totals


_SEARCH = {
    "filterFieldParams": [
        {"key": "companyShare.companyIssue.companyISIN.script", "alias": "Scrip"},
        {"key": "companyShare.companyIssue.companyISIN.company.name", "alias": "Company Name"},
    ],
    "page": 1,
    "size": 50,
    "searchRoleViewConstants": "VIEW_APPLICANT_FORM_COMPLETE",
    "filterDateParams": [
        {"key": "appliedDate", "condition": "", "alias": "", "value": ""},
        {"key": "appliedDate", "condition": "", "alias": "", "value": ""},
    ],
}


def _applications(session: requests.Session, limit: int) -> pd.DataFrame:
    forms = _json(_request(session, "POST", "applicantForm/active/search/", "Loading your ASBA applications", json=_SEARCH), "Loading your ASBA applications").get("object", [])[:limit]

    def detail(form: dict) -> dict:
        try:
            d = session.get(f"{API}/applicantForm/report/detail/{form['applicantFormId']}", timeout=_TIMEOUT)
            return d.json() if d.status_code == 200 else {}
        except (requests.RequestException, ValueError):
            return {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        details = list(pool.map(detail, forms))

    rows = []
    for form, d in zip(forms, details):
        rows.append(
            {
                "Symbol": form.get("scrip", ""),
                "Company": form.get("companyName", ""),
                "Type": form.get("shareTypeName") or form.get("shareGroupName") or "",
                "Applied": d.get("appliedKitta"),
                "Allotted": d.get("receivedKitta"),
                "Form status": form.get("statusName") or "",
                "Result": _normalise(d.get("statusName") or form.get("statusName") or ""),
                "Remark": d.get("meroshareRemark") or d.get("reasonOrRemark") or "",
            }
        )
    return pd.DataFrame(rows, columns=["Symbol", "Company", "Type", "Applied", "Allotted", "Form status", "Result", "Remark"])


def _section(errors: dict, name: str, fn: Callable, default):
    try:
        return fn()
    except MeroshareError as exc:
        errors[name] = str(exc)
        return default


def fetch_account(creds: Credentials, limit: int = 20) -> Account:
    """Sign in and read profile, banks, portfolio and ASBA applications. A failing section is reported, not fatal."""
    session, dp = _login(creds)
    errors: dict[str, str] = {}
    try:
        own = _json(_request(session, "GET", "ownDetail/", "Loading your profile"), "Loading your profile")
        banks = _section(errors, "banks", lambda: _banks(session), pd.DataFrame(columns=["Bank", "Account number", "Branch"]))
        portfolio, totals = _section(errors, "portfolio", lambda: _portfolio(session, own), (pd.DataFrame(), {}))
        applications = _section(errors, "applications", lambda: _applications(session, limit), pd.DataFrame())
    finally:
        session.close()
    return Account(_details(own, dp, creds.username), banks, portfolio, totals, applications, errors)
