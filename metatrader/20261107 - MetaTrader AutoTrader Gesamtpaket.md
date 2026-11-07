# MetaTrader 5 AutoTrader – Gesamtpaket

Stand: 07.11.2026 · Alles in einer Datei: Erklärung, Einrichtung Schritt für Schritt, Cowork-Prompt und vollständiger Programmcode.

---

## 0. Hinweis für Claude (wenn diese Datei in einen neuen Chat geladen wird)

Diese Datei setzt ein früheres Gespräch fort. Bitte so weitermachen:

- **Nutzer:** kein Programmierer, hat ein **MetaTrader-5-Demokonto** und ein **Android-Handy**. Ziel: ein Programm, das im Hintergrund selbständig Positionen öffnet und schließt – vorerst nur im Demokonto – und ihn per Push in der MT5-App informiert.
- **Lösung:** Expert Advisor `AutoTrader.mq5` (Abschnitt 6) auf einem gemieteten **Windows-VPS**, eingerichtet vom Handy per Microsoft „Windows App“ (Abschnitt 3) oder per Cowork (Abschnitt 4).
- **Technische Grenzen (bereits erklärt):** Die MT5-Android-App kann keine Expert Advisors ausführen. Claude bedient die MT5-App nicht und führt keine Trades per Klick aus – das macht ausschließlich der Expert Advisor.
- **Stand:** Code geschrieben, **noch nie in MetaEditor kompiliert**. Erster Kompilierlauf steht aus. Bei Fehlern: Fehlerliste vom Nutzer anfordern und Code korrigieren.
- **Regeln:** nur Demokonto (der EA sperrt Echtgeld selbst über `NurDemokonto = true`), keine Gewinnversprechen, Zugangsdaten und Zahlungen gibt der Nutzer selbst ein. Schritt für Schritt erklären, einfache Sprache.
- **Offene Fragen an den Nutzer:** welcher Markt (Standard EURUSD), welcher Zeitrahmen (Standard H1), hat er eigene Handelsregeln?

---

## 1. Was das ist – kurz erklärt

- **AutoTrader** ist ein kleines Programm für MetaTrader 5. Es beobachtet den Markt, erkennt nach festen Regeln Trendwechsel und **öffnet und schließt Positionen selbst**.
- Es läuft **nicht auf dem Handy**, sondern auf einem gemieteten Windows-Computer im Internet (VPS, ca. 10–25 €/Monat), Tag und Nacht.
- Du siehst jeden Deal in deiner **MT5-App auf dem Android-Handy** und bekommst eine **Push-Nachricht**.
- **Echtes Geld ist gesperrt.** Auf einem Echtgeldkonto weigert sich das Programm zu handeln.
- **Keine Gewinngarantie.** Die Regeln sind ein Startpunkt zum Testen. Erst Demokonto (1–3 Monate), dann entscheiden.

### Die Regeln des Programms

| Baustein | Verhalten |
|---|---|
| Einstieg LONG | EMA 20 kreuzt EMA 50 nach oben, Kurs über EMA 200, RSI > 50 |
| Einstieg SHORT | EMA 20 kreuzt EMA 50 nach unten, Kurs unter EMA 200, RSI < 50 |
| Stop-Loss / Take-Profit | 2 × ATR / 3 × ATR (passt sich der Schwankung an) |
| Nachziehender Stop | ab Gewinn: 1,5 × ATR hinter dem Kurs |
| Ausstieg | Stop-Loss, Take-Profit, nachgezogener Stop oder Gegensignal |
| Positionsgröße | so berechnet, dass ein Stop-Loss genau `RisikoProTrade` kostet |
| Budget | Verlust ≥ `Budget` → alle Positionen zu, Programm stoppt endgültig |
| Tageslimit | Verlust ≥ `MaxTagesverlust` an einem Tag → Positionen zu, Pause bis morgen |
| Filter | nur zu Handelszeiten (8–20 Uhr Serverzeit), nicht bei hohem Spread, max. 1 Position |

**Voreinstellung:** automatischer Handel, 10 € Risiko pro Trade, max. 100 € Verlust pro Tag, max. 500 € Verlust insgesamt, EURUSD auf Stundenkerzen (H1). Es kann Tage ohne Trade geben – das ist normal.

