# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2026-08-29

### Fixed

- **Integrations with a dismissed discovery were reported as not loaded.**
  When you press "Ignore" on a discovered device, Home Assistant keeps a
  config entry so it stops offering that device again — and never sets it
  up, by design. Those entries sit at "not loaded" forever. On a real
  installation that was 79 of powercalc's 108 entries and 13 of Battery
  Notes' 14, so both looked broken. Dismissed discoveries are now left out
  of both the runtime check and the usage check.

## [0.1.1] - 2026-08-29

### Fixed

- **Apps were reported as unused when they were merely stopped.** On a real
  installation that was 11 of 31 apps — Tailscale, Cloudflared, the file
  editor, the SSH terminal: everything you start when you need it. The
  Supervisor does not say whether an app ever ran, so a stopped app now says
  nothing about whether anyone wants it. No app is reported as unused any
  more; the state and the boot setting are still shown.
- **Every scan reported `https://data-v2.hacs.xyz/app/data.json: HTTP 404`.**
  Apps have no push date from the Supervisor, which put them in the queue for
  the HACS store index — where there is no `app` category. The store is only
  asked about the categories it actually has.
- **An error without a translated sentence showed the raw key** glued to a
  prefix. Anything the catalogue does not cover is now shown as it came out
  of the backend, on its own line.

### Changed

- The GitHub token setting carries a link straight to the token page, and
  says the two things that are easy to get wrong: set the expiry to never,
  and tick no permission at all. GitHub grants every token read access to
  public repositories; nothing beyond that is used.
- Links in the panel follow the theme colour instead of the browser default,
  which was close to unreadable on a dark theme.

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

[Unreleased]: https://github.com/sphings79/integrationguard-home-assistant/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.2
[0.1.1]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.1
[0.1.0]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.0
