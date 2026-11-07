Du hilfst mir, einen automatischen Handelsroboter (Expert Advisor) für MetaTrader 5 auf einem gemieteten Windows-Server (VPS) einzurichten. Ich kann nicht programmieren. Arbeite Schritt für Schritt, erkläre kurz, was du tust, und frage mich, bevor du etwas abschließt.

## Ziel
Auf einem Windows-VPS läuft MetaTrader 5 rund um die Uhr, eingeloggt in mein DEMO-Konto. Darauf läuft der Expert Advisor „AutoTrader“, der selbständig Positionen eröffnet und schließt. Ich verfolge alles in der MetaTrader-5-App auf meinem Android-Handy und bekomme Push-Nachrichten.

## Feste Regeln
1. Nur Demokonto. Niemals ein Echtgeldkonto einloggen oder einrichten.
2. Du führst selbst keine Trades aus und klickst nie auf Kaufen/Verkaufen. Das macht ausschließlich der Expert Advisor.
3. Zahlungsdaten, Passwörter und Zugangsdaten gebe ich selbst ein. Halte an diesen Stellen an und sag mir genau, was ich eintragen soll.
4. Keine Bestellung, kein Kauf und kein Abo ohne meine ausdrückliche Bestätigung im Chat.
5. Lade nur Software von den unten genannten Quellen herunter.
6. Wenn etwas anders aussieht als erwartet: anhalten, Screenshot beschreiben, mich fragen.

## Schritt 1 – VPS-Anbieter vergleichen (nur recherchieren)
Vergleiche in Chrome 3 Angebote für einen Windows-VPS, geeignet für MetaTrader 5 (z. B. ForexVPS.net, Contabo Windows VPS, IONOS Windows Server):
- Windows Server, mind. 2 GB RAM, Standort Europa (Frankfurt/London/Amsterdam)
- monatlich kündbar
- Preis pro Monat inkl. Windows-Lizenz und MwSt.
Zeig mir eine kurze Tabelle mit Empfehlung. Dann warte, bis ich einen auswähle und selbst bestelle und bezahle.

## Schritt 2 – Verbindung zum VPS
Nach meiner Bestellung bekomme ich IP-Adresse, Benutzername und Passwort per E-Mail. Richte auf diesem Computer eine Remotedesktop-Verbindung zum VPS ein (Windows: „Remotedesktopverbindung“; Mac: „Windows App“ von Microsoft). Das Passwort gebe ich selbst ein.

## Schritt 3 – MetaTrader 5 auf dem VPS
Auf dem VPS:
1. MetaTrader 5 von https://www.metatrader5.com herunterladen und installieren.
2. Datei → Bei Handelskonto anmelden. Login, Passwort und Server meines DEMO-Kontos trage ich selbst ein (stehen in der Android-App unter Menü → Konten verwalten).
3. Prüfen: unten rechts besteht eine Verbindung, und das Konto ist ein Demokonto.

## Schritt 4 – Expert Advisor einfügen
Auf dem VPS:
1. Diese Datei herunterladen und als `AutoTrader.mq5` speichern:
   https://raw.githubusercontent.com/damianos89/astro-platform-starter/claude/mobile-apps-development-kos8aq/metatrader/AutoTrader.mq5
2. In MetaTrader: Datei → Dateiordner öffnen → MQL5 → Experts. Datei dorthin kopieren.
3. F4 (MetaEditor) → AutoTrader.mq5 öffnen → Kompilieren (F7).
4. Ergebnis muss „0 errors“ sein. Bei Fehlern NICHTS am Code ändern – kopiere mir die komplette Fehlerliste wörtlich, ich gebe sie an den Entwickler weiter.

## Schritt 5 – Expert Advisor starten
1. Datei → Neuer Chart → EURUSD.
2. AutoTrader aus dem Navigator (Expert Advisors) auf den Chart ziehen.
3. Reiter „Allgemein“: „Algo Trading erlauben“ anhaken. Reiter „Eingaben“: nichts ändern. OK.
4. Knopf „Algo Trading“ in der Symbolleiste einschalten (grün).
5. Prüfen: oben rechts im Chart „AutoTrader“ mit blauem Hut; Reiter „Experten“ zeigt „AutoTrader gestartet | AUTO …“. Steht dort „NUR SIGNAL“ oder „Echtgeldkonto erkannt“, anhalten und mir melden.

## Schritt 6 – Push-Nachrichten
1. Ich lese dir meine MetaQuotes ID aus der Android-App vor (Menü → Nachrichten).
2. In MetaTrader: Extras → Optionen → Benachrichtigungen → „Push-Benachrichtigungen aktivieren“, ID eintragen, „Test“ klicken. Ich bestätige dir, ob die Nachricht angekommen ist.

## Schritt 7 – Dauerbetrieb
1. MetaTrader in den Autostart: Windows+R → `shell:startup` → Verknüpfung von MetaTrader 5 hineinlegen.
2. Remotedesktop nur TRENNEN (Fenster schließen), den VPS NICHT abmelden und NICHT herunterfahren.

## Abschluss
Gib mir eine kurze Zusammenfassung:
- VPS-Anbieter, IP-Adresse, monatliche Kosten (keine Passwörter aufschreiben)
- Kontonummer und Server des Demokontos
- Ergebnis Kompilieren, Status Expert Advisor, Push-Test
- alles, was nicht geklappt hat, mit genauer Fehlermeldung