---

## 2. Welcher Weg?

- **Nur Android-Handy, kein Computer** → Abschnitt 3 (alles vom Handy aus).
- **Computer mit Claude-Desktop-App (Cowork) vorhanden** → Abschnitt 4 (Cowork erledigt das meiste, du gibst nur Passwörter ein und bezahlst).

---

## 3. Einrichtung nur mit dem Android-Handy

### Teil A – Windows-Server mieten (ca. 15 Min.)

1. Anbieter mit „Forex VPS“ oder „Windows VPS“ wählen, z. B. ForexVPS.net, Contabo (Windows VPS), IONOS (Windows Server). Preise selbst prüfen. Wichtig: **Windows Server**, mind. **2 GB RAM**, Standort **Europa**, monatlich kündbar.
2. Bestellen. Per E-Mail kommen **IP-Adresse**, **Benutzername** (meist `Administrator`) und **Passwort**. Aufschreiben.

### Teil B – Vom Handy auf den Server (ca. 5 Min.)

3. Im **Play Store** die App **„Windows App“** von Microsoft installieren (früher „Remotedesktop“).
4. App öffnen → **„+“** → **„PC hinzufügen“** → bei **PC-Name** die IP-Adresse eintragen → Benutzername und Passwort eintragen → speichern.
5. Eintrag antippen → **Verbinden** → Zertifikatswarnung mit **„Verbinden“** bestätigen.
6. Du siehst jetzt Windows auf dem Handy. Handy **quer** halten. Tippen = Mausklick, Tastatur über das Tastatur-Symbol oben.

### Teil C – MetaTrader auf dem Server (ca. 10 Min.)

7. Auf dem Server **Edge** öffnen → **metatrader5.com** → **Download** → Datei öffnen → **Weiter** → **Fertig stellen**.
8. Zugangsdaten nachsehen – auf dem **Handy** in der MT5-App: **☰ Menü → Konten verwalten** → Konto antippen. Dort stehen **Login** (Kontonummer) und **Server**. Passwort = das, mit dem du dich in der App angemeldet hast.
9. In MetaTrader auf dem Server: **Datei → Bei Handelskonto anmelden** → Login, Passwort, Server → **OK**. Unten rechts darf nicht „Keine Verbindung“ stehen.

### Teil D – Programm einfügen (ca. 5 Min.)

10. Auf dem Server in Edge diesen Link öffnen (auf dem Handy kopieren, auf dem Server in die Adresszeile einfügen):
    `https://raw.githubusercontent.com/damianos89/astro-platform-starter/claude/mobile-apps-development-kos8aq/metatrader/AutoTrader.mq5`
    Es erscheint Text → **Strg+S** → Dateiname `AutoTrader.mq5`, Dateityp **„Alle Dateien“** → auf dem **Desktop** speichern.
    *Falls der Link nicht geht:* **Editor** (Notepad) öffnen, den kompletten Code aus **Abschnitt 6** hineinkopieren, **Datei → Speichern unter** → Dateityp **„Alle Dateien“**, Name `AutoTrader.mq5`, Codierung **UTF-8** → Desktop.
11. In MetaTrader: **Datei → Dateiordner öffnen** → **MQL5** → **Experts** → Datei vom Desktop hineinziehen.
12. In MetaTrader **F4** (Editor öffnet sich) → links unter **Experts** **AutoTrader** doppelt antippen → oben **Kompilieren** (oder F7). Unten muss **„0 errors“** stehen. Sonst: Screenshot der Fehlerliste an Claude. Editor schließen.

### Teil E – Programm starten (ca. 3 Min.)

13. **Datei → Neuer Chart → EURUSD**.
14. Links im **Navigator** unter **Expert Advisors** **AutoTrader** auf den Chart ziehen.
15. Reiter **Allgemein**: Haken bei **„Algo Trading erlauben“** → **OK**.
16. Oben in der Leiste **„Algo Trading“** antippen, bis er **grün** ist.
17. Kontrolle: oben rechts im Chart **AutoTrader** mit **blauem Hut** (grau = etwas ist aus). Unten im Reiter **Experten**: „AutoTrader gestartet | AUTO …“.

### Teil F – Nachrichten aufs Handy (ca. 3 Min.)

