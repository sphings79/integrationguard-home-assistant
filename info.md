# IntegrationGuard

**Which of your HACS extensions is still maintained, and which one is nobody using?**

Checks every repository you installed through HACS — and every app on Home
Assistant OS — for whether it is still being worked on, whether anything here
actually uses it, and whether its setup works. Own panel, own Lovelace card,
notifications through SMTP, Telegram, Pushover, ntfy or any Home Assistant
service.

## What it finds

- **Abandoned** — no commit for years, archived on GitHub, repository deleted,
  removed from the HACS store, or on the HACS security list
- **Unused** — a card installed but on no dashboard, an integration with no
  config entry, a theme nobody selected, a python_script nothing calls
- **Leftovers** — Lovelace resources pointing at files that are gone, folders
  HACS no longer knows about
- **Broken setups** — config entries that failed, integrations asking to be
  signed in again, Home Assistant's own repair messages

## What it does not do

It does not update anything, it does not uninstall anything, and it does not
touch your HACS. It looks, and it tells you.

## After installing

Settings → Devices & services → Add integration → **IntegrationGuard**. A
GitHub token is optional — without one, GitHub allows 60 requests an hour,
which is enough for a daily check but slow on the first run. Everything else
is configured in the **IntegrationGuard** panel in the sidebar. The Lovelace
card registers itself.

---

Unofficial and community built — not affiliated with or endorsed by the Home
Assistant project, HACS or GitHub. Data comes from HACS' own public store
index and from GitHub's public API.

If it saves you from carrying a dead integration around, a ⭐ helps others
find it.
