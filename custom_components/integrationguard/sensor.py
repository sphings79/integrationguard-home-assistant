"""Collective sensors: one number each, the detail lives in the attributes."""

from __future__ import annotations

from collections import Counter
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import IntegrationGuardConfigEntry
from .const import DOMAIN, Status, Usage
from .coordinator import IntegrationGuardCoordinator
from .entity import IntegrationGuardEntity
from .models import RepositoryHealth


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationGuardConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the collective sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ScoreSensor(coordinator),
            ProblemsSensor(coordinator),
            StatusCountSensor(coordinator, Status.STALE, "stale"),
            StatusCountSensor(coordinator, Status.ABANDONED, "abandoned"),
            UnusedSensor(coordinator),
            RepositoriesSensor(coordinator),
            RuntimeProblemsSensor(coordinator),
            RepairsSensor(coordinator),
            LastScanSensor(coordinator),
        ]
    )


def _names(repositories: list[RepositoryHealth]) -> list[str]:
    """Return the identifiers behind a count.

    HACS repositories are named "owner/repo"; apps are named "app:<slug>",
    because several apps can share one store repository.
    """
    return sorted(repository.key for repository in repositories)


def _urls(repositories: list[RepositoryHealth]) -> dict[str, str]:
    """Return a link to the source repository for everything behind a count."""
    return {item.key: item.info.url for item in repositories if item.info.url}


class ScoreSensor(IntegrationGuardEntity, SensorEntity):
    """The mean health score across every judged repository."""

    _attr_translation_key = "score"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator: IntegrationGuardCoordinator) -> None:
        """Create the score sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_score"

    @property
    def native_value(self) -> int | None:
        """Return the mean score, or None before the first scan."""
        return self.coordinator.average_score()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Name the worst repository, which the mean would otherwise hide."""
        worst = self.coordinator.worst()
        return {
            "worst_score": worst.score if worst else None,
            "worst_repository": worst.key if worst else None,
        }


class ProblemsSensor(IntegrationGuardEntity, SensorEntity):
    """How many repositories are not healthy."""

    _attr_translation_key = "problems"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "repositories"

    def __init__(self, coordinator: IntegrationGuardCoordinator) -> None:
        """Create the problem counter."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_problems"

    @property
    def native_value(self) -> int | None:
        """Return the number of repositories with at least one finding."""
        result = self.coordinator.result
        return len(result.problems()) if result else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Break the total down by status and list the repositories."""
        result = self.coordinator.result
        if result is None:
            return {}
        problems = result.problems()
        return {
            "repositories": _names(problems),
            "urls": _urls(problems),
            "by_status": dict(Counter(item.status for item in problems)),
        }


class StatusCountSensor(IntegrationGuardEntity, SensorEntity):
    """How many repositories carry one particular status."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "repositories"

    def __init__(
        self,
        coordinator: IntegrationGuardCoordinator,
        status: Status,
        translation_key: str,
    ) -> None:
        """Bind the counter to one status."""
        super().__init__(coordinator)
        self._status = status
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{DOMAIN}_{translation_key}"

    @property
    def native_value(self) -> int | None:
        """Return how many repositories carry the status."""
        result = self.coordinator.result
        return len(result.by_status(self._status)) if result else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """List the repositories behind the count."""
        result = self.coordinator.result
        if result is None:
            return {}
        affected = result.by_status(self._status)
        return {"repositories": _names(affected), "urls": _urls(affected)}


class UnusedSensor(IntegrationGuardEntity, SensorEntity):
    """How many installed repositories nothing seems to use."""

    _attr_translation_key = "unused"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "repositories"

    def __init__(self, coordinator: IntegrationGuardCoordinator) -> None:
        """Create the unused counter."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_unused"

    @property
    def native_value(self) -> int | None:
        """Return the number of unused repositories."""
        result = self.coordinator.result
        return len(result.unused()) if result else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """List the unused repositories and how sure the verdict is."""
        result = self.coordinator.result
        if result is None:
            return {}
        unused = result.unused()
        return {
            "repositories": _names(unused),
            "urls": _urls(unused),
            "confidence": {
                item.key: item.usage_confidence
                for item in unused
                if item.usage_confidence
            },
            "undetermined": _names(
                [
                    item
                    for item in result.repositories
                    if item.usage == Usage.UNDETERMINED
                ]
            ),
        }