18. **Handy**, MT5-App: **☰ Menü → Nachrichten** → oben steht die **MetaQuotes ID** (8 Zeichen).
19. **Server**, MetaTrader: **Extras → Optionen → Benachrichtigungen** → Haken **Push-Benachrichtigungen aktivieren** → ID eintragen → **Test**. Auf dem Handy muss eine Nachricht ankommen → **OK**.

### Teil G – Laufen lassen

20. Server **nicht herunterfahren, nicht abmelden**. Nur die Windows App auf dem Handy schließen (= Verbindung trennen). MetaTrader läuft weiter.
21. Autostart nach Windows-Neustart: auf dem Server **Windows-Taste + R** → `shell:startup` → **OK** → MetaTrader-Symbol vom Desktop in diesen Ordner ziehen.

### Danach

- Deals siehst du in der Android-App unter **Handel** und **Verlauf**.
- Eingreifen jederzeit möglich: Trade in der App von Hand schließen oder auf dem Server **„Algo Trading“** ausschalten.

---

## 4. Einrichtung mit Cowork (Claude-Desktop-App auf einem Computer)

Den folgenden Block komplett kopieren und in Cowork einfügen. Diese Datei als Anhang mitgeben, damit Cowork den Code aus Abschnitt 6 hat.

```text
Du hilfst mir, einen automatischen Handelsroboter (Expert Advisor) für MetaTrader 5 auf einem gemieteten Windows-Server (VPS) einzurichten. Ich kann nicht programmieren. Arbeite Schritt für Schritt, erkläre kurz, was du tust, und frage mich, bevor du etwas abschließt. Die angehängte Datei „MetaTrader AutoTrader Gesamtpaket“ enthält in Abschnitt 6 den vollständigen Programmcode.

ZIEL
Auf einem Windows-VPS läuft MetaTrader 5 rund um die Uhr, eingeloggt in mein DEMO-Konto. Darauf läuft der Expert Advisor „AutoTrader“, der selbständig Positionen eröffnet und schließt. Ich verfolge alles in der MT5-App auf meinem Android-Handy und bekomme Push-Nachrichten.

FESTE REGELN
1. Nur Demokonto. Niemals ein Echtgeldkonto einloggen oder einrichten.
2. Du führst selbst keine Trades aus und klickst nie auf Kaufen/Verkaufen. Das macht ausschließlich der Expert Advisor.
3. Zahlungsdaten, Passwörter und Zugangsdaten gebe ich selbst ein. Halte dort an und sag mir genau, was ich eintragen soll.
4. Keine Bestellung, kein Kauf, kein Abo ohne meine ausdrückliche Bestätigung im Chat.
5. Software nur von metatrader5.com bzw. der Seite des gewählten VPS-Anbieters.
6. Wenn etwas anders aussieht als erwartet: anhalten, beschreiben, mich fragen.

SCHRITT 1 – VPS-Anbieter vergleichen (nur recherchieren)
Vergleiche in Chrome 3 Angebote für einen Windows-VPS für MetaTrader 5 (z. B. ForexVPS.net, Contabo Windows VPS, IONOS Windows Server): Windows Server, mind. 2 GB RAM, Standort Europa, monatlich kündbar, Preis pro Monat inkl. Windows-Lizenz und MwSt. Zeig mir eine kurze Tabelle mit Empfehlung. Dann warte, bis ich auswähle und selbst bestelle und bezahle.

SCHRITT 2 – Verbindung zum VPS
Ich bekomme IP-Adresse, Benutzername und Passwort per E-Mail. Richte eine Remotedesktop-Verbindung ein (Windows: „Remotedesktopverbindung“, Mac: „Windows App“ von Microsoft). Das Passwort gebe ich selbst ein.

SCHRITT 3 – MetaTrader 5 auf dem VPS
1. MetaTrader 5 von https://www.metatrader5.com herunterladen und installieren.
2. Datei → Bei Handelskonto anmelden. Login, Passwort und Server meines DEMO-Kontos trage ich selbst ein.
3. Prüfen: Verbindung steht, Konto ist ein Demokonto.

SCHRITT 4 – Expert Advisor einfügen
1. Auf dem VPS die Datei AutoTrader.mq5 anlegen – entweder herunterladen von
   https://raw.githubusercontent.com/damianos89/astro-platform-starter/claude/mobile-apps-development-kos8aq/metatrader/AutoTrader.mq5
   (beim Speichern Dateityp „Alle Dateien“, damit kein .txt angehängt wird)
   oder den Code aus Abschnitt 6 der angehängten Datei unverändert in den Windows-Editor kopieren und als AutoTrader.mq5 (UTF-8, Dateityp „Alle Dateien“) speichern.
2. In MetaTrader: Datei → Dateiordner öffnen → MQL5 → Experts. Datei dorthin kopieren.
3. F4 (MetaEditor) → AutoTrader.mq5 öffnen → Kompilieren (F7).
4. Ergebnis muss „0 errors“ sein. Bei Fehlern NICHTS am Code ändern – kopiere mir die komplette Fehlerliste wörtlich.

SCHRITT 5 – Expert Advisor starten
1. Datei → Neuer Chart → EURUSD.
2. AutoTrader aus dem Navigator (Expert Advisors) auf den Chart ziehen.
3. Reiter „Allgemein“: „Algo Trading erlauben“ anhaken. Reiter „Eingaben“: nichts ändern. OK.
4. Knopf „Algo Trading“ in der Symbolleiste einschalten (grün).
5. Prüfen: oben rechts im Chart „AutoTrader“ mit blauem Hut; Reiter „Experten“ zeigt „AutoTrader gestartet | AUTO …“. Steht dort „NUR SIGNAL“ oder „Echtgeldkonto erkannt“: anhalten und melden.

SCHRITT 6 – Push-Nachrichten
1. Ich lese dir meine MetaQuotes ID aus der Android-App vor (Menü → Nachrichten).
2. In MetaTrader: Extras → Optionen → Benachrichtigungen → „Push-Benachrichtigungen aktivieren“, ID eintragen, „Test“. Ich bestätige, ob die Nachricht ankam.

SCHRITT 7 – Dauerbetrieb
1. MetaTrader in den Autostart: Windows+R → shell:startup → Verknüpfung von MetaTrader 5 hineinlegen.
2. Remotedesktop nur TRENNEN (Fenster schließen), den VPS NICHT abmelden und NICHT herunterfahren.

ABSCHLUSS
Kurze Zusammenfassung: VPS-Anbieter, IP-Adresse, Kosten pro Monat (keine Passwörter aufschreiben); Kontonummer und Server des Demokontos; Ergebnis Kompilieren, Status Expert Advisor, Push-Test; alles, was nicht geklappt hat, mit genauer Fehlermeldung.
```

