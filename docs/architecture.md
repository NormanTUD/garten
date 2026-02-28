# GartenApp – Architektur-Dokumentation

## Überblick

GartenApp ist eine Schrebergarten-Management-Anwendung für 5-10 Nutzer.
Sie läuft als dockerisierte Webanwendung auf einem eigenen Linux-Server (Debian)
und ist als PWA auf dem Handy installierbar.

**Architektur-Prinzip:** API-First. Das Backend stellt eine REST-API bereit,
das Frontend ist ein reiner Client. Alles läuft über die API – auch das Frontend
hat keine Sonderbehandlung.

---

## Tech-Stack

| Schicht       | Technologie                                      |
|---------------|--------------------------------------------------|
| Backend       | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async)   |
| Datenbank     | SQLite (via aiosqlite), migrierbar auf PostgreSQL|
| Migrations    | Alembic                                          |
| Auth          | JWT (Access + Refresh Tokens)                    |
| Frontend      | Vue 3 (Composition API), Vuetify 3, Pinia        |
| Karten        | Leaflet + ESRI Satellite Tiles                   |
| PWA           | Vite PWA Plugin, Service Worker                  |
| KI (später)   | TensorFlow.js (clientseitig), Qwen-VL (Server)  |
| Testing       | pytest, httpx, Vitest, Playwright                |
| CI/CD         | GitHub Actions                                   |
| Deployment    | Docker Compose, Nginx Reverse Proxy              |

---

## Ordnerstruktur

```
gartenapp/
├── apache
│   ├── certs
│   ├── Dockerfile
│   ├── gartenapp.conf
│   └── gartenapp-dev.conf
├── backend
│   ├── alembic
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions
│   │       ├── 001_initial_schema.py
│   │       ├── 002_harvest_watering_fertilizing.py
│   │       ├── 003_finance.py
│   │       ├── 004_messaging.py
│   │       └── 005_duty.py
│   ├── alembic.ini
│   ├── app
│   │   ├── audit
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── auth
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── utils.py
│   │   ├── beds
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   ├── duty
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── finance
│   │   │   ├── balance_calculator.py
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── garden
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── harvest
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── messaging
│   │   │   ├── default_rules.py
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── middleware
│   │   │   └── audit_log.py
│   │   ├── plants
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   └── watering
│   │       ├── __init__.py
│   │       ├── models.py
│   │       ├── router.py
│   │       ├── schemas.py
│   │       └── service.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── tests
│       ├── conftest.py
│       ├── __init__.py
│       ├── test_audit.py
│       ├── test_auth.py
│       ├── test_beds.py
│       ├── test_duty.py
│       ├── test_edge_cases.py
│       ├── test_finance.py
│       ├── test_garden.py
│       ├── test_harvest.py
│       ├── test_health.py
│       ├── test_messaging.py
│       ├── test_plants.py
│       ├── test_users.py
│       └── test_watering.py
├── build
├── build_dev
├── delete_and_rebuild
├── docker-compose.dev.yml
├── docker-compose.override.yml
├── docker-compose.yml
├── docs
│   └── architecture.md
├── frontend
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf
│   ├── package.json
│   ├── package-lock.json
│   ├── public
│   │   ├── favicon.svg
│   │   ├── icons
│   │   │   ├── icon-128x128.png
│   │   │   ├── icon-144x144.png
│   │   │   ├── icon-152x152.png
│   │   │   ├── icon-192x192.png
│   │   │   ├── icon-256x256.png
│   │   │   ├── icon-384x384.png
│   │   │   ├── icon-48x48.png
│   │   │   ├── icon-512x512.png
│   │   │   ├── icon-72x72.png
│   │   │   ├── icon-96x96.png
│   │   │   ├── icon-maskable.png
│   │   │   ├── logo.png
│   │   │   └── original_icon.png
│   │   └── manifest.json
│   ├── scripts
│   │   └── generate-icons.sh
│   ├── src
│   │   ├── api
│   │   │   └── client.ts
│   │   ├── App.vue
│   │   ├── components
│   │   │   ├── layout
│   │   │   │   ├── AppBar.vue
│   │   │   │   ├── BottomNav.vue
│   │   │   │   └── NavDrawer.vue
│   │   │   └── shared
│   │   │       └── PhotoCapture.vue
│   │   ├── main.ts
│   │   ├── plugins
│   │   │   └── vuetify.ts
│   │   ├── router
│   │   │   └── index.ts
│   │   ├── stores
│   │   │   └── auth.ts
│   │   ├── __tests__
│   │   │   ├── api-client.test.ts
│   │   │   └── auth-store.test.ts
│   │   ├── views
│   │   │   ├── AdminView.vue
│   │   │   ├── DashboardView.vue
│   │   │   ├── DutyView.vue
│   │   │   ├── FinanceView.vue
│   │   │   ├── GardenView.vue
│   │   │   ├── HarvestView.vue
│   │   │   ├── LoginView.vue
│   │   │   ├── MessagesView.vue
│   │   │   └── WateringView.vue
│   │   └── vite-env.d.ts
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   └── vitest.config.ts
├── prompt.txt
├── README.md
└── tests

```

