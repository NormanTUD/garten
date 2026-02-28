# 🌱 GartenApp

Schrebergarten-Management für kleine Gruppen. Verwaltet Finanzen, Ernten,
Bewässerung, Gartenstunden und mehr – alles in einer Webapp, auch auf dem Handy.

---

## Features

- **Finanzsystem** – Ausgaben, Umlagen, Daueraufträge, Einzahlungen, automatische Kostenaufteilung
- **Gartenstunden** – Vereinsarbeit tracken, Ausgleichszahlungen berechnen
- **Ernte-Tracking** – Was wurde wann wo geerntet, mit Fotos
- **Bewässerung** – Gieß-Events mit Uhrzeit, Menge, Wetter, Dünger
- **Gartenkarte** – Beete auf Satellitenbildern zeichnen und verwalten (Leaflet)
- **Nachrichten** – Internes Nachrichtensystem mit automatischen Benachrichtigungen
- **Dashboard** – Statistiken und Übersichten auf einen Blick
- **Admin-Panel** – Nutzerverwaltung, Audit-Logs, Backup, Alerts
- **PWA** – Installierbar auf Android/iOS, funktioniert auch offline
- **REST-API** – Vollständig dokumentiert (OpenAPI/Swagger), API-Key Support
- **Audit-Logging** – Jeder API-Zugriff wird protokolliert

(Bisher geht nur das Finanzsystem halbwegs!!!)

### Geplant (Phase 3-4)

- 📸 Rechnungs-OCR (Qwen-VL, lokal serverseitig)
- 🌿 Pflanzenerkennung per Kamera (TensorFlow.js, clientseitig)
- 💧 Automatische Bewässerungs-KI (Sensordaten + Wetter)

---

## Tech-Stack

| Schicht    | Technologie                                    |
|------------|------------------------------------------------|
| Backend    | Python 3.12, FastAPI, SQLAlchemy 2.0 (async)  |
| Datenbank  | SQLite (migrierbar auf PostgreSQL)             |
| Frontend   | Vue 3, Vuetify 3, Pinia, Leaflet              |
| Auth       | JWT (Access + Refresh Tokens) + API-Keys       |
| DevOps     | Docker Compose, Nginx, GitHub Actions          |
| Testing    | pytest, Vitest, Playwright                     |

---

## Schnellstart

### Voraussetzungen

- Docker & Docker Compose
- Git

### 1. Repository klonen

``` bash
git clone https://github.com/youruser/gartenapp.git
cd gartenapp
```

### 2. Environment konfigurieren

``` bash
cp .env.example .env
```

Bearbeite ` .env ` und setze mindestens:

``` env
SECRET_KEY=dein-geheimer-schluessel-hier-aendern
FIRST_ADMIN_USERNAME=admin
FIRST_ADMIN_PASSWORD=sicheres-passwort
```

> **Tipp:** Einen sicheren Key generieren:
> ` python -c "import secrets; print(secrets.token_urlsafe(64))" `

### 3. Starten

``` bash
docker compose up -d --build
```

Die App ist jetzt erreichbar unter:

| URL                              | Was                        |
|----------------------------------|----------------------------|
| ` http://localhost `               | Frontend (GartenApp)       |
| ` http://localhost/api/docs `      | Swagger API-Dokumentation  |
| ` http://localhost/api/redoc `     | ReDoc API-Dokumentation    |

### 4. Erster Login

Melde dich mit den in ` .env ` konfigurierten Admin-Credentials an.
Der Admin-Account wird beim ersten Start automatisch erstellt.

---

## Entwicklung

### Backend (ohne Docker)

``` bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Datenbank initialisieren
alembic upgrade head

# Dev-Server starten
uvicorn app.main:app --reload --port 8000
```

### Frontend (ohne Docker)

``` bash
cd frontend
npm install
npm run dev
```

### Linting

``` bash
# Backend
cd backend
ruff check .
ruff format .

# Frontend
cd frontend
npm run lint
npm run format
```

---

## Tests

### Backend

``` bash
cd backend
pytest                    # Alle Tests
pytest -v                 # Verbose
pytest --cov=app          # Mit Coverage
pytest -k test_finance    # Nur Finance-Tests
```

### Frontend

``` bash
cd frontend
npm run test:unit         # Vitest (Unit Tests)
npm run test:e2e          # Playwright (E2E Tests)
npm run type-check        # vue-tsc
```

### CI/CD

Tests laufen automatisch bei jedem Push/PR via GitHub Actions.
Siehe ` .github/workflows/ ` für Details.

---

## Backup & Restore

### Via Admin-Panel

1. Einloggen als Admin
2. Administration → Backup
3. "Export" klickt → DB-Dump wird heruntergeladen
4. "Import" → DB-Dump hochladen zum Wiederherstellen

### Via API

``` bash
# Export
curl -H "X-API-Key: dein-key" http://localhost/api/backup/export -o backup.db

# Import
curl -X POST -H "X-API-Key: dein-key" \
  -F "file=@backup.db" \
  http://localhost/api/backup/import
```

### Via CLI (im Container)

``` bash
# Export
docker exec gartenapp-backend python -m app.backup.service export /app/data/backup.db

# Vom Container auf den Host kopieren
docker cp gartenapp-backend:/app/data/backup.db ./backup.db
```

> **Empfehlung:** Richte einen täglichen Cron-Job ein:
> ```
> 0 3 * * * docker exec gartenapp-backend python -m app.backup.service export /app/data/backups/$(date +\%Y\%m\%d).db
> ```

---

## API

Die API ist vollständig dokumentiert via OpenAPI/Swagger.
Nach dem Start erreichbar unter ` /api/docs `.

