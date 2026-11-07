# SaaSWatch

Plateforme de monitoring et d'analyse des logs d'une application SaaS avec la stack **ELK** (Elasticsearch, Logstash, Kibana), **MongoDB** et **Redis**.

Mini-projet Big Data — ITBS 2026-2027 — Scénario D (Application Web SaaS).

## Architecture

| Service | Rôle | Port |
|---|---|---|
| elasticsearch | Stockage et recherche des logs (index `logs-saas-*`) | 9200 |
| logstash | Ingestion des fichiers CSV et JSON de `data/uploads` | 9600 |
| kibana | Visualisations et dashboards | 5601 |
| mongodb | Métadonnées, historique, règles d'alerte | 27017 |
| redis | Cache, sessions, files d'attente | 6379 |
| webapp | Application Flask (interface + API) | 8000 |
| es-init | Crée l'index template au démarrage, puis s'arrête | — |

## Prérequis

- Docker Desktop (Docker 24+ et Docker Compose 2+)
- 6 Go de RAM disponibles pour Docker
- Python 3.11 (uniquement pour le générateur de logs)

## Installation

```bash
git clone https://github.com/Malek-Mallat/saaswatch.git
cd saaswatch
cp .env.example .env        # sous Windows : copy .env.example .env
docker compose up -d --build
```

Attendre 1 à 2 minutes, puis vérifier :

```bash
docker compose ps
```

Tous les services doivent être `running` ou `healthy`, sauf `es-init` qui est `exited (0)` (normal : il s'arrête après avoir créé le template).

## Vérifications

| URL | Résultat attendu |
|---|---|
| http://localhost:9200 | Réponse JSON d'Elasticsearch |
| http://localhost:5601 | Interface Kibana |
| http://localhost:8000/status | Les 3 services à `ok` |

## Générer et importer des logs

```bash
cd generator
pip install -r requirements.txt
python generate_logs.py --rows 5000 --format csv --out ../data/uploads/logs_api.csv --incident
python generate_logs.py --rows 2000 --format json --out ../data/uploads/logs_app.json
```

Logstash lit automatiquement tout fichier `.csv` ou `.json` déposé dans `data/uploads`.
Des fichiers d'exemple sont aussi disponibles dans `data/samples` : il suffit de les copier dans `data/uploads`.

Vérifier l'import :

```bash
curl "http://localhost:9200/_cat/indices/logs-saas-*?v"
curl "http://localhost:9200/logs-saas-*/_count"
```

## Arrêt

```bash
docker compose stop        # arrêter
docker compose down        # arrêter et supprimer les conteneurs (les données restent)
docker compose down -v     # tout supprimer, y compris les données
```

## Structure du projet

```
saaswatch/
├── docker-compose.yml
├── .env.example
├── elasticsearch/      index template + script d'initialisation
├── logstash/           configuration et pipelines CSV / JSON
├── webapp/             application Flask
├── generator/          générateur de logs (Faker)
├── data/uploads/       fichiers à ingérer
├── data/samples/       fichiers d'exemple
└── docs/               dossier d'analyse et de conception
```