---

## Backend-Architektur

### Modulstruktur

Jedes Feature-Modul (auth, finance, harvest, ...) folgt dem gleichen Muster:

```
module/
├── models.py      # SQLAlchemy ORM Models
├── schemas.py     # Pydantic Request/Response Schemas
├── service.py     # Business-Logik (DB-Operationen)
└── router.py      # FastAPI Endpoints
```

**Regeln:**
- `router.py` ruft nur `service.py` auf, nie direkt die DB
- `service.py` enthält die gesamte Business-Logik
- `models.py` definiert nur die DB-Struktur, keine Logik
- `schemas.py` definiert API-Contracts (Input/Output)

### Request-Lifecycle

```
Client Request
  → Nginx (Reverse Proxy, SSL)
    → FastAPI (ASGI)
      → CORS Middleware
        → Audit-Log Middleware (loggt jeden Request)
          → Auth Dependency (JWT validieren)
            → Router → Service → SQLAlchemy → SQLite
          ← Response
        ← Audit-Log schreibt Response-Status
      ← CORS Headers
    ← Response
  ← Nginx
← Client Response
```

### Authentifizierung

```
Login: POST /api/auth/login
  → Username + Passwort prüfen (bcrypt)
  → Access Token (JWT, 30min) + Refresh Token (JWT, 7d) zurückgeben

Geschützter Request: GET /api/harvest/
  → Authorization: Bearer <access_token>
  → JWT dekodieren → User laden → Request verarbeiten

Token Refresh: POST /api/auth/refresh
  → Refresh Token prüfen → neues Access Token zurückgeben

API-Key: GET /api/harvest/ (für Scripts/Automationen)
  → X-API-Key: <key>
  → Key hashen → in DB suchen → User laden → Request verarbeiten
```

### Rollen & Berechtigungen

| Aktion                          | User | Admin |
|---------------------------------|------|-------|
| Eigene Einträge erstellen       | ✓    | ✓     |
| Eigene Einträge bearbeiten      | ✓    | ✓     |
| Alle Einträge sehen             | ✓    | ✓     |
| Fremde Einträge bearbeiten      | ✗    | ✓     |
| Einträge löschen                | ✗    | ✓     |
| User verwalten                  | ✗    | ✓     |
| Laufende Kosten verwalten       | ✗    | ✓     |
| Ausgaben bestätigen (Umlagen)   | ✗    | ✓     |
| Gartenstunden bestätigen        | ✗    | ✓     |
| Audit-Logs einsehen             | ✗    | ✓     |
| Backup erstellen/importieren    | ✗    | ✓     |

---

## Datenmodell

