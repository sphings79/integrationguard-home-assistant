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
        self.data = {}


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
    # Loaded, nothing of its own: not enough to claim either way.
    assert usage == Usage.UNDETERMINED


def test_the_runtime_monitor_also_leaves_them_out():
    from custom_components.integrationguard.runtime.monitor import RuntimeMonitor

    guard = monitor()
    guard.hass = FakeHass([FakeEntry("demo", source="ignore")], {"demo"})
    guard._domains = {"demo": "someone/demo"}
    guard._issues_by_domain = lambda: {}

    result = RuntimeMonitor._evaluate(guard, Settings())
    assert result == {}, "a domain with nothing but dismissals has nothing to judge"
    assert guard.hass.config_entries.asked_with == [False]


class FakeLoadedEntry(FakeEntry):
    """A config entry with a title, a state and a reason."""

    def __init__(self, title, state, reason=None):
        super().__init__("tuya_local")
        self.entry_id = title
        self.title = title
        self.state = state
        self.reason = reason
        self.error_reason_translation_key = None

    def async_get_active_flows(self, hass, sources):
        return iter(())


def _tuya(entries, guard=None, retrying_for=None):
    """Judge a made-up tuya-local installation.

    retrying_for maps entry titles to how long they have been retrying.
    """
    from homeassistant.util import dt as dt_util

    from custom_components.integrationguard.runtime.monitor import RuntimeMonitor

    guard = guard or monitor()
    guard.hass = FakeHass(entries, {"tuya_local"})
    guard._domains = {"tuya_local": "make-all/tuya-local"}
    guard._issues_by_domain = lambda: {}
    for title, age in (retrying_for or {}).items():
        started = dt_util.utcnow() - age
        guard._entry_since[title] = [RuntimeState.SETUP_RETRY, started.isoformat()]
    return RuntimeMonitor._evaluate(guard, Settings())["tuya_local"]


def _ok(title):
    from homeassistant.config_entries import ConfigEntryState

    return FakeLoadedEntry(title, ConfigEntryState.LOADED)


def _offline(title):
    from homeassistant.config_entries import ConfigEntryState

    return FakeLoadedEntry(title, ConfigEntryState.SETUP_RETRY, "device offline")


LONG = timedelta(hours=1)


def test_the_runtime_names_the_entry_that_is_actually_broken():
    """The title has to come from the same entry as the state and the reason.

    It used to be the first entry of the domain, so a working ceiling lamp was
    blamed for another tuya-local device being offline.
    """
    info = _tuya(
        [_ok("Ceiling lamp"), _offline("Garden socket"), _ok("Desk lamp")],
        retrying_for={"Garden socket": LONG},
    )
    assert info.state == RuntimeState.SETUP_RETRY
    assert info.problem is True
    assert info.title == "Garden socket"
    assert info.reason == "device offline"
    assert [entry["title"] for entry in info.affected] == ["Garden socket"]


def test_a_healthy_domain_keeps_the_first_title():
    info = _tuya([_ok("Ceiling lamp"), _ok("Desk lamp")])
    assert info.state == RuntimeState.OK
    assert info.problem is False
    assert info.title == "Ceiling lamp"
    assert info.affected == []


def test_every_retrying_entry_past_its_grace_is_affected():
    info = _tuya(
        [_offline("Garden socket"), _ok("Ceiling lamp"), _offline("Hall light")],
        retrying_for={"Garden socket": LONG, "Hall light": LONG},
    )
    assert [entry["title"] for entry in info.affected] == [
        "Garden socket",
        "Hall light",
    ]


def test_the_grace_period_counts_per_entry():
    """A device that only just dropped out waits, even if another is stuck."""
    info = _tuya(
        [_offline("Garden socket"), _offline("Hall light")],
        retrying_for={"Garden socket": LONG},
    )
    assert info.problem is True
    assert [entry["title"] for entry in info.affected] == ["Garden socket"]


def test_nothing_is_a_problem_while_every_entry_is_inside_its_grace():
    info = _tuya([_offline("Garden socket"), _ok("Ceiling lamp")])
    assert info.state == RuntimeState.SETUP_RETRY
    assert info.problem is False
    assert info.affected == []


def test_entry_clocks_survive_a_restart_and_forget_removed_entries():
    guard = monitor()
    _tuya(
        [_offline("Garden socket")],
        guard=guard,
        retrying_for={"Garden socket": LONG, "Gone": LONG},
    )
    assert "Gone" not in guard._entry_since

    restored = monitor()
    restored.restore(guard.to_state())
    info = _tuya([_offline("Garden socket")], guard=restored)
    assert info.problem is True


def test_only_a_growing_group_is_news():
    from custom_components.integrationguard.runtime.monitor import _is_news

    retry = RuntimeState.SETUP_RETRY
    assert _is_news(None, (retry, True, ("a",)))
    assert _is_news((retry, False, ()), (retry, True, ("a",)))
    assert _is_news((retry, True, ("a",)), (retry, True, ("a", "b")))
    assert not _is_news((retry, True, ("a", "b")), (retry, True, ("a",)))
    assert not _is_news((retry, True, ("a",)), (retry, True, ("a",)))
    # A new entry replacing a recovered one is news, too.
    assert _is_news((retry, True, ("a",)), (retry, True, ("b",)))
    # After an update from a version that did not remember the ids.
    assert not _is_news((retry, True, None), (retry, True, ("a", "b")))
    assert _is_news((retry, True, None), (RuntimeState.SETUP_ERROR, True, ("a",)))


