"""France Travail (ex-Pôle Emploi) — Offres d'emploi API v2.

Official, legal, structured source. Returns the offer description inline, so
NO scraping is needed for these offers — both more reliable and lighter than
DuckDuckGo + Playwright.

Auth: OAuth2 client_credentials. Credentials are SECRETS read locally from env
vars (never on the web, same policy as LLM keys):
  FRANCE_TRAVAIL_CLIENT_ID
  FRANCE_TRAVAIL_CLIENT_SECRET
Get them by registering an app on francetravail.io and subscribing to the
"Offres d'emploi v2" API.

Docs: https://francetravail.io/data/api/offres-emploi
"""
from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Iterator

import requests

from jobhunt.sources.base import Offer

if TYPE_CHECKING:
    from jobhunt.config import JobHuntConfig

_AUTH_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
_API_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
_SCOPE = "api_offresdemploiv2 o2dsoffre"


class FranceTravailSource:
    name = "france-travail"

    def __init__(self) -> None:
        self._token = ""
        self._token_exp = 0.0

    # --- auth ------------------------------------------------------------- #
    def _credentials(self) -> tuple[str, str]:
        from jobhunt.secrets import get_secret

        return (
            get_secret("FRANCE_TRAVAIL_CLIENT_ID"),
            get_secret("FRANCE_TRAVAIL_CLIENT_SECRET"),
        )

    def available(self, cfg: "JobHuntConfig") -> tuple[bool, str]:
        cid, secret = self._credentials()
        if not cid or not secret:
            return False, (
                "France Travail: set FRANCE_TRAVAIL_CLIENT_ID / _SECRET locally "
                "(register on francetravail.io). Disabled until then."
            )
        return True, "France Travail API configured"

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_exp - 30:
            return self._token
        cid, secret = self._credentials()
        resp = requests.post(
            _AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": cid,
                "client_secret": secret,
                "scope": _SCOPE,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_exp = time.time() + int(data.get("expires_in", 1500))
        return self._token

    # --- fetch ------------------------------------------------------------ #
    def fetch(self, cfg: "JobHuntConfig", query: str, limit: int) -> Iterator[Offer]:
        try:
            token = self._get_token()
        except requests.RequestException as e:
            raise RuntimeError(f"France Travail auth failed: {e}") from e

        params = {
            "motsCles": _keywords(query),
            "range": f"0-{max(0, min(limit, 150) - 1)}",
        }
        try:
            resp = requests.get(
                _API_URL,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=20,
            )
            # 204 = no results; 206 = partial content (normal for ranges)
            if resp.status_code == 204:
                return
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"France Travail search failed: {e}") from e

        for o in resp.json().get("resultats", []):
            yield _to_offer(o)


def _keywords(query: str) -> str:
    """France Travail wants plain keywords, not `site:` search operators."""
    q = query
    if "site:" in q:
        # strip the operator and its domain token
        parts = [p for p in q.split() if not p.startswith("site:")]
        q = " ".join(parts)
    return q.strip()[:200]


def _to_offer(o: dict) -> Offer:
    lieu = (o.get("lieuTravail") or {}).get("libelle", "")
    entreprise = (o.get("entreprise") or {}).get("nom", "") or "Inconnue"
    contrat = o.get("typeContratLibelle") or o.get("typeContrat") or ""
    desc = o.get("description", "") or ""
    oid = o.get("id", "")
    url = o.get("origineOffre", {}).get("urlOrigine") or (
        f"https://candidat.francetravail.fr/offres/recherche/detail/{oid}" if oid else ""
    )
    return Offer(
        url=url,
        title=o.get("intitule", ""),
        company=entreprise,
        location=lieu,
        contract=contrat,
        text=desc,
        source="france-travail",
        posted_at=o.get("dateCreation", ""),
        extra={"id": oid},
    )