### Authentifizierung

**Browser/Frontend:** JWT Bearer Token

``` bash
# Login
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "passwort"}'

# Geschützter Request
curl -H "Authorization: Bearer <access_token>" \
  http://localhost/api/finance/fund-overview
```

**Scripts/Automationen:** API-Key

``` bash
curl -H "X-API-Key: dein-api-key" \
  http://localhost/api/finance/fund-overview
```

API-Keys können im Admin-Panel erstellt und verwaltet werden.

### Wichtige Endpoints

| Methode | Endpoint                          | Beschreibung                    |
|---------|-----------------------------------|---------------------------------|
| POST    | ` /api/auth/login `                 | Login                           |
| POST    | ` /api/auth/refresh `               | Token erneuern                  |
| GET     | ` /api/users/ `                     | Alle Nutzer                     |
| GET     | ` /api/garden/ `                    | Garten-Info                     |
| GET/POST| ` /api/beds/ `                      | Beete verwalten                 |
| GET/POST| ` /api/plants/ `                    | Pflanzen-Katalog                |
| GET/POST| ` /api/harvest/ `                   | Ernten eintragen/abrufen        |
| GET/POST| ` /api/watering/ `                  | Bewässerung eintragen/abrufen   |
| GET/POST| ` /api/finance/expenses `            | Ausgaben                        |
| GET/POST| ` /api/finance/payments `             | Einzahlungen                    |
| GET/POST| ` /api/finance/standing-orders `     | Daueraufträge                   |
| GET     | ` /api/finance/fund-overview `       | Kassenübersicht + Balances      |
| GET/POST| ` /api/finance/recurring-costs `     | Laufende Kosten (Admin)         |
| GET/POST| ` /api/duty/ `                      | Gartenstunden                   |
| GET     | ` /api/messages/ `                  | Nachrichten                     |
| GET     | ` /api/backup/export `              | DB-Backup herunterladen (Admin) |
| POST    | ` /api/backup/import `              | DB-Backup einspielen (Admin)    |

Vollständige Dokumentation: ` /api/docs ` (Swagger) oder ` /api/redoc ` (ReDoc)

---

## Projektstruktur

```
gartenapp/
├── docker-compose.yml
├── .env.example
├── .github/workflows/       # CI/CD
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/             # DB Migrations
│   ├── app/
│   │   ├── main.py          # FastAPI App
│   │   ├── config.py        # Settings
│   │   ├── database.py      # DB Engine
│   │   ├── auth/            # Login, JWT, API-Keys
│   │   ├── users/           # Nutzerverwaltung
│   │   ├── garden/          # Garten
│   │   ├── beds/            # Beete
│   │   ├── plants/          # Pflanzen-Katalog
│   │   ├── harvest/         # Ernte-Tracking
│   │   ├── watering/        # Bewässerung
│   │   ├── finance/         # Finanzsystem
│   │   ├── duty/            # Gartenstunden
│   │   ├── sensors/         # Sensoren (vorbereitet)
│   │   ├── messaging/       # Nachrichten
│   │   ├── backup/          # Export/Import
│   │   └── middleware/       # Audit-Log, CORS
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── views/           # Seiten
│   │   ├── components/      # UI-Komponenten
│   │   ├── stores/          # Pinia State
│   │   ├── api/             # API Client
│   │   └── composables/     # Vue Composables
│   └── tests/
├── nginx/
│   └── default.conf
└── docs/
    ├── ARCHITECTURE.md
    ├── API.md
    └── SETUP.md
```

Für Details zur Architektur siehe [ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Konfiguration

Alle Einstellungen werden über Umgebungsvariablen gesteuert (` .env ` Datei):

| Variable                  | Beschreibung                        | Default                |
|---------------------------|-------------------------------------|------------------------|
| ` SECRET_KEY `              | JWT Signing Key                     | *Pflichtfeld*          |
| ` DATABASE_URL `            | SQLAlchemy DB URL                   | ` sqlite+aiosqlite:///./data/gartenapp.db ` |
| ` FIRST_ADMIN_USERNAME `    | Admin-Username beim ersten Start    | ` admin `            |
| ` FIRST_ADMIN_PASSWORD `    | Admin-Passwort beim ersten Start    | *Pflichtfeld*          |
| ` ACCESS_TOKEN_EXPIRE_MINUTES ` | JWT Access Token Gültigkeit     | ` 30 `               |
| ` REFRESH_TOKEN_EXPIRE_DAYS `   | JWT Refresh Token Gültigkeit    | ` 7 `                |
| ` CORS_ORIGINS `            | Erlaubte Origins (kommagetrennt)    | ` * `                |
| ` UPLOAD_DIR `              | Verzeichnis für Uploads             | ` ./data/uploads `   |

---

## Mitwirken

1. Fork erstellen
2. Feature-Branch anlegen (` git checkout -b feature/mein-feature `)
3. Änderungen committen (` git commit -m "feat: mein neues feature" `)
4. Branch pushen (` git push origin feature/mein-feature `)
5. Pull Request erstellen

**Commit-Konvention:** [Conventional Commits](https://www.conventionalcommits.org/)

```
feat: neues Feature
fix: Bugfix
docs: Dokumentation
refactor: Code-Umbau ohne Funktionsänderung
test: Tests hinzufügen/ändern
chore: Build, CI, Dependencies
```

---

## Lizenz

Dieses Projekt ist privat. Alle Rechte vorbehalten.

---

## Danksagungen

Gebaut mit ❤️ und diesen großartigen Open-Source-Projekten:

- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [Vuetify](https://vuetifyjs.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Leaflet](https://leafletjs.com/)
- [Pinia](https://pinia.vuejs.org/)