---

## 5. Einstellungen und Hinweise

Alle Werte sind in MetaTrader änderbar: Rechtsklick auf den Chart → **Expertenliste** bzw. Doppelklick auf den Hut → Reiter **Eingaben**.

| Eingabe | Standard | Bedeutung |
|---|---|---|
| `Modus` | Automatisch handeln | oder „Nur Signal aufs Handy“ (handelt nicht, schickt nur Vorschläge) |
| `NurDemokonto` | true | sperrt Automatik auf Echtgeldkonten |
| `Zeitrahmen` | H1 | Kerzen, die ausgewertet werden |
| `Budget` | 500 | max. Gesamtverlust, danach endgültiger Stopp |
| `MaxTagesverlust` | 100 | max. Verlust pro Tag, danach Pause bis morgen |
| `RisikoProTrade` | 10 | Verlust je Trade, falls der Stop-Loss greift |
| `MaxPositionen` | 1 | gleichzeitig offene Positionen |
| `MaxSpreadPunkte` | 30 | kein Einstieg bei höherem Spread |
| `BudgetNeuStarten` | false | einmal auf true = Budget-Zähler zurücksetzen, danach wieder false |
| `StartStunde` / `EndStunde` | 8 / 20 | Einstiege nur in diesem Zeitfenster (Serverzeit des Brokers) |

**Wichtig:**
- Das Budget zählt das **ganze Konto**. Handelst du auf demselben Konto zusätzlich von Hand, zählen diese Verluste mit.
- Ein Stop-Loss schützt nicht vor **Kurslücken** (z. B. übers Wochenende). Der Verlust kann dann höher sein als `RisikoProTrade`.
- Mehrere Märkte: Programm auf mehrere Charts ziehen, pro Chart eine andere `MagicNumber`.
- MetaTrader erlaubt max. **10 Push-Nachrichten pro Minute**.

