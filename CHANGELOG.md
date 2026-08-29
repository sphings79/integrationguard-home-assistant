# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-29

First release.

### Added

- **Health of every installed extension.** Sixteen rules, each one switchable,
  reweightable and with its own threshold: last commit, newest release,
  archived, repository gone, removed from the HACS store, on the HACS security
  list, no release at all, prereleases only, open issues, stars, required Home
  Assistant version, update available, installed from a branch, unused.
- **Apps** (formerly add-ons) are judged the same way, plus three rules of
  their own: the store repository is gone, the author marked it deprecated,
  the Supervisor no longer offers it. Home Assistant OS and Supervised only.
- **Usage detection.** Cards are matched against every dashboard in both
  directions — the types read out of the bundle, and the types the dashboards
  ask for looked up inside the bundle. A card that cannot be read is reported
  as "cannot be determined", never as unused. Integrations are judged by their
  config entries, entities and devices; themes by the default and the per-user
  choice; templates and python_scripts by a text search across the
  configuration.
- **Leftovers.** Lovelace resources without a file, folders in `www/community`
  and `custom_components` that HACS does not know about.
- **Runtime.** Config entry states, pending reauthentications and Home
  Assistant's own repair messages, live rather than once a day, with a grace
  period so a restart does not produce a wave of notifications.
- **Panel** with eight views, and a Lovelace card that registers itself.
- **Notifications** through SMTP, Telegram, Pushover, ntfy or any Home
  Assistant service, with severities, quiet hours and per-channel templates.
- Eleven languages: English, German, Dutch, French, Spanish, Italian,
  Portuguese, Polish, Swedish, Danish and Czech.

[Unreleased]: https://github.com/sphings79/integrationguard-home-assistant/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.0
