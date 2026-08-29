"""Data model for IntegrationGuard configuration and scan results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any
from uuid import uuid4

from .const import (
    ALL_CATEGORIES,
    DEFAULT_HISTORY_RETENTION_DAYS,
    DEFAULT_RUNTIME_GRACE_MINUTES,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DEFAULT_SCAN_TIME,
    Category,
    PanelAccess,
    RuntimeState,
    SeverityId,
    Status,
    Usage,
)


def new_id() -> str:
    """Return a short identifier for a newly created object."""
    return uuid4().hex[:12]


def _known_only(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    """Drop keys the dataclass does not know, so older stores still load."""
    known = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in known}


@dataclass(slots=True)
class Severity:
    """A named severity level. Its priority decides the resulting status."""

    id: str = SeverityId.WARNING
    name: str = "Warning"
    priority: int = 50
    color: str = "amber"
    icon: str = "mdi:alert-outline"
    channels: list[str] = field(default_factory=list)
    ignore_quiet_hours: bool = False
    persistent_notification: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Severity:
        """Build a severity from stored data, tolerating missing keys."""
        return cls(**_known_only(cls, data))

    def to_dict(self) -> dict[str, Any]:
        """Return the severity as plain data."""
        return asdict(self)


@dataclass(slots=True)
class Rule:
    """User-adjustable settings of one health rule.

    The rule catalogue itself is fixed; only these four values change.
    """

    id: str = ""
    enabled: bool = True
    severity_id: str = SeverityId.WARNING
    penalty: int = 10
    threshold: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        """Build a rule from stored data, tolerating missing keys."""
        return cls(**_known_only(cls, data))

    def to_dict(self) -> dict[str, Any]:
        """Return the rule as plain data."""
        return asdict(self)


@dataclass(slots=True)
class Channel:
    """A notification destination.

    ``kind`` selects the handler, ``config`` holds whatever that handler needs.
    The templates are Jinja2 and may be empty, in which case the built-in text
    for the interface language is used.
    """

    id: str = field(default_factory=new_id)
    name: str = ""
    kind: str = "ha_service"
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)
    title_template: str = ""
    template: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Channel:
        """Build a channel from stored data, tolerating missing keys."""
        return cls(**_known_only(cls, data))

    def to_dict(self) -> dict[str, Any]:
        """Return the channel as plain data."""
        return asdict(self)


@dataclass(slots=True)
class QuietHours:
    """A window in which notifications are held back."""

    enabled: bool = False
    start: str = "22:00"
    end: str = "07:00"
    # Weekdays the window applies to, Monday is 0. Empty means every day.
    weekdays: list[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuietHours:
        """Build the quiet hours from stored data."""
        quiet = cls(**_known_only(cls, data))
        quiet.weekdays = [int(day) for day in quiet.weekdays]
        return quiet

    def to_dict(self) -> dict[str, Any]:
        """Return the quiet hours as plain data."""
        return asdict(self)


@dataclass(slots=True)
class Ignore:
    """Something the user asked not to be bothered about.

    Keyed the same way everything else is: ``owner/repo`` for a HACS
    repository, ``app:<slug>`` for an app.
    """

    key: str = ""
    until: str | None = None
    reason: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ignore:
        """Build an ignore entry from stored data."""
        return cls(**_known_only(cls, data))

    def to_dict(self) -> dict[str, Any]:
        """Return the ignore entry as plain data."""
        return asdict(self)


@dataclass(slots=True)
class Settings:
    """Global settings, all editable in the panel."""

    monitoring_enabled: bool = True
    scan_interval_hours: int = DEFAULT_SCAN_INTERVAL_HOURS
    scan_time: str = DEFAULT_SCAN_TIME
    categories_health: list[str] = field(
        default_factory=lambda: [str(c) for c in ALL_CATEGORIES]
    )
    categories_usage: list[str] = field(
        default_factory=lambda: [
            Category.INTEGRATION,
            Category.PLUGIN,
            Category.THEME,
            Category.TEMPLATE,
            Category.PYTHON_SCRIPT,
            Category.APP,
        ]
    )
    check_orphans: bool = True
    notify_on_recovery: bool = True
    runtime_enabled: bool = True
    # Off: only integrations that came from HACS. On: every integration.
    runtime_include_all: bool = False
    runtime_grace_minutes: int = DEFAULT_RUNTIME_GRACE_MINUTES
    quiet_hours: QuietHours = field(default_factory=QuietHours)
    history_retention_days: int = DEFAULT_HISTORY_RETENTION_DAYS
    panel_access: str = PanelAccess.ADMINS
    ui_language: str = "auto"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        """Build the settings from stored data, tolerating missing keys."""
        known = _known_only(cls, data)
        quiet = known.pop("quiet_hours", None)
        settings = cls(**known)
        if isinstance(quiet, dict):
            settings.quiet_hours = QuietHours.from_dict(quiet)
        settings.categories_health = [str(c) for c in settings.categories_health]
        settings.categories_usage = [str(c) for c in settings.categories_usage]
        return settings

    def to_dict(self) -> dict[str, Any]:
        """Return the settings as plain data."""
        return asdict(self)


@dataclass(slots=True)
class Config:
    """Everything IntegrationGuard persists as configuration."""

    settings: Settings = field(default_factory=Settings)
    severities: list[Severity] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    channels: list[Channel] = field(default_factory=list)
    ignored: list[Ignore] = field(default_factory=list)
    marked_used: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Rebuild the configuration from stored data."""
        return cls(
            settings=Settings.from_dict(data.get("settings") or {}),
            severities=[Severity.from_dict(s) for s in data.get("severities") or []],
            rules=[Rule.from_dict(r) for r in data.get("rules") or []],
            channels=[Channel.from_dict(c) for c in data.get("channels") or []],
            ignored=[Ignore.from_dict(i) for i in data.get("ignored") or []],
            marked_used=list(data.get("marked_used") or []),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the configuration as plain data."""
        return {
            "settings": self.settings.to_dict(),
            "severities": [s.to_dict() for s in self.severities],
            "rules": [r.to_dict() for r in self.rules],
            "channels": [c.to_dict() for c in self.channels],
            "ignored": [i.to_dict() for i in self.ignored],
            "marked_used": list(self.marked_used),
        }

    def severity(self, severity_id: str) -> Severity | None:
        """Return a severity by id."""
        return next((s for s in self.severities if s.id == severity_id), None)

    def rule(self, rule_id: str) -> Rule | None:
        """Return a rule by id."""
        return next((r for r in self.rules if r.id == rule_id), None)

    def channel(self, channel_id: str) -> Channel | None:
        """Return a channel by id."""
        return next((c for c in self.channels if c.id == channel_id), None)

    def ignore(self, key: str) -> Ignore | None:
        """Return the ignore entry for a repository, if there is one."""
        return next((i for i in self.ignored if i.key == key), None)


@dataclass(slots=True)
class Finding:
    """One rule that fired for one repository.

    ``params`` carries values, never finished sentences: the panel and the
    notifications translate them themselves.
    """

    rule_id: str
    severity_id: str
    penalty: int
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the finding as plain data."""
        return asdict(self)


@dataclass(slots=True)
class RepairIssue:
    """One entry from Home Assistant's repair registry."""

    domain: str
    issue_id: str
    severity: str | None = None
    is_fixable: bool | None = None
    translation_key: str | None = None
    learn_more_url: str | None = None
    breaks_in_ha_version: str | None = None
    created: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the issue as plain data."""
        return asdict(self)


@dataclass(slots=True)
class RuntimeInfo:
    """How one integration is doing on this installation."""

    domain: str
    state: str = RuntimeState.NOT_APPLICABLE
    # False while a retrying entry is still inside its grace period.
    problem: bool = False
    title: str = ""
    # The repository the integration came from, empty for core integrations.
    full_name: str = ""
    reason: str = ""
    translation_key: str | None = None
    since: str | None = None
    entries: list[dict[str, Any]] = field(default_factory=list)
    repairs: list[RepairIssue] = field(default_factory=list)

    @property
    def url(self) -> str | None:
        """Return the GitHub page, empty for core integrations."""
        return f"https://github.com/{self.full_name}" if self.full_name else None

    @property
    def configuration_url(self) -> str:
        """Return the Home Assistant page that shows this integration."""
        return f"/config/integrations/integration/{self.domain}"

    def to_dict(self) -> dict[str, Any]:
        """Return the runtime picture as plain data."""
        return {
            "domain": self.domain,
            "url": self.url,
            "configuration_url": self.configuration_url,
            "state": self.state,
            "problem": self.problem,
            "title": self.title,
            "full_name": self.full_name,
            "reason": self.reason,
            "translation_key": self.translation_key,
            "since": self.since,
            "entries": self.entries,
            "repairs": [issue.to_dict() for issue in self.repairs],
        }


@dataclass(slots=True)
class RepositoryInfo:
    """The facts about one installed repository, before any judgement."""

    full_name: str
    category: str
    name: str = ""
    description: str = ""
    domain: str | None = None
    topics: list[str] = field(default_factory=list)
    hacs_id: str = ""
    is_default_store: bool = True
    # Apps only: the Supervisor slug, the store repository and its own state.
    slug: str = ""
    app_state: str | None = None
    app_stage: str | None = None
    app_boot: str | None = None
    app_repository: str = ""
    detached: bool | None = None
    available: bool | None = None
    # Single file categories (template, python_script) install exactly one
    # file; HACS remembers its name.
    file_name: str = ""

    installed_version: str = ""
    available_version: str = ""
    selected_tag: str | None = None
    default_branch: str | None = None
    installed_commit: str | None = None
    last_commit: str | None = None
    pending_update: bool = False
    has_releases: bool = False
    last_version: str | None = None
    prerelease: str | None = None

    last_push: datetime | None = None
    last_release_at: datetime | None = None
    stars: int | None = None
    open_issues: int | None = None
    downloads: int | None = None
    archived: bool | None = None
    gone: bool | None = None
    has_issues: bool | None = None
    min_ha_version: str | None = None

    removed_from_hacs: bool = False
    critical: bool = False
    # Which source last supplied data, as ISO timestamps.
    data_sources: dict[str, str] = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Return the identifier everything else keys on.

        Several apps can share one store repository, so the repository name is
        not unique for them; their slug is.
        """
        return f"app:{self.slug}" if self.slug else self.full_name

    @property
    def owner(self) -> str:
        """Return the GitHub account the repository belongs to."""
        return self.full_name.split("/")[0]

    @property
    def url(self) -> str:
        """Return the repository page on GitHub, empty when there is none."""
        return f"https://github.com/{self.full_name}" if self.full_name else ""

    @property
    def issues_url(self) -> str:
        """Return the issue list on GitHub."""
        return f"{self.url}/issues"

    @property
    def releases_url(self) -> str:
        """Return the release list on GitHub."""
        return f"{self.url}/releases"

    @property
    def hacs_url(self) -> str | None:
        """Return the page inside Home Assistant this thing is managed on."""
        if self.slug:
            return f"/hassio/addon/{self.slug}/info"
        return f"/hacs/repository/{self.hacs_id}" if self.hacs_id else None


@dataclass(slots=True)
class RepositoryHealth:
    """The verdict for one repository."""

    info: RepositoryInfo
    findings: list[Finding] = field(default_factory=list)
    score: int = 100
    status: str = Status.HEALTHY
    usage: str = Usage.NOT_CHECKED
    usage_confidence: str | None = None
    usage_detail: dict[str, Any] = field(default_factory=dict)
    ignored: bool = False

    @property
    def full_name(self) -> str:
        """Return the repository the verdict belongs to."""
        return self.info.full_name

    @property
    def key(self) -> str:
        """Return the identifier everything else keys on."""
        return self.info.key

    def to_dict(self) -> dict[str, Any]:
        """Return the verdict as plain data for the panel and the sensors."""
        info = self.info
        return {
            "key": info.key,
            "full_name": info.full_name,
            "slug": info.slug,
            "name": info.name,
            "url": info.url,
            "issues_url": info.issues_url,
            "releases_url": info.releases_url,
            "hacs_url": info.hacs_url,
            "category": info.category,
            "domain": info.domain,
            "description": info.description,
            "installed_version": info.installed_version,
            "available_version": info.available_version,
            "pending_update": info.pending_update,
            "is_default_store": info.is_default_store,
            "last_push": info.last_push.isoformat() if info.last_push else None,
            "last_release_at": (
                info.last_release_at.isoformat() if info.last_release_at else None
            ),
            "stars": info.stars,
            "open_issues": info.open_issues,
            "archived": info.archived,
            "gone": info.gone,
            "removed_from_hacs": info.removed_from_hacs,
            "critical": info.critical,
            "min_ha_version": info.min_ha_version,
            "app_state": info.app_state,
            "app_stage": info.app_stage,
            "app_boot": info.app_boot,
            "app_repository": info.app_repository,
            "detached": info.detached,
            "available": info.available,
            "data_sources": info.data_sources,
            "score": self.score,
            "status": self.status,
            "usage": self.usage,
            "usage_confidence": self.usage_confidence,
            "usage_detail": self.usage_detail,
            "ignored": self.ignored,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass(slots=True)
class ScanResult:
    """Everything one scan produced."""

    started: datetime
    finished: datetime
    repositories: list[RepositoryHealth] = field(default_factory=list)
    orphans: list[dict[str, Any]] = field(default_factory=list)
    # Populated when a source could not be reached, so the panel can say so
    # instead of showing a silently incomplete picture.
    source_errors: dict[str, str] = field(default_factory=dict)
    github_remaining: int | None = None
    github_pending: int = 0

    @property
    def duration(self) -> float:
        """Return how long the scan took, in seconds."""
        return (self.finished - self.started).total_seconds()

    def by_status(self, status: str) -> list[RepositoryHealth]:
        """Return the repositories with a given status, ignored ones aside."""
        return [r for r in self.repositories if not r.ignored and r.status == status]

    def problems(self) -> list[RepositoryHealth]:
        """Return every repository that is not healthy, ignored ones aside."""
        return [
            r for r in self.repositories if not r.ignored and r.status != Status.HEALTHY
        ]

    def unused(self) -> list[RepositoryHealth]:
        """Return the repositories found to be unused."""
        return [
            r for r in self.repositories if not r.ignored and r.usage == Usage.UNUSED
        ]


__all__ = [
    "Channel",
    "Config",
    "Finding",
    "Ignore",
    "QuietHours",
    "RepairIssue",
    "RepositoryHealth",
    "RepositoryInfo",
    "Rule",
    "RuntimeInfo",
    "ScanResult",
    "Settings",
    "Severity",
]
