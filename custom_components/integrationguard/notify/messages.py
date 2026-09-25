"""Builds the text of a notification.

The data changes once a day, so a run produces one message per severity rather
than a stream of single alerts. The notification inside Home Assistant is the
exception: it is one per problem, so it can be removed on its own once that
problem is gone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..const import DOMAIN, Status
from ..l10n import finding_text, translate
from ..models import Config, RepositoryHealth, RuntimeInfo

MAX_LINES = 20


@dataclass(slots=True)
class Change:
    """One repository whose verdict changed since the last announcement."""

    item: RepositoryHealth
    previous: str

    @property
    def key(self) -> str:
        """Return the identifier of the changed repository."""
        return self.item.key


@dataclass(slots=True)
class Notice:
    """One notification inside Home Assistant, about exactly one problem."""

    notification_id: str
    title: str
    body: str


@dataclass(slots=True)
class Message:
    """A message about one severity, ready to be rendered per channel."""

    severity_id: str
    title: str
    body: str
    keys: list[str] = field(default_factory=list)
    url: str | None = None
    is_recovery: bool = False
    notices: list[Notice] = field(default_factory=list)


def repository_notice_id(key: str) -> str:
    """Return the id of the Home Assistant notification about a repository."""
    return f"{DOMAIN}_repository_{key}"


def runtime_notice_id(domain: str) -> str:
    """Return the id of the Home Assistant notification about an integration."""
    return f"{DOMAIN}_runtime_{domain}"


def _with_url(body: str, url: str | None) -> str:
    """Return a body with the link underneath, the way notifications show it."""
    return f"{body}\n\n{url}" if url else body


def severity_of(config: Config, item: RepositoryHealth) -> str | None:
    """Return the severity a repository's worst finding carries."""
    best: tuple[int, str] | None = None
    for finding in item.findings:
        severity = config.severity(finding.severity_id)
        priority = severity.priority if severity else 50
        if best is None or priority > best[0]:
            best = (priority, finding.severity_id)
    return best[1] if best else None


def lowest_severity(config: Config) -> str | None:
    """Return the least urgent severity, used to announce good news."""
    if not config.severities:
        return None
    return min(config.severities, key=lambda s: s.priority).id


def build_problem_messages(
    config: Config, changes: list[Change], language: str
) -> list[Message]:
    """Return one message per severity for everything that got worse."""
    grouped: dict[str, list[Change]] = {}
    for change in changes:
        severity_id = severity_of(config, change.item)
        if severity_id is None:
            continue
        grouped.setdefault(severity_id, []).append(change)

    messages: list[Message] = []
    for severity_id, group in grouped.items():
        group.sort(key=lambda change: change.item.key)
        messages.append(
            Message(
                severity_id=severity_id,
                title=_problem_title(config, group, language),
                body=_problem_body(group, language),
                keys=[change.key for change in group],
                url=group[0].item.info.url if len(group) == 1 else None,
                notices=[
                    Notice(
                        notification_id=repository_notice_id(change.key),
                        title=_problem_title(config, [change], language),
                        body=_problem_body([change], language),
                    )
                    for change in group
                ],
            )
        )
    return messages


def build_recovery_message(
    config: Config, changes: list[Change], language: str
) -> Message | None:
    """Return one message for everything that is healthy again."""
    if not changes:
        return None
    severity_id = lowest_severity(config)
    if severity_id is None:
        return None
    changes.sort(key=lambda change: change.item.key)
    if len(changes) == 1:
        item = changes[0].item
        title = translate(language, "title.runtime", name=item.info.name)
        body = translate(language, "body.recovered", name=item.info.name)
    else:
        title = translate(language, "title.recovered", count=len(changes))
        body = "\n".join(
            translate(language, "body.recovered", name=change.item.info.name)
            for change in changes[:MAX_LINES]
        )
    return Message(
        severity_id=severity_id,
        title=title,
        body=body,
        keys=[change.key for change in changes],
        url=changes[0].item.info.url if len(changes) == 1 else None,
        is_recovery=True,
    )


def build_runtime_message(
    info: RuntimeInfo, severity_id: str, language: str
) -> Message:
    """Return the message for one integration whose runtime state changed."""
    if len(info.affected) > 1:
        title = translate(language, "title.runtime", name=info.name or info.domain)
        body = _runtime_group_body(info, language)
    else:
        state = translate(language, f"runtime.{info.state}")
        name = info.title or info.domain
        key = "body.runtime_reason" if info.reason else "body.runtime"
        title = translate(language, "title.runtime", name=name)
        body = translate(language, key, name=name, state=state, reason=info.reason)
    url = info.url or info.configuration_url
    return Message(
        severity_id=severity_id,
        title=title,
        body=body,
        keys=[info.domain],
        url=url,
        notices=[Notice(runtime_notice_id(info.domain), title, _with_url(body, url))],
    )


def build_runtime_recovery_message(
    config: Config, domain: str, name: str, language: str
) -> Message | None:
    """Return the message that an integration is working again."""
    severity_id = lowest_severity(config)
    if severity_id is None:
        return None
    return Message(
        severity_id=severity_id,
        title=translate(language, "title.runtime", name=name),
        body=translate(language, "body.recovered", name=name),
        keys=[domain],
        url=RuntimeInfo(domain=domain).configuration_url,
        is_recovery=True,
    )


def _runtime_group_body(info: RuntimeInfo, language: str) -> str:
    """Return the text for several entries of an integration in trouble."""
    header = translate(
        language,
        "body.runtime_many",
        count=len(info.affected),
        state=translate(language, f"runtime_many.{info.state}"),
    )
    lines = [
        f"{entry['title']}: {entry['reason']}" if entry["reason"] else entry["title"]
        for entry in info.affected[:MAX_LINES]
    ]
    if len(info.affected) > MAX_LINES:
        lines.append(f"... +{len(info.affected) - MAX_LINES}")
    return "\n".join([header, *lines])


def _problem_title(config: Config, group: list[Change], language: str) -> str:
    """Return the headline for a group of findings."""
    if len(group) == 1:
        item = group[0].item
        status = translate(language, f"status.{item.status}")
        return f"{item.info.name}: {status}"
    return translate(language, "title.problems", count=len(group))


def _problem_body(group: list[Change], language: str) -> str:
    """Return one line per repository, with the reasons behind it."""
    lines: list[str] = []
    for change in group[:MAX_LINES]:
        item = change.item
        reasons = ", ".join(
            finding_text(language, finding.rule_id, finding.params)
            for finding in item.findings
        )
        line = f"{item.info.name} ({item.key})"
        if reasons:
            line = f"{line}: {reasons}"
        if item.info.url:
            line = f"{line}\n{item.info.url}"
        lines.append(line)
    if len(group) > MAX_LINES:
        lines.append(f"... +{len(group) - MAX_LINES}")
    return "\n\n".join(lines)


def collect_changes(
    repositories: list[RepositoryHealth], announced: dict[str, str]
) -> tuple[list[Change], list[Change]]:
    """Split the repositories into what got worse and what recovered.

    A repository nobody has heard about yet counts as a change only when it is
    not healthy — a fresh installation should not announce everything at once.
    """
    problems: list[Change] = []
    recoveries: list[Change] = []
    for item in repositories:
        if item.ignored:
            continue
        previous = announced.get(item.key)
        if previous == item.status:
            continue
        if item.status != Status.HEALTHY:
            problems.append(Change(item, previous or Status.HEALTHY))
        elif previous is not None:
            recoveries.append(Change(item, previous))
    return problems, recoveries
