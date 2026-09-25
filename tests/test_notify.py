"""One Home Assistant notification per problem, removed once it is fixed."""

from __future__ import annotations

from dataclasses import replace

import pytest

from custom_components.integrationguard.const import RuntimeState, Status
from custom_components.integrationguard.models import (
    Finding,
    RepositoryHealth,
    RuntimeInfo,
)
from custom_components.integrationguard.notify import dispatcher as dispatcher_module
from custom_components.integrationguard.notify.dispatcher import Dispatcher
from custom_components.integrationguard.notify.messages import (
    Change,
    build_problem_messages,
    build_runtime_message,
    build_runtime_recovery_message,
    repository_notice_id,
    runtime_notice_id,
)

from .conftest import NOW


class FakeHass:
    def __init__(self):
        self.config = type("C", (), {"language": "de"})()


@pytest.fixture
def shown(monkeypatch):
    """Record what would be shown and removed in Home Assistant."""
    calls = {"created": [], "dismissed": []}

    def create(hass, message, title=None, notification_id=None):
        calls["created"].append((notification_id, title, message))

    def dismiss(hass, notification_id):
        calls["dismissed"].append(notification_id)

    monkeypatch.setattr(
        dispatcher_module.persistent_notification, "async_create", create
    )
    monkeypatch.setattr(
        dispatcher_module.persistent_notification, "async_dismiss", dismiss
    )
    return calls


def _health(info, name, severity_id="warning"):
    return RepositoryHealth(
        info=replace(info, full_name=f"someone/{name}", name=name),
        findings=[Finding(rule_id="archived", severity_id=severity_id, penalty=30)],
        status=Status.STALE,
    )


def _retrying(*titles):
    info = RuntimeInfo(
        domain="tuya_local",
        name="Tuya Local",
        state=RuntimeState.SETUP_RETRY,
        problem=True,
    )
    info.affected = [
        {"entry_id": title, "title": title, "reason": "device offline"}
        for title in titles
    ]
    info.title = titles[0]
    info.reason = "device offline"
    return info


def test_every_repository_gets_its_own_notification(config, info):
    changes = [
        Change(_health(info, "alpha"), Status.HEALTHY),
        Change(_health(info, "beta"), Status.HEALTHY),
    ]
    [message] = build_problem_messages(config, changes, "de")
    assert [notice.notification_id for notice in message.notices] == [
        repository_notice_id(changes[0].key),
        repository_notice_id(changes[1].key),
    ]
    assert message.notices[0].title == "alpha: veraltet"
    assert "beta" not in message.notices[0].body


def test_a_runtime_problem_has_one_notification_per_integration():
    message = build_runtime_message(_retrying("Garden socket"), "warning", "de")
    [notice] = message.notices
    assert notice.notification_id == runtime_notice_id("tuya_local")
    assert notice.title == "IntegrationGuard: Garden socket"
    assert notice.body.endswith("/config/integrations/integration/tuya_local")


def test_the_recovery_names_the_integration(config):
    message = build_runtime_recovery_message(config, "tuya_local", "Tuya Local", "de")
    assert message.is_recovery
    assert message.body == "Tuya Local ist wieder in Ordnung."
    assert message.notices == []


async def test_a_problem_is_shown_and_good_news_is_not(config, shown):
    dispatcher = Dispatcher(FakeHass(), config)
    await dispatcher.async_send(
        build_runtime_message(_retrying("Garden socket"), "warning", "de")
    )
    await dispatcher.async_send(
        build_runtime_recovery_message(config, "tuya_local", "Tuya Local", "de")
    )
    assert [call[0] for call in shown["created"]] == [runtime_notice_id("tuya_local")]


