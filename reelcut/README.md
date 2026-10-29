# ReelCut – Reels & TikToks automatisch schneiden lassen

Android-App + Backend. Du teilst ein Rohvideo aus der Galerie mit ReelCut, das Backend transkribiert es
(Whisper), **Claude** plant Schnitt, Hook, Untertitel-Design und Bild/Ton-Aufbereitung, FFmpeg rendert
das fertige 9:16-Video mit eingebrannten Untertiteln im **Freestyle-Mix** (wechselnde Fonts, Farben,
Größen, Positionen, Animationen). Das Ergebnis landet in `Filme/ReelCut` und lässt sich mit einem Tipp an
TikTok oder Instagram übergeben – die vorgeschlagene Caption liegt dabei schon in der Zwischenablage.

```
Android-App (Kotlin/Compose)           Backend (Python/FastAPI)              KI / Tools
──────────────────────────────         ──────────────────────────────         ─────────────────────────
Video teilen / auswählen   ──upload──▶ POST /v1/jobs
Fortschritt (WorkManager)  ◀──poll───  GET  /v1/jobs/{id}
                                        1. ffprobe/ffmpeg: Audio extrahieren
                                        2. Transkript mit Wort-Zeitstempeln ──▶ faster-whisper (lokal)
                                        3. EditPlan (Schnitt, Captions,
                                           Styles, Enhance, Caption-Text)  ──▶ Claude (structured output)
                                        4. .ass-Untertitel erzeugen (libass)
                                        5. Render: trim/concat, 1080x1920,
                                           eq/unsharp, afftdn/loudnorm, ass
Ergebnis laden, in Galerie ◀─download─ GET  /v1/jobs/{id}/result
Teilen → TikTok / Instagram
```

## Warum ein Backend und nicht alles auf dem Handy?

- Der Claude-API-Key darf nicht in eine APK (jeder kann ihn extrahieren). Das Backend hält den Key.
- Whisper mit Wort-Zeitstempeln und ein FFmpeg-Render mit libass sind auf dem Handy langsam/instabil.
- Du kannst das Backend auf einem kleinen Server (Hetzner, eigener PC im LAN, Docker) laufen lassen; die
  App braucht nur URL + Token.

## Was Claude konkret entscheidet (`backend/reelcut/planner.py`)

Claude bekommt das Wort-Transkript mit Zeiten, Preset, Ziellänge und deine Anweisungen und liefert ein
striktes JSON (`EditPlan`, Pydantic-Schema, `output_format`):

| Feld | Inhalt |
|---|---|
| `keep_segments` | Welche Stellen bleiben (Hook nach vorn, Füllwörter/Pausen/Versprecher raus, Ziellänge ±15 %) |
| `captions` | 2–5 Wörter pro Zeile, Zeiten auf Wortgrenzen, Betonungswörter, Emoji, Position, Animation, **Style** (Font-Familie, Größe, Farben, Box/Outline, Neigung) |
| `enhance` | Rauschfilter, Loudness-Normalisierung, Schärfen, Farb-Boost, optional Stabilisierung |
| `title` / `suggested_caption` | Hook-Titel für die ersten 2 s und Post-Text mit Hashtags |

Presets: `freestyle_mix` (Standard, bewusst gemischtes Design), `bold_pop`, `clean`, `karaoke`.
Fällt die API aus, greift ein regelbasierter Plan (`plan_heuristic`), damit trotzdem ein Video entsteht.

## Backend starten

Voraussetzungen: Python ≥ 3.11, `ffmpeg` mit libass (Ubuntu/Debian: `apt install ffmpeg`), Fonts.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # ANTHROPIC_API_KEY und REELCUT_API_TOKEN eintragen
set -a; source .env; set +a
uvicorn reelcut.main:app --host 0.0.0.0 --port 8000
```

Oder mit Docker (bringt ffmpeg + Fonts mit):

```bash
cd backend
docker build -t reelcut-backend .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... -e REELCUT_API_TOKEN=geheim -v reelcut-data:/app/data reelcut-backend
```

Testaufruf ohne App:

```bash
curl -H "Authorization: Bearer geheim" -F file=@roh.mp4 -F preset=freestyle_mix -F target_duration=30 \
     -F instructions="Hook betonen, keine Emojis" http://localhost:8000/v1/jobs
