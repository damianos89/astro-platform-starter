# AutoTrader – Expert Advisor für MetaTrader 5

Regelbasierter EA, der Trendwechsel erkennt, innerhalb eines festen Budgets selbst Positionen eröffnet und schließt und dich per Push in der MT5-App auf dem Handy informiert.

> **Wichtig:** Das ist keine KI und keine Gewinngarantie. Der EA folgt festen, nachvollziehbaren Regeln. Ob diese Regeln auf deinem Markt Geld verdienen, zeigt erst der Test. Reihenfolge: **Backtest → Demokonto (1–3 Monate) → kleines Echtgeld**.

## Was der EA tut

| Baustein | Verhalten |
|---|---|
| **Einstieg LONG** | EMA 20 kreuzt EMA 50 nach oben, Kurs über EMA 200 (Aufwärtstrend), RSI > 50 |
| **Einstieg SHORT** | EMA 20 kreuzt EMA 50 nach unten, Kurs unter EMA 200, RSI < 50 |
| **Stop-Loss / Take-Profit** | 2 × ATR / 3 × ATR (passt sich der aktuellen Schwankung an) |
| **Nachziehender Stop** | ab Gewinn: 1,5 × ATR hinter dem Kurs |
| **Ausstieg** | Stop-Loss, Take-Profit, nachgezogener Stop oder Gegensignal |
| **Positionsgröße** | so berechnet, dass ein Stop-Loss genau `RisikoProTrade` kostet |
| **Budget** | Verlust ≥ `Budget` → alle EA-Positionen zu, EA stoppt endgültig |
| **Tageslimit** | Verlust ≥ `MaxTagesverlust` an einem Tag → Positionen zu, Pause bis morgen |
| **Filter** | nur zu Handelszeiten, nicht bei zu hohem Spread, max. Anzahl Positionen |
| **Benachrichtigung** | Push bei Signal, Eröffnung, Schließung, Limit, Fehler |

Alle Werte sind im MetaTrader unter „Eingaben“ änderbar – ohne Programmieren.

**Modus:**
- `Nur Signal aufs Handy` (Standard): handelt nicht, schickt dir Einstieg, SL, TP und empfohlene Lotgröße.
- `Automatisch handeln`: eröffnet und schließt selbst. Mit `NurDemokonto = true` (Standard) verweigert der EA den Automatikhandel auf einem Echtgeldkonto.

## Einrichtung

### 1. MetaTrader 5 Desktop (Windows) installieren
Die Handy-App kann keine EAs ausführen. Du brauchst das Desktop-Terminal deines Brokers – auf einem PC, der dauerhaft läuft, oder auf einem VPS (siehe Schritt 6). Dort mit deinen Broker-Zugangsdaten einloggen, **zuerst mit einem Demokonto** (Datei → Konto eröffnen → Demo).

### 2. EA einfügen und kompilieren
1. Im MT5: **Datei → Dateiordner öffnen** → `MQL5\Experts`
2. `AutoTrader.mq5` dort hineinkopieren.
3. Im MT5: **Extras → MetaQuotes Language Editor** (F4) → Datei `AutoTrader.mq5` öffnen → **Kompilieren** (F7). Es dürfen keine Fehler erscheinen. Falls doch: Fehlermeldung an mich schicken.

### 3. Push aufs Handy einrichten
1. MT5-App auf dem Handy → **Einstellungen → Nachrichten** → **MetaQuotes ID** notieren.
2. Desktop-MT5 → **Extras → Optionen → Benachrichtigungen** → „Push-Benachrichtigungen aktivieren“ anhaken, MetaQuotes ID eintragen → **Test** drücken.

### 4. Backtest (Pflicht vor dem Livebetrieb)
1. **Ansicht → Strategietester** (Strg+R).
2. Expert: `AutoTrader`, Symbol z. B. `EURUSD`, Zeitraum mindestens 3 Jahre, Modell **„Jeder Tick basierend auf echten Ticks“**.
3. Starten, dann Reiter **Backtest** prüfen: Nettogewinn, maximaler Drawdown, Anzahl Trades, Profitfaktor.
   - Profitfaktor < 1,2 oder < 100 Trades → nicht live handeln.
   - Gute Werte in einem Zeitraum allein beweisen nichts. Gegenprobe auf einem anderen Zeitraum.

### 5. Auf Chart starten
1. Chart des Symbols öffnen (Zeitrahmen egal, der EA nutzt `Zeitrahmen` aus den Eingaben).
2. `AutoTrader` aus dem Navigator auf den Chart ziehen → Reiter **Eingaben** anpassen → **Allgemein:** „Algo Trading erlauben“ anhaken.
3. Oben in der Symbolleiste **Algo Trading** einschalten (grün).
4. Im Reiter **Experten** unten steht „AutoTrader gestartet …“, gleichzeitig kommt eine Push-Nachricht.

### 6. Dauerbetrieb (VPS)
Einfachste Variante: Rechtsklick auf das Konto im Navigator → **Virtuellen Server registrieren** (MQL5-VPS, ca. 10–15 $/Monat). Danach Chart mit EA → **Migration**. Der EA läuft dann auch, wenn dein PC aus ist.

## Empfohlene Startwerte

| Eingabe | Demo | Erstes Echtgeld |
|---|---|---|
| `Budget` | 500 | was du **komplett verlieren kannst** |
| `RisikoProTrade` | 10 | 1–2 % des Budgets |
| `MaxTagesverlust` | 100 | 3–5 × `RisikoProTrade` |
| `MaxPositionen` | 1 | 1 |

## Wichtige Hinweise

- **Budget zählt das ganze Konto:** Der EA misst Verluste am Kontostand (Equity) seit dem Start. Handelst du auf demselben Konto zusätzlich von Hand, zählen deine Verluste mit. Für saubere Kontrolle ein eigenes Konto für den EA nutzen.
- **Budget zurücksetzen:** Nach einem Budget-Stopp handelt der EA nicht mehr, auch nicht nach Neustart. Bewusster Neustart nur über `BudgetNeuStarten = true` (danach wieder auf `false`).
- **Mehrere Märkte:** EA auf mehrere Charts ziehen ist möglich, dann pro Chart eine andere `MagicNumber` verwenden. Das Budget gilt pro Chart, das Kontorisiko addiert sich.
- **Gaps und Wochenende:** Ein Stop-Loss schützt nicht vor Kurslücken. Der tatsächliche Verlust kann höher sein als `RisikoProTrade`.
- **Push-Limit:** MetaTrader erlaubt max. 2 Nachrichten pro Sekunde und 10 pro Minute.