### ER-Diagramm (vereinfacht)

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│   User   │────<│ Harvest  │>────│  Plant   │
│          │     │          │     │          │
│ id       │     │ id       │     │ id       │
│ username │     │ user_id  │     │ name     │
│ role     │     │ plant_id │     │ variety  │
│          │     │ bed_id   │     │ category │
└──────────┘     │ amount   │     └──────────┘
     │           │ unit     │          │
     │           │ date     │          │
     │           └──────────┘          │
     │                                 │
     │           ┌──────────┐     ┌────┴─────┐
     ├──────────<│ Watering │>────│   Bed    │
     │           │ Event    │     │          │
     │           │          │     │ id       │
     │           │ id       │     │ name     │
     │           │ user_id  │     │ geometry │
     │           │ bed_id   │     │ garden_id│
     │           │ liters   │     └────┬─────┘
     │           │ duration │          │
     │           └──────────┘     ┌────┴─────┐
     │                            │  Garden  │
     │           ┌──────────┐     │          │
     ├──────────<│ Expense  │     │ id       │
     │           │          │     │ name     │
     │           │ id       │     │ location │
     │           │ user_id  │     └──────────┘
     │           │ amount   │
     │           │ is_shared│
     │           └──────────┘
     │
     │           ┌──────────────┐
     ├──────────<│StandingOrder │
     │           │              │
     │           │ id           │
     │           │ user_id      │
     │           │ amount_cents │
     │           │ valid_from   │
     │           │ valid_to     │
     │           └──────┬───────┘
     │                  │
     │           ┌──────┴───────┐
     │           │StandingOrder │
     │           │    Skip      │
     │           │ month, year  │
     │           └──────────────┘
     │
     │           ┌──────────┐
     └──────────<│  Duty    │
                 │  Log     │
                 │          │
                 │ id       │
                 │ user_id  │
                 │ hours    │
                 │ date     │
                 └──────────┘
```

### Sensor-Datenmodell (vorbereitet für Phase 4)

```
┌──────────┐     ┌──────────────┐     ┌────────────────┐
│   Bed    │────<│   Sensor     │────<│ SensorReading  │
│          │     │              │     │                │
└──────────┘     │ type         │     │ value          │
                 │ hardware_id  │     │ unit           │
                 └──────────────┘     │ timestamp      │
                                      └────────────────┘

┌──────────────────┐     ┌────────────────────┐
│ IrrigationZone   │────<│ IrrigationSchedule │
│                  │     │                    │
│ beds (m2m)       │     │ trigger_type       │
│ valve_hardware_id│     │ (manual/scheduled/ │
└──────────────────┘     │  ai)               │
                         └────────────────────┘
```

---

## Finanzsystem

### Konzept

Das Finanzsystem berechnet pro Jahr, wie viel jedes Mitglied zahlen muss
und wie viel es bereits gezahlt hat.

**Kostenarten:**
- **Laufende Kosten** (RecurringCost): Monatlich oder jährlich, z.B. Pacht, Wasser
- **Einmal-Ausgaben** (GardenExpense): Erde, Werkzeug, etc. – müssen von Admin bestätigt werden wenn von User erstellt; Admin-Ausgaben werden automatisch bestätigt

**Einnahmen:**
- **Einzahlungen** (MemberPayment): Manuelle Zahlungen (Bar, Überweisung, Material)
- **Daueraufträge** (StandingOrder): Monatliche automatische Zahlungen

### Balance-Berechnung

```
Gesamtkosten/Jahr = Σ(Laufende Kosten) + Σ(Einmal-Ausgaben bestätigt)
Soll/Person       = Gesamtkosten / Anzahl aktive Mitglieder

Ist/Person         = Einzahlungen + Daueraufträge (nur abgeschlossene Monate!)
Remaining          = Soll - Ist
                     > 0 → schuldet noch Geld
                     < 0 → hat überbezahlt (Rückerstattung)
                     = 0 → ausgeglichen