def test_an_old_saved_state_still_restores():
    guard = monitor()
    guard.restore({"previous": {"tuya_local": [RuntimeState.SETUP_RETRY, True]}})
    assert guard._previous == {"tuya_local": (RuntimeState.SETUP_RETRY, True, None)}
    assert guard.to_state()["previous"] == {
        "tuya_local": [RuntimeState.SETUP_RETRY, True, None]
    }


def test_one_affected_entry_is_named_in_the_message():
    from custom_components.integrationguard.notify.messages import (
        build_runtime_message,
    )

    info = _tuya(
        [_ok("Ceiling lamp"), _offline("Garden socket")],
        retrying_for={"Garden socket": LONG},
    )
    message = build_runtime_message(info, "warning", "de")
    assert message.title == "IntegrationGuard: Garden socket"
    assert message.body == ("Garden socket versucht es immer wieder: device offline")


def test_several_affected_entries_become_one_message():
    from custom_components.integrationguard.notify.messages import (
        build_runtime_message,
    )

    info = _tuya(
        [_offline("Garden socket"), _ok("Ceiling lamp"), _offline("Hall light")],
        retrying_for={"Garden socket": LONG, "Hall light": LONG},
    )
    info.name = "Tuya Local"
    message = build_runtime_message(info, "warning", "de")
    assert message.title == "IntegrationGuard: Tuya Local"
    assert message.body == (
        "2 Einträge versuchen es immer wieder:\n"
        "Garden socket: device offline\n"
        "Hall light: device offline"
    )
    assert message.keys == ["tuya_local"]


def test_the_group_falls_back_to_the_domain_without_a_name():
    info = _tuya(
        [_offline("Garden socket"), _offline("Hall light")],
        retrying_for={"Garden socket": LONG, "Hall light": LONG},
    )
    assert info.name == "tuya_local"


def _judge(entries, components, domain, required=frozenset(), counts=(0, 0)):
    """Run the integration check against a made-up installation."""
    import pytest

    from custom_components.integrationguard.usage import integrations

    monkey = pytest.MonkeyPatch()
    monkey.setattr(
        integrations,
        "_counts",
        lambda *a: {"entities": counts[0], "devices": counts[1]},
    )
    try:
        return integrations.evaluate(
            FakeHass(entries, components), domain, set(required)
        )
    finally:
        monkey.undo()


def test_a_configured_integration_is_used_even_with_no_entities():
    """Switch Manager runs blueprints on events and owns nothing.

    Having been configured is the evidence. Owning no entity is not evidence
    of the opposite — plenty of integrations only register services or
    publish over MQTT.
    """
    usage, confidence, detail = _judge(
        [FakeEntry("switch_manager")], {"switch_manager"}, "switch_manager"
    )
    assert usage == Usage.USED
    assert confidence == "high"
    # Still reported, just not judged on.
    assert detail["entities"] == 0


def test_an_integration_switched_off_by_hand_is_unused():
    usage, confidence, _ = _judge(
        [FakeEntry("demo", disabled_by="user")], {"demo"}, "demo"
    )
    assert usage == Usage.UNUSED
    assert confidence == "medium"


def test_an_integration_that_was_never_set_up_is_unused():
    usage, confidence, _ = _judge([], set(), "demo")
    assert usage == Usage.UNUSED
    assert confidence == "high"


def test_a_yaml_integration_with_entities_is_used():
    usage, _, _ = _judge([], {"demo"}, "demo", counts=(3, 0))
    assert usage == Usage.USED


def test_a_backend_helper_another_integration_needs_is_not_unused():
    usage, _, detail = _judge([], {"demo"}, "demo", required={"demo"})
    assert usage == Usage.UNDETERMINED
    assert detail["required_by_another_integration"] is True


def test_not_loaded_waits_for_the_grace_period_too():
    """Right after a start, entries are not set up yet; that is not news."""
    from homeassistant.config_entries import ConfigEntryState

    info = _tuya([FakeLoadedEntry("Analytics", ConfigEntryState.NOT_LOADED)])
    assert info.state == RuntimeState.NOT_LOADED
    assert info.problem is False


def test_an_entry_being_reloaded_keeps_its_last_verdict():
    """A broken entry being set up again must not look fixed for a moment."""
    from homeassistant.config_entries import ConfigEntryState

    info = _tuya(
        [FakeLoadedEntry("Garden socket", ConfigEntryState.SETUP_IN_PROGRESS)],
        retrying_for={"Garden socket": LONG},
    )
    assert info.state == RuntimeState.SETUP_RETRY
    assert info.problem is True


def test_an_entry_set_up_for_the_first_time_is_fine():
    from homeassistant.config_entries import ConfigEntryState

    info = _tuya([FakeLoadedEntry("New lamp", ConfigEntryState.SETUP_IN_PROGRESS)])
    assert info.state == RuntimeState.OK


def test_nothing_is_judged_before_home_assistant_has_started():
    guard = monitor()
    changes = []
    guard._on_change = changes.append
    import asyncio

    asyncio.run(guard._async_refresh())
    assert changes == []
    assert guard.states == {}


def test_a_counted_entry_stays_counted_when_its_clock_restarts():
    """A longer grace period must not make a known problem look fixed."""
    guard = monitor()
    guard._previous = {
        "tuya_local": (RuntimeState.SETUP_RETRY, True, ("Garden socket",))
    }
    info = _tuya(
        [_offline("Garden socket"), _offline("Hall light")],
        guard=guard,
    )
    assert info.problem is True
    assert [entry["title"] for entry in info.affected] == ["Garden socket"]
