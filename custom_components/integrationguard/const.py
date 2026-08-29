"""Constants for the IntegrationGuard integration."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

DOMAIN: Final = "integrationguard"
PLATFORMS: Final = ["binary_sensor", "sensor", "switch"]

STORAGE_KEY_CONFIG: Final = f"{DOMAIN}.config"
STORAGE_VERSION_CONFIG: Final = 2
STORAGE_KEY_STATE: Final = f"{DOMAIN}.state"
STORAGE_VERSION_STATE: Final = 1

CONF_GITHUB_TOKEN: Final = "github_token"

SIGNAL_UPDATED: Final = f"{DOMAIN}_updated"

EVENT_SCAN_COMPLETED: Final = f"{DOMAIN}_scan_completed"
EVENT_STATUS_CHANGED: Final = f"{DOMAIN}_status_changed"
EVENT_RUNTIME_CHANGED: Final = f"{DOMAIN}_runtime_changed"

# The integration HACS itself registers under.
HACS_DOMAIN: Final = "hacs"
# Apps (formerly add-ons) live behind the Supervisor, which registers here.
HASSIO_DOMAIN: Final = "hassio"

# Public HACS data endpoints. They need no token and carry an ETag, so a
# repeated fetch of unchanged data is free.
HACS_DATA_BASE: Final = "https://data-v2.hacs.xyz"
HACS_REMOVED_URL: Final = f"{HACS_DATA_BASE}/removed/repositories.json"
HACS_CRITICAL_URL: Final = f"{HACS_DATA_BASE}/critical/repositories.json"

GITHUB_API: Final = "https://api.github.com"
# Requests kept in reserve so a scan never uses up the whole hourly budget.
GITHUB_RESERVE: Final = 5

DEFAULT_SCAN_INTERVAL_HOURS: Final = 24
DEFAULT_SCAN_TIME: Final = "04:00"
DEFAULT_HISTORY_RETENTION_DAYS: Final = 365
# Home Assistant is still settling right after a restart; HACS may not have
# finished loading its repositories yet.
STARTUP_DELAY_SECONDS: Final = 300

# A config entry that is retrying is normal for a while after a restart, so it
# only counts as a problem once it has been retrying for this long.
DEFAULT_RUNTIME_GRACE_MINUTES: Final = 15
# Bursts of config entry changes during startup are collapsed into one pass.
RUNTIME_DEBOUNCE_SECONDS: Final = 5
# Not everything announces itself: a reauth flow can be started later by the
# integration without any config entry change, and a repair message can be
# dismissed. A slow heartbeat catches what the live signals miss.
RUNTIME_HEARTBEAT_MINUTES: Final = 5


class Category(StrEnum):
    """What kind of thing is installed.

    The first six are HACS' own categories, named as HACS names them. Apps
    (formerly add-ons) do not come from HACS at all, but they are installed
    software with a source repository, so they are judged the same way.
    """

    INTEGRATION = "integration"
    PLUGIN = "plugin"
    THEME = "theme"
    TEMPLATE = "template"
    PYTHON_SCRIPT = "python_script"
    APPDAEMON = "appdaemon"
    APP = "app"


HACS_CATEGORIES: Final = (
    Category.INTEGRATION,
    Category.PLUGIN,
    Category.THEME,
    Category.TEMPLATE,
    Category.PYTHON_SCRIPT,
    Category.APPDAEMON,
)


ALL_CATEGORIES: Final = tuple(Category)


class Status(StrEnum):
    """Overall verdict for one repository."""

    HEALTHY = "healthy"
    INFO = "info"
    STALE = "stale"
    ABANDONED = "abandoned"
    CRITICAL = "critical"


# Order from harmless to worst, used to compare two verdicts.
STATUS_ORDER: Final = (
    Status.HEALTHY,
    Status.INFO,
    Status.STALE,
    Status.ABANDONED,
    Status.CRITICAL,
)


class Usage(StrEnum):
    """Whether an installed repository is actually being used."""

    USED = "used"
    UNUSED = "unused"
    UNDETERMINED = "undetermined"
    NOT_REGISTERED = "not_registered"
    NOT_CHECKED = "not_checked"


class Confidence(StrEnum):
    """How much the usage verdict can be trusted."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RuleId(StrEnum):
    """Identifiers of the health rules. The set is fixed.

    Rules that come in two grades are two separate entries, so every rule has
    exactly one threshold, one severity and one penalty. The harsher one
    supersedes the milder one; see health/rules.py.
    """

    PUSH_AGE = "push_age"
    PUSH_AGE_SEVERE = "push_age_severe"
    RELEASE_AGE = "release_age"
    RELEASE_AGE_SEVERE = "release_age_severe"
    ARCHIVED = "archived"
    GONE = "gone"
    REMOVED = "removed"
    CRITICAL_LIST = "critical_list"
    NO_RELEASE = "no_release"
    PRERELEASE_ONLY = "prerelease_only"
    MANY_ISSUES = "many_issues"
    FEW_STARS = "few_stars"
    HA_VERSION = "ha_version"
    OUTDATED = "outdated"
    UNPINNED = "unpinned"
    UNUSED = "unused"
    # Apps only.
    APP_DETACHED = "app_detached"
    APP_DEPRECATED = "app_deprecated"
    APP_UNAVAILABLE = "app_unavailable"