class RepositoriesSensor(IntegrationGuardEntity, SensorEntity):
    """How many repositories are installed altogether."""

    _attr_translation_key = "repositories"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "repositories"

    def __init__(self, coordinator: IntegrationGuardCoordinator) -> None:
        """Create the total counter."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_repositories"

    @property
    def native_value(self) -> int | None:
        """Return the number of judged repositories."""
        result = self.coordinator.result
        return len(result.repositories) if result else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Split the total by category and count the ignored ones."""
        result = self.coordinator.result
        if result is None:
            return {}
        return {
            "by_category": dict(
                Counter(item.info.category for item in result.repositories)
            ),
            "ignored": _names([r for r in result.repositories if r.ignored]),
            "custom_repositories": _names(
                [r for r in result.repositories if not r.info.is_default_store]
            ),
        }


class RuntimeProblemsSensor(IntegrationGuardEntity, SensorEntity):
    """Integrations whose setup is not working on this installation.

    Deliberately separate from the health score: an expired API key says
    nothing about the state of a repository.
    """

    _attr_translation_key = "runtime_problems"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "integrations"

    def __init__(self, coordinator: IntegrationGuardCoordinator) -> None:
        """Create the runtime counter."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_runtime_problems"

    @property
    def native_value(self) -> int:
        """Return how many integrations need attention."""
        return len(self.coordinator.runtime.problems())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Name the integrations, why, and where to look."""
        problems = self.coordinator.runtime.problems()
        return {
            "integrations": sorted(info.domain for info in problems),
            "detail": {
                info.domain: {
                    "state": info.state,
                    "reason": info.reason,
                    "since": info.since,
                    "url": info.url,
                    "configuration_url": info.configuration_url,
                    "repairs": len(info.repairs),
                }
                for info in problems
            },
            "waiting": sorted(
                info.domain
                for info in self.coordinator.runtime.states.values()
                if not info.problem and info.state != "ok"
            ),
        }


class RepairsSensor(IntegrationGuardEntity, SensorEntity):
    """Repair messages Home Assistant raised for the watched integrations."""

    _attr_translation_key = "repairs"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "issues"

    def __init__(self, coordinator: IntegrationGuardCoordinator) -> None:
        """Create the repair counter."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_repairs"

    @property
    def native_value(self) -> int:
        """Return how many repair messages are open."""
        return len(self.coordinator.runtime.repairs())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """List the messages with their severity and where they came from."""
        runtime = self.coordinator.runtime
        return {
            "issues": [
                {
                    **issue.to_dict(),
                    "url": runtime.states[issue.domain].url
                    if issue.domain in runtime.states
                    else None,
                }
                for issue in runtime.repairs()
            ],
            "by_severity": dict(
                Counter(issue.severity or "unknown" for issue in runtime.repairs())
            ),
        }


class LastScanSensor(IntegrationGuardEntity, SensorEntity):
    """When the last scan finished, and how it went."""

    _attr_translation_key = "last_scan"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: IntegrationGuardCoordinator) -> None:
        """Create the timestamp sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_last_scan"

    @property
    def native_value(self) -> Any:
        """Return when the last scan finished."""
        result = self.coordinator.result
        return result.finished if result else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Report duration, data sources and what is still outstanding."""
        result = self.coordinator.result
        if result is None:
            return {}
        return {
            "duration": round(result.duration, 1),
            "errors": result.source_errors,
            "orphans": result.orphans,
            "github_remaining": result.github_remaining,
            "github_pending": result.github_pending,
        }
