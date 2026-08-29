"""The grace period and the worst-state logic of the runtime monitor.

Everything tested here works on the monitor's own bookkeeping, so it needs no
Home Assistant instance.
"""

from __future__ import annotations

from datetime import timedelta

from custom_components.integrationguard.const import RuntimeState, Usage
from custom_components.integrationguard.models import RepairIssue, RuntimeInfo, Settings
from custom_components.integrationguard.runtime.monitor import RuntimeMonitor, _worse

from .conftest import NOW

GRACE = timedelta(minutes=15)


def monitor() -> RuntimeMonitor:
    """Return a monitor that is never started, so it touches no hass."""
    return RuntimeMonitor(None, Settings, lambda: None)


def test_worse_picks_the_worse_state():
    assert _worse(RuntimeState.OK, RuntimeState.SETUP_RETRY) == RuntimeState.SETUP_RETRY
    assert (
        _worse(RuntimeState.SETUP_ERROR, RuntimeState.SETUP_RETRY)
        == RuntimeState.SETUP_ERROR
    )
    assert _worse(RuntimeState.OK, RuntimeState.OK) == RuntimeState.OK
    assert _worse(RuntimeState.NOT_APPLICABLE, RuntimeState.OK) == RuntimeState.OK


def test_healthy_integration_is_no_problem():
    info = RuntimeInfo(domain="demo", state=RuntimeState.OK)
    monitor()._finalise(info, NOW, GRACE)
    assert info.problem is False
    assert info.since == NOW.isoformat()


def test_setup_error_reports_at_once():
    info = RuntimeInfo(domain="demo", state=RuntimeState.SETUP_ERROR)
    monitor()._finalise(info, NOW, GRACE)
    assert info.problem is True


def test_retry_stays_quiet_inside_the_grace_period():
    """A restart puts entries into retry for a while; that is not news."""
    guard = monitor()
    info = RuntimeInfo(domain="demo", state=RuntimeState.SETUP_RETRY)
    guard._finalise(info, NOW, GRACE)
    assert info.problem is False

    later = RuntimeInfo(domain="demo", state=RuntimeState.SETUP_RETRY)
    guard._finalise(later, NOW + timedelta(minutes=14), GRACE)
    assert later.problem is False
    assert later.since == NOW.isoformat()


def test_retry_reports_once_the_grace_period_is_over():
    guard = monitor()
    guard._finalise(
        RuntimeInfo(domain="demo", state=RuntimeState.SETUP_RETRY), NOW, GRACE
    )
    info = RuntimeInfo(domain="demo", state=RuntimeState.SETUP_RETRY)
    guard._finalise(info, NOW + timedelta(minutes=15), GRACE)
    assert info.problem is True


def test_recovering_resets_the_clock():
    guard = monitor()
    guard._finalise(
        RuntimeInfo(domain="demo", state=RuntimeState.SETUP_RETRY), NOW, GRACE
    )
    guard._finalise(
        RuntimeInfo(domain="demo", state=RuntimeState.OK),
        NOW + timedelta(minutes=5),
        GRACE,
    )
    info = RuntimeInfo(domain="demo", state=RuntimeState.SETUP_RETRY)
    guard._finalise(info, NOW + timedelta(minutes=6), GRACE)
    assert info.problem is False
    assert info.since == (NOW + timedelta(minutes=6)).isoformat()


def test_reauth_reports_at_once():
    info = RuntimeInfo(domain="demo", state=RuntimeState.REAUTH)
    monitor()._finalise(info, NOW, GRACE)
    assert info.problem is True


def test_disabled_is_shown_but_not_reported():
    info = RuntimeInfo(domain="demo", state=RuntimeState.DISABLED)
    monitor()._finalise(info, NOW, GRACE)
    assert info.problem is False


def test_a_repair_message_alone_is_a_problem():
    info = RuntimeInfo(
        domain="demo",
        state=RuntimeState.OK,
        repairs=[RepairIssue(domain="demo", issue_id="broken")],
    )
    monitor()._finalise(info, NOW, GRACE)
    assert info.problem is True


def test_state_survives_a_restart():
    guard = monitor()
    guard._finalise(
        RuntimeInfo(domain="demo", state=RuntimeState.SETUP_RETRY), NOW, GRACE
    )
    restored = monitor()
    restored.restore(guard.to_state())

    info = RuntimeInfo(domain="demo", state=RuntimeState.SETUP_RETRY)
    restored._finalise(info, NOW + timedelta(minutes=16), GRACE)
    assert info.problem is True


def test_links_are_built_from_the_repository():
    info = RuntimeInfo(domain="demo", full_name="someone/demo")
    assert info.url == "https://github.com/someone/demo"
    assert info.configuration_url == "/config/integrations/integration/demo"
    assert RuntimeInfo(domain="core_thing").url is None


class FakeEntries:
    """A config entry registry that honours include_ignore, like the real one."""

    def __init__(self, entries):
        self.entries = entries
        self.asked_with = []

    def async_entries(self, domain=None, include_ignore=True, include_disabled=True):
        self.asked_with.append(include_ignore)
        return [
            entry
            for entry in self.entries
            if (domain is None or entry.domain == domain)
            and (include_ignore or entry.source != "ignore")
        ]


class FakeEntry:
    """Just enough of a config entry for the checks that look at one."""

    def __init__(self, domain, source="user", disabled_by=None):
        self.domain = domain
        self.source = source
        self.disabled_by = disabled_by
        self.entry_id = f"{domain}-{source}"


class FakeHass:
    def __init__(self, entries, components):
        self.config_entries = FakeEntries(entries)
        self.config = type("C", (), {"components": components})()


def test_ignored_discoveries_do_not_count_as_configuration(monkeypatch):
    """A dismissed discovery is not configuration.

    Home Assistant never sets those entries up, so they sit at "not loaded"
    forever. Counting them made powercalc look broken on a real installation:
    79 of its 108 entries were dismissed discoveries.
    """
    from custom_components.integrationguard.usage import integrations

    monkeypatch.setattr(
        integrations, "_counts", lambda *a: {"entities": 0, "devices": 0}
    )

    hass = FakeHass(
        [FakeEntry("powercalc", source="ignore") for _ in range(79)]
        + [FakeEntry("demo", source="ignore")],
        {"powercalc", "demo"},
    )
    # powercalc also has real entries; demo has nothing but dismissals.
    hass.config_entries.entries += [FakeEntry("powercalc") for _ in range(29)]

    _usage, _conf, detail = integrations.evaluate(hass, "powercalc", set())
    assert detail["entries"] == 29
    assert hass.config_entries.asked_with == [False]

    usage, _confidence, detail = integrations.evaluate(hass, "demo", set())
    assert detail["entries"] == 0
    assert usage == Usage.UNUSED


def test_the_runtime_monitor_also_leaves_them_out():
    from custom_components.integrationguard.runtime.monitor import RuntimeMonitor

    guard = monitor()
    guard.hass = FakeHass([FakeEntry("demo", source="ignore")], {"demo"})
    guard._domains = {"demo": "someone/demo"}
    guard._issues_by_domain = lambda: {}

    result = RuntimeMonitor._evaluate(guard, Settings())
    assert result == {}, "a domain with nothing but dismissals has nothing to judge"
    assert guard.hass.config_entries.asked_with == [False]