def test_an_open_notification_follows_a_shrinking_group(config, shown):
    dispatcher = Dispatcher(FakeHass(), config)
    notice = build_runtime_message(
        _retrying("Garden socket", "Hall light"), "warning", "de"
    ).notices[0]
    dispatcher._handle_notices(
        dispatcher_module.persistent_notification.UpdateType.ADDED,
        {notice.notification_id: {"title": notice.title, "message": notice.body}},
    )

    dispatcher.refresh_runtime(_retrying("Garden socket", "Hall light"))
    assert shown["created"] == [], "nothing changed, nothing to redraw"

    dispatcher.refresh_runtime(_retrying("Garden socket"))
    [(notification_id, title, _body)] = shown["created"]
    assert notification_id == runtime_notice_id("tuya_local")
    assert title == "IntegrationGuard: Garden socket"


def test_a_dismissed_notification_stays_dismissed(config, shown):
    dispatcher = Dispatcher(FakeHass(), config)
    notice = build_runtime_message(
        _retrying("Garden socket", "Hall light"), "warning", "de"
    ).notices[0]
    added = {notice.notification_id: {"title": notice.title, "message": notice.body}}
    update = dispatcher_module.persistent_notification.UpdateType
    dispatcher._handle_notices(update.ADDED, added)
    dispatcher._handle_notices(update.REMOVED, added)

    dispatcher.refresh_runtime(_retrying("Garden socket"))
    assert shown["created"] == []


async def test_held_good_news_is_dropped_when_it_broke_again(config, shown):
    config.settings.quiet_hours.enabled = True
    config.settings.quiet_hours.start = "00:00"
    config.settings.quiet_hours.end = "23:59"
    config.settings.quiet_hours.weekdays = []
    dispatcher = Dispatcher(FakeHass(), config)
    now = NOW.replace(hour=12)

    await dispatcher.async_send_runtime_recovery("tuya_local", "Tuya Local", now)
    assert "tuya_local" in dispatcher.held_runtime

    announced = await dispatcher.async_flush_runtime(
        {"tuya_local": _retrying("Garden socket")}
    )
    assert announced == []
    assert shown["created"] == []


async def test_held_good_news_goes_out_when_it_still_holds(config, shown):
    config.settings.quiet_hours.enabled = True
    config.settings.quiet_hours.start = "00:00"
    config.settings.quiet_hours.end = "23:59"
    config.settings.quiet_hours.weekdays = []
    config.channels = []
    dispatcher = Dispatcher(FakeHass(), config)
    sent = []

    async def send(message):
        sent.append(message)

    dispatcher.async_send = send
    await dispatcher.async_send_runtime_recovery(
        "tuya_local", "Tuya Local", NOW.replace(hour=12)
    )
    healthy = RuntimeInfo(domain="tuya_local", state=RuntimeState.OK)
    assert await dispatcher.async_flush_runtime({"tuya_local": healthy}) == []
    assert [message.is_recovery for message in sent] == [True]


async def test_no_good_news_when_the_user_does_not_want_it(config, shown):
    config.settings.notify_on_recovery = False
    dispatcher = Dispatcher(FakeHass(), config)
    sent = []

    async def send(message):
        sent.append(message)

    dispatcher.async_send = send
    await dispatcher.async_send_runtime_recovery("tuya_local", "Tuya Local", NOW)
    assert sent == []


def test_the_card_shows_the_integration_with_a_count():
    assert _retrying("Garden socket", "Hall light").label == "Tuya Local (2)"
    assert _retrying("Garden socket").label == "Garden socket"
    assert RuntimeInfo(domain="tuya_local").label == "tuya_local"


def test_a_restart_brings_the_notification_back(config, shown):
    dispatcher = Dispatcher(FakeHass(), config)
    dispatcher.refresh_runtime(_retrying("Garden socket"))
    assert shown["created"] == [], "a plain refresh never reopens"

    dispatcher.refresh_runtime(_retrying("Garden socket"), reopen=True)
    assert [call[0] for call in shown["created"]] == [runtime_notice_id("tuya_local")]


def test_show_brings_back_notifications_without_sending(config, info, shown):
    dispatcher = Dispatcher(FakeHass(), config)
    change = Change(_health(info, "alpha"), Status.HEALTHY)
    [message] = build_problem_messages(config, [change], "de")
    dispatcher.show(message)
    assert [call[0] for call in shown["created"]] == [repository_notice_id(change.key)]