---

## 6. Programmcode `AutoTrader.mq5`

Unverändert kopieren, von `//+---` bis zur letzten Zeile.

```cpp
//+------------------------------------------------------------------+
//| AutoTrader.mq5                                                    |
//| Regelbasierter Expert Advisor für MetaTrader 5:                   |
//|  - erkennt Trendwechsel (EMA-Kreuzung + Trendfilter + RSI)        |
//|  - eröffnet/schließt Positionen selbst (Modus AUTO)               |
//|    oder schickt nur Push-Signale aufs Handy (Modus NUR_SIGNAL)     |
//|  - hält ein festes Budget, ein Tagesverlust-Limit und ein          |
//|    Risiko pro Trade ein                                            |
//| WICHTIG: Die Strategie ist ein Startpunkt zum Testen, keine        |
//| Gewinngarantie. Erst Backtest, dann Demokonto, dann Echtgeld.      |
//+------------------------------------------------------------------+
#property version   "1.00"
#property description "Regelbasierter EA mit Budget-Grenzen und Push-Benachrichtigung"

#include <Trade\Trade.mqh>

enum ENUM_MODUS
  {
   MODUS_NUR_SIGNAL = 0, // Nur Signal aufs Handy
   MODUS_AUTO       = 1  // Automatisch handeln
  };

input group "Betrieb"
input ENUM_MODUS      Modus           = MODUS_AUTO;       // Modus
input bool            NurDemokonto    = true;             // Automatik nur auf Demokonto erlauben
input ENUM_TIMEFRAMES Zeitrahmen      = PERIOD_H1;        // Zeitrahmen der Auswertung
input long            MagicNumber     = 260711;           // Kennung der EA-Positionen
input bool            PushNachrichten = true;             // Push an MT5-App senden

input group "Budget und Risiko (Kontowährung)"
input double Budget            = 500.0; // Max. Gesamtverlust, danach stoppt der EA endgültig
input double MaxTagesverlust   = 100.0; // Max. Verlust pro Tag, danach Pause bis morgen (0 = aus)
input double RisikoProTrade    = 10.0;  // Verlust je Trade, falls Stop-Loss greift
input int    MaxPositionen     = 1;     // Max. gleichzeitig offene Positionen
input int    MaxSpreadPunkte   = 30;    // Kein Einstieg bei größerem Spread (0 = aus)
input bool   BudgetNeuStarten  = false; // Budget-Zähler beim Start zurücksetzen

input group "Strategie"
input int    EMA_Schnell              = 20;   // Schnelle EMA
input int    EMA_Langsam              = 50;   // Langsame EMA
input int    EMA_Trend                = 200;  // Trendfilter-EMA
input int    RSI_Periode              = 14;   // RSI-Periode
input double RSI_LongMin              = 50.0; // Long nur wenn RSI darüber
input double RSI_ShortMax             = 50.0; // Short nur wenn RSI darunter
input int    ATR_Periode              = 14;   // ATR-Periode
input double SL_ATR                   = 2.0;  // Stop-Loss = ATR x Faktor
input double TP_ATR                   = 3.0;  // Take-Profit = ATR x Faktor (0 = aus)
input double Trailing_ATR             = 1.5;  // Nachziehender Stop = ATR x Faktor (0 = aus)
input bool   SchliessenBeiGegensignal = true; // Position bei Gegensignal schließen

input group "Handelszeiten (Serverzeit des Brokers)"
input int StartStunde = 8;  // Einstiege ab Stunde
input int EndStunde   = 20; // Einstiege bis Stunde (gleich Start = immer)

CTrade          trade;
ENUM_TIMEFRAMES tf;
int             hSchnell, hLangsam, hTrend, hRsi, hAtr;
datetime        letzteKerze = 0;
double          letzterAtr  = 0;
bool            autoErlaubt = false;
string          gvStart, gvGestoppt, gvTag, gvTagStart, gvTagGestoppt;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(EMA_Schnell >= EMA_Langsam || Budget <= 0 || RisikoProTrade <= 0 || SL_ATR <= 0)
     {
      Print("Ungültige Einstellungen: EMA_Schnell < EMA_Langsam, Budget, RisikoProTrade und SL_ATR > 0 erforderlich.");
      return INIT_PARAMETERS_INCORRECT;
     }

   tf = (Zeitrahmen == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : Zeitrahmen;

   hSchnell = iMA(_Symbol, tf, EMA_Schnell, 0, MODE_EMA, PRICE_CLOSE);
   hLangsam = iMA(_Symbol, tf, EMA_Langsam, 0, MODE_EMA, PRICE_CLOSE);
   hTrend   = iMA(_Symbol, tf, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE);
   hRsi     = iRSI(_Symbol, tf, RSI_Periode, PRICE_CLOSE);
   hAtr     = iATR(_Symbol, tf, ATR_Periode);
   if(hSchnell == INVALID_HANDLE || hLangsam == INVALID_HANDLE || hTrend == INVALID_HANDLE ||
      hRsi == INVALID_HANDLE || hAtr == INVALID_HANDLE)
     {
      Print("Indikatoren konnten nicht geladen werden.");
      return INIT_FAILED;
     }

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(20);

   string p = "AT_" + _Symbol + "_" + IntegerToString(MagicNumber) + "_";
   gvStart       = p + "Start";
   gvGestoppt    = p + "Gestoppt";
   gvTag         = p + "Tag";
   gvTagStart    = p + "TagStart";
   gvTagGestoppt = p + "TagGestoppt";

   bool tester = (bool)MQLInfoInteger(MQL_TESTER);
   if(BudgetNeuStarten || tester || !GlobalVariableCheck(gvStart))
     {
      GlobalVariableSet(gvStart, AccountInfoDouble(ACCOUNT_EQUITY));
      GlobalVariableSet(gvGestoppt, 0);
      GlobalVariableSet(gvTag, 0);
     }

   autoErlaubt = (Modus == MODUS_AUTO);
   if(autoErlaubt && NurDemokonto &&
      AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
     {
      autoErlaubt = false;
      Melden("Echtgeldkonto erkannt – Automatik gesperrt (NurDemokonto = true). Läuft nur mit Signalen.");
     }

   Melden(StringFormat("gestartet | %s | %s | Budget %.2f, Rest %.2f %s",
                       autoErlaubt ? "AUTO" : "NUR SIGNAL", TfText(),
                       Budget, RestBudget(), AccountInfoString(ACCOUNT_CURRENCY)));
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   IndicatorRelease(hSchnell);
   IndicatorRelease(hLangsam);
   IndicatorRelease(hTrend);
   IndicatorRelease(hRsi);
   IndicatorRelease(hAtr);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   if(!BudgetPruefen())
      return;

   if(autoErlaubt && Trailing_ATR > 0 && letzterAtr > 0)
      Nachziehen();

   datetime t = iTime(_Symbol, tf, 0);
   if(t == 0 || t == letzteKerze)
      return;
   letzteKerze = t;
   Auswerten();
  }

//+------------------------------------------------------------------+
//| Budget- und Tageslimit. false = keine neuen Aktionen.             |
//+------------------------------------------------------------------+
bool BudgetPruefen()
  {
   if(GlobalVariableGet(gvGestoppt) > 0)
      return false;

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq <= GlobalVariableGet(gvStart) - Budget)
     {
      PositionenSchliessen(-1, "Budget aufgebraucht");
      GlobalVariableSet(gvGestoppt, 1);
      Melden("BUDGET AUFGEBRAUCHT – EA gestoppt. Neustart nur mit BudgetNeuStarten = true.");
      return false;
     }

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   double tagKey = dt.year * 10000.0 + dt.mon * 100.0 + dt.day;
   if(GlobalVariableGet(gvTag) != tagKey)
     {
      GlobalVariableSet(gvTag, tagKey);
      GlobalVariableSet(gvTagStart, eq);
      GlobalVariableSet(gvTagGestoppt, 0);
     }
   if(GlobalVariableGet(gvTagGestoppt) > 0)
      return false;

   if(MaxTagesverlust > 0 && eq <= GlobalVariableGet(gvTagStart) - MaxTagesverlust)
     {
      PositionenSchliessen(-1, "Tageslimit erreicht");
      GlobalVariableSet(gvTagGestoppt, 1);
      Melden("TAGESLIMIT ERREICHT – Pause bis zum nächsten Handelstag.");
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
double RestBudget()
  {
   return AccountInfoDouble(ACCOUNT_EQUITY) - (GlobalVariableGet(gvStart) - Budget);
  }

//+------------------------------------------------------------------+
//| Auswertung der zuletzt abgeschlossenen Kerze                      |
//+------------------------------------------------------------------+
void Auswerten()
  {
   double s[], l[], tr[], r[], a[];
   ArraySetAsSeries(s, true);
   ArraySetAsSeries(l, true);
   ArraySetAsSeries(tr, true);
   ArraySetAsSeries(r, true);
   ArraySetAsSeries(a, true);

   if(CopyBuffer(hSchnell, 0, 1, 2, s) < 2 || CopyBuffer(hLangsam, 0, 1, 2, l) < 2 ||
      CopyBuffer(hTrend, 0, 1, 1, tr) < 1 || CopyBuffer(hRsi, 0, 1, 1, r) < 1 ||
      CopyBuffer(hAtr, 0, 1, 1, a) < 1)
      return; // Daten noch nicht bereit

   letzterAtr = a[0];
   double schluss = iClose(_Symbol, tf, 1);

   // Index 0 = letzte abgeschlossene Kerze, 1 = die davor
   bool longSignal  = s[0] > l[0] && s[1] <= l[1] && schluss > tr[0] && r[0] > RSI_LongMin;
   bool shortSignal = s[0] < l[0] && s[1] >= l[1] && schluss < tr[0] && r[0] < RSI_ShortMax;

   if(SchliessenBeiGegensignal)
     {
      if(longSignal)
         PositionenSchliessen((int)POSITION_TYPE_SELL, "Gegensignal LONG");
      if(shortSignal)
         PositionenSchliessen((int)POSITION_TYPE_BUY, "Gegensignal SHORT");
     }

   if(!longSignal && !shortSignal)
      return;

   if(!Handelszeit())
     {
      Print("Signal außerhalb der Handelszeit ignoriert.");
      return;
     }
   if(autoErlaubt && AnzahlPositionen() >= MaxPositionen)
      return;

   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(MaxSpreadPunkte > 0 && spread > MaxSpreadPunkte)
     {
      Melden(StringFormat("Signal %s ignoriert – Spread %d > %d Punkte.",
                          longSignal ? "LONG" : "SHORT", (int)spread, MaxSpreadPunkte));
      return;
     }

   Eroeffnen(longSignal);
  }

//+------------------------------------------------------------------+
void Eroeffnen(bool kaufen)
  {
   double preis = kaufen ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double minAbst = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   double slAbst = MathMax(letzterAtr * SL_ATR, minAbst);
   double tpAbst = MathMax(letzterAtr * TP_ATR, minAbst);

   double sl = NormalizeDouble(kaufen ? preis - slAbst : preis + slAbst, _Digits);
   double tp = (TP_ATR > 0) ? NormalizeDouble(kaufen ? preis + tpAbst : preis - tpAbst, _Digits) : 0;

   double risiko = MathMin(RisikoProTrade, RestBudget());
   double lot = Lotgroesse(kaufen, preis, slAbst, risiko);

   string info = StringFormat("%s %s @%s SL %s TP %s | %.2f Lot | Risiko %.2f %s",
                              kaufen ? "LONG" : "SHORT", TfText(),
                              DoubleToString(preis, _Digits), DoubleToString(sl, _Digits),
                              tp > 0 ? DoubleToString(tp, _Digits) : "-",
                              lot, risiko, AccountInfoString(ACCOUNT_CURRENCY));

   if(lot <= 0)
     {
      Melden("Signal übersprungen (Lot unter Minimum oder Margin fehlt): " + info);
      return;
     }

   if(!autoErlaubt)
     {
      Melden("SIGNAL " + info + (SchliessenBeiGegensignal ? " | ggf. Gegenposition schließen" : ""));
      return;
     }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
     {
      Melden("Algo Trading ist deaktiviert – nicht eröffnet: " + info);
      return;
     }

   bool ok = kaufen ? trade.Buy(lot, _Symbol, 0, sl, tp, "AutoTrader")
                    : trade.Sell(lot, _Symbol, 0, sl, tp, "AutoTrader");
   uint rc = trade.ResultRetcode();
   if(ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED))
      Melden("ERÖFFNET " + info);
   else
      Melden(StringFormat("FEHLER %u (%s): %s", rc, trade.ResultRetcodeDescription(), info));
  }

//+------------------------------------------------------------------+
//| Lotgröße so, dass der Stop-Loss genau 'risiko' kostet             |
//+------------------------------------------------------------------+
double Lotgroesse(bool kaufen, double preis, double slAbst, double risiko)
  {
   double tickWert = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickGr   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(tickWert <= 0 || tickGr <= 0 || step <= 0 || slAbst <= 0 || risiko <= 0)
      return 0;

   double verlustProLot = slAbst / tickGr * tickWert;
   double lot = MathFloor(risiko / verlustProLot / step) * step;
   if(lot < minLot)
      return 0; // nie größer handeln als das Risiko erlaubt
   lot = MathMin(lot, maxLot);

   int stellen = 0;
   for(double x = step; x < 1.0 - 1e-9 && stellen < 8; x *= 10)
      stellen++;
   lot = NormalizeDouble(lot, stellen);

   double margin = 0;
   if(OrderCalcMargin(kaufen ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, _Symbol, lot, preis, margin) &&
      margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return 0;
   return lot;
  }

//+------------------------------------------------------------------+
//| Stop nachziehen, sobald die Position im Gewinn ist                |
//+------------------------------------------------------------------+
void Nachziehen()
  {
   double abst = letzterAtr * Trailing_ATR;
   if(abst < SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !EigenePosition())
         continue;

      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      double offen = PositionGetDouble(POSITION_PRICE_OPEN);

      if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
        {
         double neu = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_BID) - abst, _Digits);
         if(neu > offen && (sl == 0 || neu > sl + _Point))
            trade.PositionModify(ticket, neu, tp);
        }
      else
        {
         double neu = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_ASK) + abst, _Digits);
         if(neu < offen && (sl == 0 || neu < sl - _Point))
            trade.PositionModify(ticket, neu, tp);
        }
     }
  }

//+------------------------------------------------------------------+
//| typ: POSITION_TYPE_BUY / _SELL oder -1 für alle                   |
//+------------------------------------------------------------------+
void PositionenSchliessen(int typ, string grund)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !EigenePosition())
         continue;
      if(typ >= 0 && PositionGetInteger(POSITION_TYPE) != typ)
         continue;

      double ergebnis = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      string art = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "LONG" : "SHORT";
      if(trade.PositionClose(ticket))
         Melden(StringFormat("GESCHLOSSEN %s (%s) | Ergebnis ca. %.2f %s",
                             art, grund, ergebnis, AccountInfoString(ACCOUNT_CURRENCY)));
      else
         Melden(StringFormat("FEHLER beim Schließen %s: %u %s",
                             art, trade.ResultRetcode(), trade.ResultRetcodeDescription()));
     }
  }

//+------------------------------------------------------------------+
//| Erwartet eine per PositionGetTicket ausgewählte Position          |
//+------------------------------------------------------------------+
bool EigenePosition()
  {
   return PositionGetString(POSITION_SYMBOL) == _Symbol &&
          PositionGetInteger(POSITION_MAGIC) == MagicNumber;
  }

//+------------------------------------------------------------------+
int AnzahlPositionen()
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && EigenePosition())
         n++;
   return n;
  }

//+------------------------------------------------------------------+
bool Handelszeit()
  {
   if(StartStunde == EndStunde)
      return true;
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(StartStunde < EndStunde)
      return dt.hour >= StartStunde && dt.hour < EndStunde;
   return dt.hour >= StartStunde || dt.hour < EndStunde; // über Mitternacht
  }

//+------------------------------------------------------------------+
string TfText()
  {
   return _Symbol + " " + StringSubstr(EnumToString(tf), 7);
  }

//+------------------------------------------------------------------+
void Melden(string text)
  {
   string t = "AutoTrader " + text;
   Print(t);
   if(PushNachrichten && !MQLInfoInteger(MQL_TESTER))
      SendNotification(StringSubstr(t, 0, 255));
  }
//+------------------------------------------------------------------+
```
