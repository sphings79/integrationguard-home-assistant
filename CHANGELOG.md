# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.6] - 2026-08-29

### Fixed

- **Integrations that own no entities were reported as unused.** An
  integration with a config entry but no entities and no devices was called
  unused. Switch Manager runs blueprints on events, others only register
  services or publish over MQTT — none of them owns an entity, and all of
  them were flagged. Having been configured is the evidence; owning no
  entity is not evidence of the opposite. An enabled config entry now means
  used, and the counts are shown but no longer judged on.
- An integration that is loaded without a config entry and owns nothing is
  "cannot be determined" rather than unused. It may be configured in YAML
  and own nothing, which cannot be told apart from here.

## [0.1.5] - 2026-08-29

### Fixed

- **The result did not survive a restart.** Every sensor went to `unknown`
  and the panel stood empty until the first scan afterwards, several minutes
  later. The caches were persisted but the result itself was not. It is
  stored now and restored on start, so everything is there immediately and
  the timestamp says when that scan actually ran.

## [0.1.4] - 2026-08-29

### Fixed

- **The key-based usage detection added in 0.1.3 never ran.** The line that
  collects the keys out of a dashboard was missing, so the set it matches
  against was always empty. card-mod stayed "cannot be determined" although
  five dashboards use it. There is a test for it now.

## [0.1.3] - 2026-08-29

### Fixed

- **card-mod and card-tools were reported as unused.** Exactly the case the
  detection was built to avoid. A plugin that defines custom elements but
  announces no card of its own was called unused with medium confidence —
  which is the guess this integration promises not to make. Only a plugin
  that announces a card, badge, row or feature through `window.customCards`
  or one of its siblings can be called unused now; everything else is
  "cannot be determined".
- **Plugins used through a key of their own were missed.** card-mod is
  switched on by writing `card_mod:` under a card, never as
  `custom:card-mod`. The keys of the dashboard configuration are now read as
  well, so such a plugin is recognised as used instead of merely
  undetermined.
- **Clicking a repository in the overview or in the unused list did
  nothing.** Both set the selection but stayed on their own tab, and the
  detail is only rendered in the repositories tab. They now switch there and
  clear the filters, so the entry cannot be hidden behind one.

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

[Unreleased]: https://github.com/sphings79/integrationguard-home-assistant/compare/v0.1.6...HEAD
[0.1.6]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.6
[0.1.5]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.5
[0.1.4]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.4
[0.1.3]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.3
[0.1.2]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.2
[0.1.1]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.1
[0.1.0]: https://github.com/sphings79/integrationguard-home-assistant/releases/tag/v0.1.0
