<div align="center">
  <img src="assets/banner.svg" alt="IntegrationGuard für Home Assistant — ein Gesundheitsring mit dem Wert 74 neben drei Statuskarten mit den Beschriftungen verwaist, ungenutzt und Einrichtung fehlgeschlagen" width="100%">

  # IntegrationGuard — HACS-Zustand und ungenutzte Erweiterungen für Home Assistant

  **Findet heraus, welche deiner HACS-Erweiterungen nicht mehr gepflegt wird und welche niemand benutzt.**

  Liest denselben öffentlichen Store-Index, den [HACS](https://hacs.xyz) selbst verwendet, nimmt deine Dashboards und Config-Entries dazu und sagt dir, wo du hinschauen solltest.

  <img src="https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge" alt="Über HACS als Custom Repository verfügbar">
  <img src="https://img.shields.io/github/v/release/sphings79/integrationguard-home-assistant?style=for-the-badge" alt="Neuestes Release">
  <img src="https://img.shields.io/badge/Home%20Assistant-2026.1.0%2B-41BDF5?style=for-the-badge" alt="Benötigt Home Assistant 2026.1.0 oder neuer">
  <img src="https://img.shields.io/badge/license-MIT-3ddc97?style=for-the-badge" alt="MIT-Lizenz">

  [English](README.md) · **Deutsch**
</div>

## Inhaltsverzeichnis

- [Was diese Integration macht](#was-diese-integration-macht)
- [Welche Entitäten du bekommst](#welche-entitäten-du-bekommst)
- [Wie es funktioniert](#wie-es-funktioniert)
- [Wie ungenutzte Karten gefunden werden](#wie-ungenutzte-karten-gefunden-werden)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Die Regeln](#die-regeln)
- [Automatisierungsbeispiele](#automatisierungsbeispiele)
- [Dashboard-Beispiel](#dashboard-beispiel)
- [Fehlerbehebung](#fehlerbehebung)
- [Häufige Fragen](#häufige-fragen)
- [Was es bewusst nicht macht](#was-es-bewusst-nicht-macht)
- [Credits](#credits)
- [Haftungsausschluss](#haftungsausschluss)
- [Mitmachen](#mitmachen)
- [Lizenz](#lizenz)

## Was diese Integration macht

Eine Home-Assistant-Instanz sammelt Erweiterungen an. Nach zwei Jahren hast du
neunzig davon und keine Ahnung mehr, an welchen noch gearbeitet wird, welche du
nicht mehr benutzt und welche still kaputt ist. IntegrationGuard beantwortet
alle drei Fragen.

**Wird es noch gepflegt?** Letzter Commit, neuestes Release, auf GitHub
archiviert, Repository gelöscht, aus dem HACS-Store entfernt, auf der
HACS-Sicherheitsliste, nur Vorabversionen, verlangt ein neueres Home Assistant
als du hast. Sechzehn Regeln, jede einzeln abschaltbar und umgewichtbar.

**Benutzt es überhaupt jemand?** Eine Karte, die auf keinem Dashboard liegt.
Eine Integration ohne Config-Entry. Ein Theme, das niemand ausgewählt hat. Ein
python_script, das niemand aufruft. Dazu das Verwaiste — Lovelace-Ressourcen,
die auf verschwundene Dateien zeigen, und Ordner in `custom_components`, die
HACS nicht kennt.

**Funktioniert es?** Config-Entries, deren Einrichtung fehlgeschlagen ist,
Integrationen, die eine neue Anmeldung verlangen, und Home Assistants eigene
Reparaturmeldungen — live beobachtet, nicht einmal am Tag.

Apps (früher Add-ons) werden auf Home Assistant OS und Supervised genauso
bewertet: ihr Store-Repository wird geprüft wie jedes andere, dazu kommt, ob der
Autor die App als veraltet gekennzeichnet hat, ob der Supervisor sie noch
anbietet und ob sie installiert, aber nie gestartet wurde.

## Welche Entitäten du bekommst

<img src="assets/entities.svg" alt="Die neun Sensoren, die IntegrationGuard unter einem Gerät anlegt, dazu ein Binärsensor für Kritisches und ein Schalter für die Überwachung" width="100%">

| Entität | Beispiel | Was drinsteht |
| --- | --- | --- |
| `sensor.integrationguard_gesundheitswert` | `89` | Mittelwert. In den Attributen steht das schlechteste Repository, das ein Mittelwert sonst verstecken würde |
| `sensor.integrationguard_probleme` | `6` | Repositories mit mindestens einem Befund, jeweils mit GitHub-Link |
| `sensor.integrationguard_veraltet` | `4` | Kein Commit jenseits der Schwelle |
| `sensor.integrationguard_verwaist` | `2` | Archiviert, gelöscht oder aus dem Store geflogen |
| `sensor.integrationguard_ungenutzt` | `7` | Installiert, aber nichts hier verwendet es — mit Konfidenz |
| `sensor.integrationguard_repositories` | `90` | Alles Installierte, aufgeteilt nach Kategorie |
| `sensor.integrationguard_laufzeitprobleme` | `1` | Config-Entries, die nicht laufen |
| `sensor.integrationguard_reparaturmeldungen` | `2` | Reparaturmeldungen zu beobachteten Integrationen |
| `sensor.integrationguard_letzte_prufung` | Zeitstempel | Dauer, Quellenfehler, verbleibendes GitHub-Budget |
| `binary_sensor.integrationguard_kritisch` | `off` | An, wenn etwas archiviert, gelöscht oder markiert ist |
| `switch.integrationguard_uberwachung` | `on` | Pausiert den Zeitplan. Eine Prüfung von Hand läuft trotzdem |

Die Entity-IDs richten sich nach der Oberflächensprache — auf Englisch heißt der
erste `sensor.integrationguard_score`.

## Wie es funktioniert

<img src="assets/architecture.svg" alt="Datenfluss: HACS im laufenden Prozess, der öffentliche HACS-Store-Index, die optionale GitHub-API und der Supervisor speisen IntegrationGuard, das daraus Zustand, Nutzung und Laufzeit zu Sensoren, Panel, Karte und Benachrichtigungen verbindet" width="100%">

Vier Quellen, in dieser Reihenfolge:

1. **HACS im laufenden Prozess.** Alles, was HACS heruntergeladen hat, auch die
   Custom Repositories, die in keinem Store stehen. Auf einer gewachsenen
   Instanz ist das ein Viertel von allem.
2. **Der öffentliche HACS-Store-Index** unter `data-v2.hacs.xyz` — dieselben
   Daten, die dein HACS ohnehin holt. Kein Token, kein Konto, und eine
   konditionale Anfrage kostet nichts, wenn sich nichts geändert hat. Von dort
   kommen auch die Listen der entfernten und der als kritisch markierten Repos.
3. **GitHub**, optional und nur für das, was die ersten beiden nicht beantworten:
   archiviert, Repository gelöscht, Datum des neuesten Releases. Ohne Token
   erlaubt GitHub 60 Anfragen pro Stunde; konditionale Anfragen, die mit *nicht
   geändert* antworten, zählen nicht dagegen — teuer ist also nur der erste
   Durchlauf.
4. **Deine Installation** — Dashboards, Config-Entries, Reparaturmeldungen,
   Themes, das Konfigurationsverzeichnis.

Alles liegt in `.storage`. Außer den beiden lesenden Anfragen oben verlässt
nichts die Maschine.

## Wie ungenutzte Karten gefunden werden

<img src="assets/usage.svg" alt="Nutzungserkennung in zwei Richtungen: aus dem installierten Bundle gelesene Elementnamen und die von den Dashboards angesprochenen Kartentypen, im Bundle nachgeschlagen" width="100%">

Die Elementnamen aus dem Bundle zu lesen ist der naheliegende Weg — und er
reicht nicht. Mushroom baut seine Kartenliste aus Variablen zusammen; ein
regulärer Ausdruck findet einen einzigen Badge-Namen und verfehlt jede Karte.
Deshalb läuft die Prüfung in beide Richtungen: die aus dem Bundle gelesenen
Namen **und** jeder `custom:`-Typ, den die Dashboards ansprechen, als
Zeichenkette im Bundle nachgeschlagen. Eine Karte, die ein Dashboard anspricht,
muss ihren eigenen Namen irgendwo tragen, egal was sie damit anstellt.

Kommt aus beiden Richtungen nichts, lautet die Antwort **nicht bestimmbar**,
nicht *ungenutzt*. Genau das hält card-mod, card-tools, kiosk-mode,
custom-sidebar und die Icon-Sets aus den Ergebnissen heraus — die bringen keine
ansprechbare Karte mit, und Raten wäre schlechter als Schweigen.

Ist ein **Strategy-Dashboard** im Einsatz, sinkt die Konfidenz um eine Stufe:
eine Strategy entscheidet zur Laufzeit, was sie anzeigt, und das steht in keiner
gespeicherten Konfiguration. Das automatisch erzeugte Standard-Dashboard zählt
dabei nicht — Home Assistant baut es aus der Entity-Registry und kann darin gar
keine Custom-Karte unterbringen.

## Installation

<img src="assets/install.svg" alt="Vier Installationsschritte: Repository in HACS eintragen, herunterladen, Home Assistant neu starten, dann die Integration hinzufügen und das Panel öffnen" width="100%">

### Über HACS

1. HACS → die drei Punkte → **Benutzerdefinierte Repositories**
2. URL `https://github.com/sphings79/integrationguard-home-assistant`, Typ **Integration**
3. Nach **IntegrationGuard** suchen und herunterladen
4. Home Assistant neu starten
5. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → IntegrationGuard

### Von Hand

`custom_components/integrationguard` in dein `config/custom_components`
kopieren und neu starten.

Die Lovelace-Karte registriert sich selbst, es ist keine Ressource einzutragen.
Bei einem YAML-Dashboard geht das nicht automatisch:

```yaml
resources:
  - url: /integrationguard-frontend/integrationguard-card.js
    type: module
```

## Konfiguration

Der Einrichtungsdialog fragt genau eine optionale Sache ab: ein GitHub-Token.
Alles andere steht im **IntegrationGuard**-Panel in der Seitenleiste.

| Einstellung | Standard | Was sie ändert |
| --- | --- | --- |
| Prüfen alle | 24 Stunden | Wie oft eine Prüfung läuft |
| Verankert um | 04:00 | Die tägliche Uhrzeit. Bei sechs Stunden: diese Zeit, dann alle sechs Stunden |
| GitHub-Token | leer | 60 Anfragen pro Stunde ohne, 5000 mit. Lesezugriff auf öffentliche Repositories genügt |
| Zustand prüfen bei | alle Kategorien | Was bewertet wird |
| Nutzung prüfen bei | alle außer AppDaemon | Was auf Verwendung geprüft wird |
| Nach Verwaistem suchen | an | Tote Lovelace-Ressourcen und unbekannte Ordner |
| Config-Entries beobachten | an | Die Laufzeit-Säule |
| Alle Integrationen | aus | An: auch Core-Integrationen, nicht nur die aus HACS |
| Karenzzeit | 15 Minuten | Wie lange ein wiederholender Config-Entry still bleibt |
| Ruhezeiten | aus | Benachrichtigungen werden zurückgehalten und danach nachgeholt |
| Panel-Zugriff | Administratoren | Oder alle |
| Verlauf aufbewahren | 365 Tage | Aufbewahrung der Änderungshistorie |

Ein GitHub-Token legst du unter **Settings → Developer settings → Personal
access tokens** an. Das Token braucht **überhaupt keine Berechtigung** — GitHub gibt jedem
Token Lesezugriff auf öffentliche Repositories. Kreuze nichts an.

## Die Regeln

<img src="assets/rules.svg" alt="Wie der Wert entsteht: ein Repository startet bei 100, jede ausgelöste Regel zieht ihren Abzug ab, und die höchste ausgelöste Severity bestimmt den Status" width="100%">

Jedes Repository startet bei 100. Jede ausgelöste Regel zieht ihren Abzug ab.
Der **Status** ergibt sich nicht aus dem Wert, sondern aus der höchsten
ausgelösten Severity — sonst würden fünf harmlose Befunde ein archiviertes
Repository überstimmen.

| Regel | Standard-Schwelle | Severity | Abzug |
| --- | --- | --- | --- |
| Auf der HACS-Sicherheitsliste | — | Sicherheit | 100 |
| Repository gelöscht | — | Kritisch | 60 |
| Auf GitHub archiviert | — | Kritisch | 50 |
| Aus dem HACS-Store entfernt | — | Kritisch | 50 |
| Store-Repository der App weg | — | Kritisch | 50 |
| Kein Commit seit | 545 Tagen | Kritisch | 45 |
| App als veraltet gekennzeichnet | — | Kritisch | 45 |
| Kein Commit seit | 180 Tagen | Warnung | 20 |
| Neuestes Release älter als | 730 Tage | Warnung | 20 |
| App wird nicht mehr angeboten | — | Warnung | 20 |
| Verlangt neueres Home Assistant | — | Warnung | 15 |
| Neuestes Release älter als | 365 Tage | Info | 10 |
| Wird nirgends verwendet | — | Info | 10 |
| Mehr offene Issues als | 50 | Info | 5 |
| Weniger Sterne als | 5 | Info | 5 |
| Gar kein Release | — | Info | 5 |
| Nur Vorabversionen | — | Info | 5 |
| Update verfügbar | — | Info | 5 |
| Aus einem Branch installiert | — | Info | 5 |

Regeln mit zwei Stufen feuern nie beide: die härtere ersetzt die mildere. Regeln,
die nur für eine Art von Sache Sinn ergeben, sind darauf beschränkt — eine App
hat kein HACS-Release, also feuert *gar kein Release* dort nie.

Die Severities bestimmen über ihre Priorität den Status: ab 90 kritisch, ab 80
verwaist, ab 50 veraltet, darunter einen Blick wert. Du kannst sie umbenennen,
umfärben und jede Regel auf jede von ihnen zeigen lassen.

## Automatisierungsbeispiele

Auf ein kippendes Repository reagieren:

```yaml
automation:
  - alias: Melden, wenn eine Erweiterung verwaist
    triggers:
      - trigger: event
        event_type: integrationguard_status_changed
        event_data:
          status: abandoned
    actions:
      - action: notify.mobile_app_handy
        data:
          title: "{{ trigger.event.data.name }} sieht verwaist aus"
          message: "{{ trigger.event.data.url }}"
```

Auf eine ausgefallene Integration reagieren, ohne auf die Tagesprüfung zu warten:

```yaml
automation:
  - alias: Melden, wenn eine Integration neu angemeldet werden muss
    triggers:
      - trigger: event
        event_type: integrationguard_runtime_changed
    conditions:
      - condition: template
        value_template: "{{ trigger.event.data.state == 'reauth' }}"
    actions:
      - action: persistent_notification.create
        data:
          title: "{{ trigger.event.data.domain }} braucht Aufmerksamkeit"
          message: "{{ trigger.event.data.reason }}"
```

Eine wöchentliche Erinnerung an das, was herumliegt:

```yaml
automation:
  - alias: Sonntagsaufräumen
    triggers:
      - trigger: time
        at: "10:00:00"
    conditions:
      - condition: time
        weekday: [sun]
      - condition: numeric_state
        entity_id: sensor.integrationguard_ungenutzt
        above: 0
    actions:
      - action: notify.mobile_app_handy
        data:
          message: >-
            {{ states('sensor.integrationguard_ungenutzt') }} Erweiterungen sind
            installiert, aber ungenutzt:
            {{ state_attr('sensor.integrationguard_ungenutzt', 'repositories')
               | join(', ') }}
```

Verfügbare Events: `integrationguard_scan_completed`,
`integrationguard_status_changed`, `integrationguard_runtime_changed`.
Verfügbare Aktionen: `integrationguard.scan`, `.ignore`, `.unignore`,
`.mark_used`.

## Dashboard-Beispiel

<img src="assets/dashboard.svg" alt="Ein Lovelace-Mockup mit der IntegrationGuard-Karte, Wertering und Befundliste, daneben zwei Entitätskarten mit der Zahl ungenutzter Erweiterungen und der Laufzeitprobleme" width="100%">

```yaml
type: custom:integrationguard-card
title: Erweiterungen
max_items: 6
min_status: stale
show_score: true
show_runtime: true
```

| Option | Standard | Wirkung |
| --- | --- | --- |
| `title` | Name der Integration | Überschrift der Karte |
| `max_items` | `5` | Höchstens so viele Zeilen, dann „und N weitere" |
| `min_status` | `info` | Nur diesen Status und schlechtere zeigen |
| `show_score` | `true` | Der Wertering links |
| `show_runtime` | `true` | Laufzeitprobleme einbeziehen |

Die Karte hat einen grafischen Editor, tippen musst du davon nichts.

## Fehlerbehebung

**Alles leer, und die letzte Prüfung meldet `hacs: unavailable`.**
HACS ist nicht geladen. IntegrationGuard liest die Repositories aus der
laufenden HACS-Instanz; ohne sie gibt es nichts anzusehen. Das vorherige
Ergebnis bleibt stehen, statt durch ein leeres ersetzt zu werden.

**Repositories melden dauernd „warten auf GitHub".**
Ohne Token erlaubt GitHub 60 Anfragen pro Stunde. Neunzig Repositories brauchen
beim ersten Mal also ein paar Stunden, verteilt über mehrere Läufe. Jede Antwort
wird gespeichert, und ab dem zweiten Tag ist fast jede Anfrage eine konditionale,
die nicht gegen das Limit zählt. Ein Token nimmt das Warten weg.

**Eine Karte gilt als ungenutzt, obwohl ich sie benutze.**
Prüf, ob das Dashboard von einer Strategy gebaut wird — die entscheidet zur
Laufzeit und ist nicht auslesbar. Nimm im Repository-Detail **Als benutzt
markieren**, dann bleibt die Bewertung überschrieben.

**Das Panel taucht in der Seitenleiste nicht auf.**
Es ist standardmäßig nur für Administratoren sichtbar. Entweder als Administrator
anmelden oder den Panel-Zugriff in den Einstellungen auf „Alle" stellen.

**Eine Integration zeigt `not_loaded`, obwohl sie läuft.**
Das ist ein Config-Entry, der existiert, aber nicht geladen ist — meist ein
Überbleibsel einer entfernten Integration. Home Assistant zeigt ihn unter Geräte
& Dienste an.

## Häufige Fragen

### Schickt das meine Daten irgendwohin?

Nein. Zwei lesende Anfragen verlassen die Maschine: der öffentliche
HACS-Store-Index und GitHubs öffentliche API für Repositories, die du ohnehin
installiert hast. Kein Konto, keine Telemetrie, nichts über deine Entitäten oder
dein Zuhause.

### Brauche ich ein GitHub-Token?

Nein. Ohne Token bekommst du 60 Anfragen pro Stunde, was für eine tägliche
Prüfung reicht, sobald der erste Durchlauf durch ist. Mit Token sind es 5000,
und der erste Durchlauf dauert Minuten statt Stunden.

### Funktioniert es ohne HACS?

Nein. Die Repository-Liste kommt aus HACS. Apps auf Home Assistant OS werden vom
Supervisor gelesen und würden auch allein funktionieren, aber die Integration ist
darauf gebaut, dass HACS da ist.

### Löscht es irgendwas?

Nie. Es aktualisiert nichts, deinstalliert nichts und ändert nichts. Es liest,
bewertet und meldet.

### Warum meldet es bei meinem eigenen Repository „kaum Sterne"?

Weil es keine hat. Schalte die Regel *weniger Sterne als* ab oder setze die
Schwelle auf null — die sagt mehr über Beliebtheit als über den Zustand.

### Läuft es auf einer Home-Assistant-Container-Installation?

Ja, bis auf die Apps: die brauchen einen Supervisor, deshalb bleibt die Kategorie
auf Container- und Core-Installationen einfach leer.

### Woran unterscheidet es eine Karten-Bibliothek von einer ungenutzten Karte?

An gar keiner Liste. Lässt sich aus einem Bundle nichts Ansprechbares lesen,
lautet die Antwort „nicht bestimmbar". Bibliotheken werden auf andere Weise
benutzt und registrieren keinen Kartentyp, also landen sie von selbst dort.

### Kann ich ein einzelnes Repository stummschalten?

Ja, im Repository-Detail oder über `integrationguard.ignore`, auf Wunsch nur für
eine Weile. Ein ignoriertes Repository zählt nirgends mit.

## Was es bewusst nicht macht

- **Kein Aktualisieren.** Das ist HACS' Aufgabe.
- **Kein Deinstallieren.** Es zeigt an, es räumt nicht auf.
- **Keine Bewertung von Core-Integrationen.** Nur was über HACS kam, plus Apps.
- **Keine Entitätsüberwachung.** Ob ein Gerät antwortet, ist eine andere Frage —
  dafür gibt es [StateGuard](https://github.com/sphings79/stateguard-home-assistant).

## Credits

**[HACS](https://hacs.xyz)** von [Joakim Sørensen](https://github.com/ludeeus)
und den Mitwirkenden. IntegrationGuard liest die Repositories aus der laufenden
HACS-Instanz und nutzt den öffentlichen Store-Index unter `data-v2.hacs.xyz` —
dieselben Daten, die HACS selbst holt. Quellcode:
[hacs/integration](https://github.com/hacs/integration). HACS ist freie Software
und nimmt [Spenden](https://github.com/sponsors/ludeeus) entgegen.

**[GitHub](https://github.com)** für die öffentliche Repository-API.
Standardmäßig ohne Anmeldung genutzt, innerhalb der dokumentierten
[Rate-Limits](https://docs.github.com/rest/using-the-rest-api/rate-limits-for-the-rest-api).

Keines der beiden Projekte ist an diesem hier beteiligt.

## Haftungsausschluss

Inoffiziell und von der Community gebaut. Nicht verbunden mit, unterstützt von
oder betreut durch das Home-Assistant-Projekt, Nabu Casa, HACS oder GitHub.
„Home Assistant" ist eine Marke des Home-Assistant-Projekts.

Ein Urteil wie *verwaist* oder *ungenutzt* ist ein Hinweis, keine Tatsache. Schau
nach, bevor du etwas entfernst.

## Mitmachen

Issues und Pull Requests gern unter
[sphings79/integrationguard-home-assistant](https://github.com/sphings79/integrationguard-home-assistant).
Vor dem Push:

```bash
ruff format . && ruff check . && pytest
```

Für das Frontend:

```bash
cd frontend && npm ci && npx tsc --noEmit && npm run build
```

Das gebaute Bundle liegt im Repository — HACS führt keinen Build aus — und die
CI prüft, dass es zum Quellcode passt.

## Lizenz

MIT, siehe [LICENSE](LICENSE), Attribution in [NOTICE](NOTICE).

---

<sub>Home Assistant HACS Zustand prüfen · ungenutzte HACS-Integrationen finden · ungenutzte Lovelace-Karten finden · verwaiste Custom Components erkennen · HACS Repository Wartungsstatus · ungenutzte Custom Cards Home Assistant · Home Assistant Add-on Zustand · HACS aufräumen · Custom Integration nicht mehr gepflegt · Home Assistant Reparaturmeldungen</sub>
