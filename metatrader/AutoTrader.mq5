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
input ENUM_MODUS      Modus           = MODUS_NUR_SIGNAL; // Modus
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