curl -H "Authorization: Bearer geheim" http://localhost:8000/v1/jobs/<id>          # Status + Plan
curl -H "Authorization: Bearer geheim" -o fertig.mp4 http://localhost:8000/v1/jobs/<id>/result
```

Tests (ohne API-Key, ohne Whisper-Download – Mock-Transkript + Heuristik + echter FFmpeg-Render):

```bash
pip install -r requirements-dev.txt
pytest
```

Wichtige Variablen (alle in `.env.example`): `REELCUT_CLAUDE_MODEL` (Standard `claude-opus-5-5`),
`REELCUT_CLAUDE_EFFORT`, `REELCUT_WHISPER_MODEL` (`small` reicht für Deutsch, `medium` ist genauer,
GPU: `REELCUT_WHISPER_DEVICE=cuda`), `REELCUT_FONTS_DIR` + `REELCUT_FONT_<FAMILIE>` für eigene Schriften
(z. B. Anton, Bebas Neue für den TikTok-Look).

## Android-App bauen

1. `android/` in Android Studio (Ladybug oder neuer) öffnen, Gradle-Sync abwarten (AGP 8.7, Kotlin 2.0,
   Compose BOM 2024.12). Die Gradle-Wrapper-Dateien erzeugt Android Studio beim ersten Öffnen, alternativ
   `gradle wrapper --gradle-version 8.9` im Ordner `android/`.
2. Debug-Build auf dem Handy installieren (`Run`). Debug erlaubt `http://` für den Server im LAN, Release
   verlangt `https://`.
3. In der App unter **Einstellungen** Server-URL (z. B. `http://192.168.0.10:8000/`) und Token eintragen,
   **Verbindung testen**.
4. Video auswählen oder aus der Galerie **„Mit ReelCut schneiden“** teilen. Bei aktivierter Option
   „Geteilte Videos sofort verarbeiten“ startet der Job ohne weitere Klicks mit den zuletzt gespeicherten
   Einstellungen. Upload/Polling/Download laufen als WorkManager-Job im Hintergrund mit Benachrichtigung.
5. Ergebnis ansehen, **Zu TikTok** / **Zu Instagram** tippen – die App übergibt das Video per Share-Intent
   und kopiert die vorgeschlagene Caption in die Zwischenablage.

## Grenzen (ehrlich)

- **Kein automatisches Posten.** TikTok (Content Posting API) und Instagram (Graph API) erlauben das nur
  nach App-Review bzw. für Business-Konten. Der letzte Tipp „Posten“ bleibt bei dir; alles davor ist
  automatisiert.
- **Claude sieht keine Bilder.** Der Schnitt basiert auf dem Gesprochenen. Für reine Musik-/B-Roll-Clips
  ohne Sprache gibt es keine sinnvollen Schnittentscheidungen – dann bleibt das Video ungeschnitten und
  wird nur aufbereitet.
- **Whisper auf CPU** braucht für 60 s Video mit `small` ca. 20–60 s. GPU oder ein kleineres Modell
  beschleunigt das.
- **Kosten pro Video** (Claude Opus 5.5, Stand Okt 2026, $4/$20 pro 1M Tokens): Transkript + Prompt sind
  typischerweise 2–6k Input-Tokens, der Plan 2–6k Output-Tokens → grob 0,05–0,15 $ pro Video. Der
  System-Prompt ist gecacht.
- Die Android-App wurde in dieser Umgebung **nicht kompiliert** (kein Android-SDK verfügbar). Der Code
  folgt den aktuellen stabilen APIs, kleine Compile-Korrekturen beim ersten Build sind aber möglich.
  Das Backend ist durch Tests abgedeckt (inkl. echtem FFmpeg-Render).

## Projektstruktur

```
backend/reelcut/
  main.py        FastAPI-Endpunkte, Bearer-Token-Auth
  jobs.py        Job-Store + Worker-Thread, status.json pro Job
  pipeline.py    probe → transcribe → plan → captions → render
  transcribe.py  faster-whisper (oder mock)
  planner.py     Claude structured output (EditPlan), Heuristik-Fallback, Plan-Validierung
  captions.py    EditPlan → .ass (Styles, Betonung, Animationen, Karaoke, Hook-Titel)
  render.py      FFmpeg: trim/concat, 9:16-Fit (Crop oder Blur-Hintergrund), Enhance, ass-Burn-in
  schemas.py     Pydantic-Modelle (API + Claude-Schema)
android/app/src/main/java/de/reelcut/app/
  MainActivity.kt           Launcher + Share-Target (ACTION_SEND video/*)
  work/ProcessVideoWorker   Upload → Poll → Download → MediaStore, Foreground-Notification
  data/                     Retrofit-API, DataStore-Einstellungen, Video-Import/Galerie
  ui/                       Compose-Screens: Home, Processing, Result (ExoPlayer), Settings
  share/ShareHelper.kt      Direkt an TikTok / Instagram teilen
```
