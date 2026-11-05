"""The repository source: Marketplace first, HACS as the fallback."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from homeassistant.config_entries import ConfigEntryState

from custom_components.integrationguard.sources import hacs


def _repository(full_name: str = "someone/thing") -> SimpleNamespace:
    data = SimpleNamespace(
        full_name=full_name,
        category="integration",
        id="42",
        domain="thing",
        last_updated="2026-08-01T00:00:00+00:00",
    )
    return SimpleNamespace(
        data=data,
        display_name="Thing",
        display_installed_version="1.0.0",
        display_available_version="1.1.0",
        pending_update=True,
        repository_manifest=None,
    )


def _registry(attribute: str, *, as_method: bool = False) -> SimpleNamespace:
    repositories = [_repository()]
    value: Any = (lambda: repositories) if as_method else repositories
    return SimpleNamespace(**{attribute: value}, is_default=lambda _id: True)


def _hass(
    *, entries: list[Any] | None = None, data: dict[str, Any] | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda _domain: entries or []),
        data=data or {},
    )


def _entry(manager: Any, state: ConfigEntryState = ConfigEntryState.LOADED):
    return SimpleNamespace(state=state, runtime_data=manager)


def test_marketplace_manager_is_read() -> None:
    manager = SimpleNamespace(repositories=_registry("list_installed"))
    result = hacs.async_installed_repositories(_hass(entries=[_entry(manager)]))
    assert result is not None
    assert [info.full_name for info in result] == ["someone/thing"]
    assert result[0].pending_update is True


def test_hacs_instance_is_still_read() -> None:
    manager = SimpleNamespace(repositories=_registry("list_downloaded"))
    result = hacs.async_installed_repositories(_hass(data={"hacs": manager}))
    assert result is not None
    assert len(result) == 1


def test_old_hacs_method_spelling() -> None:
    manager = SimpleNamespace(repositories=_registry("list_downloaded", as_method=True))
    result = hacs.async_installed_repositories(_hass(data={"hacs": manager}))
    assert result is not None
    assert len(result) == 1


def test_marketplace_wins_over_leftover_hacs() -> None:
    market = SimpleNamespace(repositories=_registry("list_installed"))
    old = SimpleNamespace(repositories=SimpleNamespace(list_downloaded=[]))
    result = hacs.async_installed_repositories(
        _hass(entries=[_entry(market)], data={"hacs": old})
    )
    assert result is not None
    assert len(result) == 1


def test_unloaded_marketplace_is_unavailable() -> None:
    manager = SimpleNamespace(repositories=_registry("list_installed"))
    hass = _hass(entries=[_entry(manager, ConfigEntryState.SETUP_RETRY)])
    assert hacs.async_is_available(hass) is False
    assert hacs.async_installed_repositories(hass) is None


def test_nothing_available() -> None:
    assert hacs.async_installed_repositories(_hass()) is None


def test_registry_without_any_list_gives_none() -> None:
    manager = SimpleNamespace(repositories=SimpleNamespace())
    assert hacs.async_installed_repositories(_hass(data={"hacs": manager})) is None
