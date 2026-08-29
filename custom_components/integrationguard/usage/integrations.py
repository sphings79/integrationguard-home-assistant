"""Decides whether an integration installed through HACS is in use."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.loader import IntegrationNotLoaded, async_get_loaded_integration

from ..const import Confidence, Usage

_LOGGER = logging.getLogger(__name__)


def required_domains(hass: HomeAssistant) -> set[str]:
    """Return the domains another loaded integration depends on.

    A backend helper that nothing configures directly is still needed, so it
    must not be reported as unused.
    """
    required: set[str] = set()
    for domain in list(hass.config.components):
        # Platforms show up as "sensor.demo"; only the integrations matter.
        base = domain.partition(".")[0]
        try:
            integration = async_get_loaded_integration(hass, base)
        except (IntegrationNotLoaded, KeyError):
            continue
        required.update(integration.dependencies)
        required.update(integration.after_dependencies)
    return required


def evaluate(
    hass: HomeAssistant, domain: str, required: set[str]
) -> tuple[str, str, dict]:
    """Return usage, confidence and detail for one integration."""
    # Ignored discoveries are not configuration: they only exist so Home
    # Assistant stops offering the device.
    entries = hass.config_entries.async_entries(domain, include_ignore=False)
    loaded = domain in hass.config.components
    detail: dict = {"entries": len(entries), "loaded": loaded}

    if entries:
        enabled = [entry for entry in entries if entry.disabled_by is None]
        detail["enabled_entries"] = len(enabled)
        # Counted for information only. Plenty of integrations legitimately
        # own nothing: Switch Manager runs blueprints on events, others only
        # register services or publish over MQTT. Having been configured is
        # the evidence; owning no entity is not evidence of the opposite.
        detail.update(_counts(hass, domain, [e.entry_id for e in enabled]))
        if enabled:
            return Usage.USED, Confidence.HIGH, detail
        # Every entry switched off by hand is a decision, not a guess.
        return Usage.UNUSED, Confidence.MEDIUM, detail

    if not loaded:
        # Not even imported: nothing on this installation asks for it.
        return Usage.UNUSED, Confidence.HIGH, detail

    counts = _counts(hass, domain, None)
    detail.update(counts)
    if counts["entities"] or counts["devices"]:
        # Configured in YAML rather than through the interface.
        return Usage.USED, Confidence.HIGH, detail
    if domain in required:
        detail["required_by_another_integration"] = True
        return Usage.UNDETERMINED, Confidence.LOW, detail
    # Loaded without a config entry and without anything of its own. Something
    # pulled it in, or it is configured in YAML and owns nothing. Neither can
    # be told apart from here.
    return Usage.UNDETERMINED, Confidence.LOW, detail


def _counts(hass: HomeAssistant, domain: str, entry_ids: list[str] | None) -> dict:
    """Count the entities and devices belonging to an integration."""
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    if entry_ids is None:
        entity_count = sum(
            1 for entry in entities.entities.values() if entry.platform == domain
        )
        device_count = sum(
            1
            for device in devices.devices.values()
            if any(identifier[0] == domain for identifier in device.identifiers)
        )
    else:
        entity_count = sum(
            len(er.async_entries_for_config_entry(entities, entry_id))
            for entry_id in entry_ids
        )
        device_count = sum(
            len(dr.async_entries_for_config_entry(devices, entry_id))
            for entry_id in entry_ids
        )
    return {"entities": entity_count, "devices": device_count}