Prognose/Person    = Einzahlungen + Daueraufträge (ganzes Jahr projiziert)
Remaining Projected = Soll - Prognose
```

**Wichtig:** Daueraufträge zählen erst als "bezahlt" wenn der Monat
**vollständig abgeschlossen** ist. Am 28. Februar zählt nur Januar.
Ab 1. März zählen Januar + Februar.

### Gartenstunden

```
Pflicht/Person/Jahr  = GardenDutyConfig.required_hours (z.B. 2.5h)
Stundensatz          = GardenDutyConfig.hourly_rate_cents (variabel pro Jahr)
Geleistet            = Σ(DutyLog.hours) für bestätigte Einträge
Offen                = Pflicht - Geleistet
Ausgleichszahlung    = Offen × Stundensatz
```

---

## Frontend-Architektur

### State Management (Pinia)

```
stores/
├── auth.ts       # User, Token, Login/Logout
├── garden.ts     # Garden, Beds, Plants
├── harvest.ts    # Harvest entries
├── watering.ts   # Watering events
├── finance.ts    # Expenses, Payments, Standing Orders, Fund Overview
└── duty.ts       # Garden duty logs
```

Jeder Store folgt dem Muster:
- State: Reactive Daten
- Actions: API-Calls via ` api/client.ts `
- Getters: Computed/abgeleitete Daten

### API Client

` api/client.ts ` ist ein Fetch-Wrapper der:
- JWT Access Token automatisch als Bearer Header mitsendet
- Bei 401 automatisch ein Token-Refresh versucht
- Bei erneutem 401 zum Login redirected
- Basis-URL aus Environment liest

### Routing

```
/              → DashboardView (Startseite)
/login         → LoginView
/garden        → GardenView (Karte + Beete)
/harvest       → HarvestView
/watering      → WateringView
/finance       → FinanceView
/duty          → DutyView
/calendar      → CalendarView
/stats         → StatsView
/messages      → MessagesView
/admin         → AdminView (nur Admins)
```

### PWA

- ` manifest.json `: App-Name, Icons, Theme-Color
- Service Worker: Caching für Offline-Nutzung
- Installierbar auf Android/iOS Homescreen
- Update-Detection mit Snackbar-Benachrichtigung

### Karten-Integration (Leaflet)

- ESRI Satellite Tiles als Basislayer (kostenlos)
- Leaflet.draw Plugin für Polygon-Editor (Beete zeichnen)
- GeoJSON Polygone werden in ` Bed.geometry ` gespeichert
- Klick auf Beet → Details, Statistiken, Bewässerung

---

## Deployment

### Docker Compose

``` yaml
services:
  backend:
    build: ./backend
    volumes:
      - ./data:/app/data          # SQLite DB + Uploads
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/gartenapp.db
      - SECRET_KEY=${SECRET_KEY}

  frontend:
    build: ./frontend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
```

### Nginx

```
/api/*     → backend:8000  (FastAPI)
/*         → frontend      (Vue SPA, static files)
```

### Backup

- **API:** ` GET /api/backup/export ` → SQLite DB-Dump als Download
- **API:** ` POST /api/backup/import ` → DB-Dump hochladen + einspielen
- **CLI:** ` docker exec gartenapp-backend python -m app.backup.service export `
- Empfehlung: Täglicher Cron-Job für automatisches Backup

---

## CI/CD Pipeline (GitHub Actions)

### Backend

```
Trigger: Push/PR auf main
1. Python 3.12 Setup
2. pip install (mit Cache)
3. Ruff Linting
4. pytest (Unit + Integration Tests)
5. Coverage Report
```

### Frontend

```
Trigger: Push/PR auf main
1. Node 20 Setup
2. npm ci (mit Cache)
3. ESLint + Prettier Check
4. vue-tsc (Type Check)
5. Vitest (Unit Tests)
6. Playwright (E2E Tests)
```

---

## Entwicklungsphasen

### Phase 1: Foundation ✓
Backend + Auth + Basis-CRUD + Minimales Frontend + PWA + CI/CD

### Phase 2: Features & UX (aktuell)
Leaflet Gartenkarte, Dashboard, Statistiken, Kalender,
Finanzsystem komplett, Gartenstunden, Foto-Upload, Backup, Admin-Panel

### Phase 3: KI-Features (Serverseitig)
Rechnungs-OCR (Qwen-VL, lokal), Wetter-API Integration,
Sensor-Datenmodell + API

### Phase 4: KI-Features (Clientseitig) + Bewässerung
TF.js Pflanzenerkennung im Browser, Kamera → Erkennung → Formular,
Bewässerungs-KI Datengrundlage, Irrigation Zones + Schedules

---

## Audit-Logging

Jeder API-Request wird in der ` AuditLog ` Tabelle gespeichert:

| Feld            | Beschreibung                    |
|-----------------|---------------------------------|
| user_id         | Wer hat den Request gemacht     |
| method          | GET, POST, PUT, DELETE          |
| endpoint        | z.B. /api/finance/expenses      |
| request_body    | JSON Body (bei POST/PUT)        |
| response_status | HTTP Status Code                |
| ip_address      | Client IP                       |
| timestamp       | Zeitpunkt des Requests          |

Admins können die Logs im Admin-Panel einsehen und filtern.
Alerts werden in der GUI angezeigt wenn Fehler auftreten.