class ThresholdUnit(StrEnum):
    """What a rule's threshold counts."""

    DAYS = "days"
    COUNT = "count"


class SeverityId(StrEnum):
    """Identifiers of the four severities seeded on first start."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SECURITY = "security"


class PanelAccess(StrEnum):
    """Who may open the panel."""

    ADMINS = "admins"
    ALL = "all"


# Severity priorities decide the status of a repository. Users may rename,
# recolour and add severities, so the mapping goes through the priority number
# rather than through the identifier.
def status_for_priority(priority: int) -> Status:
    """Return the status a finding of this priority leads to."""
    if priority >= 90:
        return Status.CRITICAL
    if priority >= 80:
        return Status.ABANDONED
    if priority >= 50:
        return Status.STALE
    return Status.INFO


class RuntimeState(StrEnum):
    """How an installed integration is doing on this installation."""

    OK = "ok"
    SETUP_ERROR = "setup_error"
    SETUP_RETRY = "setup_retry"
    REAUTH = "reauth"
    MIGRATION_ERROR = "migration_error"
    FAILED_UNLOAD = "failed_unload"
    NOT_LOADED = "not_loaded"
    DISABLED = "disabled"
    # No config entry exists, so there is nothing to say about the runtime.
    # Whether the integration is used at all is the usage engine's question.
    NOT_APPLICABLE = "not_applicable"


# From harmless to worst. An integration with several config entries takes the
# worst state of them all.
RUNTIME_ORDER: Final = (
    RuntimeState.NOT_APPLICABLE,
    RuntimeState.OK,
    RuntimeState.DISABLED,
    RuntimeState.NOT_LOADED,
    RuntimeState.FAILED_UNLOAD,
    RuntimeState.SETUP_RETRY,
    RuntimeState.REAUTH,
    RuntimeState.SETUP_ERROR,
    RuntimeState.MIGRATION_ERROR,
)

# States that are worth telling the user about. "disabled" is the user's own
# decision and only shown, never announced.
RUNTIME_PROBLEM_STATES: Final = frozenset(
    {
        RuntimeState.SETUP_ERROR,
        RuntimeState.MIGRATION_ERROR,
        RuntimeState.REAUTH,
        RuntimeState.SETUP_RETRY,
        RuntimeState.FAILED_UNLOAD,
        RuntimeState.NOT_LOADED,
    }
)

# These resolve themselves or they do not; there is no point in waiting.
RUNTIME_IMMEDIATE_STATES: Final = frozenset(
    {RuntimeState.SETUP_ERROR, RuntimeState.MIGRATION_ERROR}
)

RUNTIME_SEVERITY: Final[dict[str, str]] = {
    RuntimeState.SETUP_ERROR: SeverityId.CRITICAL,
    RuntimeState.MIGRATION_ERROR: SeverityId.CRITICAL,
    RuntimeState.REAUTH: SeverityId.WARNING,
    RuntimeState.SETUP_RETRY: SeverityId.WARNING,
    RuntimeState.FAILED_UNLOAD: SeverityId.INFO,
    RuntimeState.NOT_LOADED: SeverityId.INFO,
}

# Home Assistant's own repair severities, mapped onto ours. "error" is by far
# the most common one, so it becomes a warning rather than a critical alert.
REPAIR_SEVERITY: Final[dict[str, str]] = {
    "critical": SeverityId.CRITICAL,
    "error": SeverityId.WARNING,
    "warning": SeverityId.INFO,
}


class AppState(StrEnum):
    """What the Supervisor reports about a running app."""

    STARTUP = "startup"
    STARTED = "started"
    STOPPED = "stopped"
    UNKNOWN = "unknown"
    ERROR = "error"


class AppStage(StrEnum):
    """How finished an app is, as its author declared it."""

    STABLE = "stable"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"
