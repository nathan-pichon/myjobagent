"""Configuration schema for MyJobAgent (`jobhunt.config.json`).

This is the single source of truth shared between the static web configurator
and the local engine. The web SPA produces a JSON conforming to this schema;
the engine validates and runs it. No config is ever stored server-side.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

SCHEMA_VERSION = "1.0"


class Profile(BaseModel):
    roles: list[str] = Field(default_factory=list)
    stack_core: list[str] = Field(default_factory=list, description="Must-have technologies")
    stack_nice: list[str] = Field(default_factory=list, description="Nice-to-have technologies")
    exclusions: list[str] = Field(default_factory=list, description="Hard exclusions (e.g. 'PHP', 'Paris only')")
    geography: list[str] = Field(default_factory=list)
    contract_types: list[str] = Field(default_factory=list)
    seniority: str = "Senior"
    years_experience: int | None = None
    min_salary: int | None = None
    min_tjm: int | None = None

    def as_prompt_text(self) -> str:
        """Render a compact, LLM-friendly description of the target profile."""
        lines = [
            f"Roles: {', '.join(self.roles) or 'any'}",
            f"Seniority: {self.seniority}" + (f" ({self.years_experience}y xp)" if self.years_experience else ""),
            f"Must-have stack: {', '.join(self.stack_core) or 'any'}",
            f"Nice-to-have stack: {', '.join(self.stack_nice) or 'none'}",
            f"Geography: {', '.join(self.geography) or 'any'}",
            f"Contract types: {', '.join(self.contract_types) or 'any'}",
        ]
        if self.exclusions:
            lines.append(f"Hard exclusions: {', '.join(self.exclusions)}")
        if self.min_salary:
            lines.append(f"Min salary (CDI): {self.min_salary} EUR/year")
        if self.min_tjm:
            lines.append(f"Min TJM (freelance): {self.min_tjm} EUR/day")
        return "\n".join(lines)


class LLMConfig(BaseModel):
    provider: Literal["ollama", "openai", "anthropic", "lmstudio", "mistral", "groq"] = "ollama"
    # gemma4:e2b — light (~2 GB), passes the quality GATE (see eval/RESULTS.md).
    # For higher precision: gemma4:e4b, qwen2.5:7b, or a cloud API key.
    model: str = "gemma4:e2b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.3
    # API keys are NEVER embedded in the shared config / never entered on the web.
    # They are read locally from the OS keychain or the JOBHUNT_LLM_API_KEY env var.
    api_key_env: str = "JOBHUNT_LLM_API_KEY"


class SearchConfig(BaseModel):
    modes: list[Literal["PLATFORM", "CAREERS", "LINKEDIN"]] = ["PLATFORM", "CAREERS"]
    platforms: list[str] = Field(default_factory=list)
    max_steps: int = 200
    max_results_per_query: int = 25


class RssFeed(BaseModel):
    """A recruitment RSS/Atom feed. Robust, official, often ships full text."""
    name: str
    url: str
    enabled: bool = True


class SourcesConfig(BaseModel):
    """Source toggles. LinkedIn is OFF by default (ToS / scraping risk)."""
    france_travail_enabled: bool = True
    welcometothejungle_enabled: bool = True
    linkedin_enabled: bool = False  # opt-in only, with disclaimer in `doctor`
    indeed_enabled: bool = False
    rss_enabled: bool = True
    rss_feeds: list[RssFeed] = Field(default_factory=list)


class ScoringConfig(BaseModel):
    threshold: int = Field(default=50, ge=0, le=100)


class FiltersConfig(BaseModel):
    domain_blacklist: list[str] = Field(default_factory=list)
    reject_url_patterns: list[str] = Field(default_factory=list)
    fasttrack_job_patterns: list[str] = Field(default_factory=list)


class ScheduleConfig(BaseModel):
    """Automatic recurring hunts (managed by `mja watch` / the dashboard)."""
    enabled: bool = False
    every_hours: float = Field(default=6.0, ge=0.25, le=168.0)
    notify: bool = True


class JobHuntConfig(BaseModel):
    schema_version: str = SCHEMA_VERSION
    profile: Profile = Field(default_factory=Profile)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)


# --------------------------------------------------------------------------- #
# Loading / validation
# --------------------------------------------------------------------------- #

class ConfigError(Exception):
    pass


def load_config(path: str | Path) -> JobHuntConfig:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {p}: {e}") from e
    try:
        return JobHuntConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"Config does not match schema:\n{e}") from e


def load_config_b64(b64: str) -> JobHuntConfig:
    """Decode a base64url-inlined config (the `mja init --b64 ...` path)."""
    import base64

    try:
        payload = base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))
        raw = json.loads(payload.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise ConfigError(f"Invalid base64 config: {e}") from e
    return JobHuntConfig.model_validate(raw)


def _default_rss_feeds() -> list[RssFeed]:
    from jobhunt.sources.rss import default_feeds

    return [RssFeed(**f) for f in default_feeds()]


def default_config() -> JobHuntConfig:
    """The seed config (mirrors the original FLEXIBLE_CRITERIA, parameterised)."""
    return JobHuntConfig(
        profile=Profile(
            roles=[
                "Senior Backend Engineer",
                "Backend Architect",
                "Fractional CTO",
                "Tech Lead Backend",
                "Principal Engineer",
            ],
            stack_core=["Node.js", "TypeScript"],
            stack_nice=["MongoDB Atlas", "Docker", "Kubernetes"],
            geography=["Nice", "Cannes", "Sophia-Antipolis", "Remote", "Full Remote"],
            contract_types=["CDI", "Freelance", "Mission"],
            seniority="Senior",
        ),
        search=SearchConfig(
            platforms=[
                "welcometothejungle.com",
                "free-work.com",
                "malt.fr",
                "talent.io",
                "lesjeudis.com",
                "chooseyourboss.com",
                "turnover-it.com",
                "remixjobs.com",
            ],
        ),
        sources=SourcesConfig(rss_feeds=_default_rss_feeds()),
        filters=FiltersConfig(
            domain_blacklist=[
                "wikipedia.org", "reddit.com", "quora.com", "stackoverflow.com",
                "github.com", "medium.com", "youtube.com", "facebook.com",
                "twitter.com", "x.com", "pinterest.com", "tiktok.com",
                "instagram.com", "amazon.com", "ebay.com",
                "glassdoor.fr", "glassdoor.com", "payscale.com",
            ],
            reject_url_patterns=[
                "/profile/", "/profil/", "/freelances/", "/freelancer/",
                "/talents/", "/cv/", "/dir/", "/tags/", "/categories/",
                "/secteur/", "/metier/", "/blog/", "/article/", "/guide/",
                "/conseils/", "/news/", "/login", "/register", "/signup",
                "/connexion", "/inscription", "/barometre", "/tarifs",
                "/pricing", "/salaires", "/statistiques", "/about", "/contact",
                "/faq", "/a-propos", "/conditions", "/mentions-legales",
                "/cgu", "/cgv", "?page=", "&page=", "?q=", "&q=",
            ],
            fasttrack_job_patterns=[
                "/jobs/view/", "/freelance-missions/", "/offre/", "/offres/",
                "/job/", "/emploi/", "/mission/", "/annonce/", "/vacancy/",
                "/nos-offres/", "/position/", "/careers/", "/join-us/",
                "/nous-rejoindre/", "/recrutement/",
            ],
        ),
    )
