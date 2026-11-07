"""Générateur de logs réalistes pour une application SaaS (SaaSWatch).

Exemples :
    python generate_logs.py --rows 5000 --format csv  --out ../data/uploads/logs_api.csv
    python generate_logs.py --rows 5000 --format json --out ../data/uploads/logs_api.json
    python generate_logs.py --rows 20000 --days 7 --incident

Le script simule :
- des logs serveur web (nginx), applicatifs (flask), base de données (db)
  et de performance ;
- un trafic plus fort en journée qu'en pleine nuit ;
- avec --incident : un incident (lenteurs et erreurs 5xx sur le service billing).
"""
import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone

from faker import Faker

fake = Faker("fr_FR")

SERVICES = {
    "api":     ["/api/projects", "/api/tasks", "/api/comments", "/api/teams"],
    "auth":    ["/login", "/logout", "/api/token", "/signup"],
    "billing": ["/api/invoices", "/api/subscriptions", "/api/payments"],
    "search":  ["/api/search"],
    "export":  ["/api/export/csv", "/api/export/pdf"],
}
FEATURES = {"api": "projects", "auth": "authentication", "billing": "billing",
            "search": "search", "export": "export"}
TENANTS = [fake.unique.company().split()[0].lower() for _ in range(25)]
USERS = [f"u_{i}" for i in range(1000, 1400)]
METHODS = {"GET": 70, "POST": 20, "PUT": 6, "DELETE": 4}
SLOW_QUERIES = [
    "SELECT * FROM projects WHERE tenant_id = ? ORDER BY updated_at DESC",
    "SELECT t.*, u.name FROM tasks t JOIN users u ON t.owner = u.id",
    "UPDATE invoices SET status = 'paid' WHERE id = ?",
    "SELECT COUNT(*) FROM events WHERE created_at > NOW() - INTERVAL 30 DAY",
]
FIELDS = ["timestamp", "level", "service", "source", "http_method", "endpoint",
          "status_code", "response_time", "user_id", "tenant", "feature",
          "client_ip", "sql_query", "message"]


def random_time(start, days, now):
    """Heure aléatoire (plus de trafic entre 8 h et 20 h), jamais dans le futur."""
    while True:
        day = start + timedelta(days=random.randrange(days))
        hour = random.choices(range(24), weights=[1, 1, 1, 1, 1, 2, 3, 5, 8, 9, 9, 9,
                                                  8, 9, 9, 9, 8, 7, 6, 5, 4, 3, 2, 1])[0]
        ts = day.replace(hour=hour, minute=random.randrange(60),
                         second=random.randrange(60), microsecond=random.randrange(10**6))
        if ts <= now:
            return ts


def http_log(ts, service, incident=False):
    endpoint = random.choice(SERVICES[service])
    method = random.choices(list(METHODS), weights=METHODS.values())[0]
    rt = round(random.lognormvariate(-1.8, 0.6), 3)          # ~0.15 s en moyenne
    status = random.choices([200, 201, 204, 400, 401, 403, 404, 500, 502, 503],
                            weights=[70, 8, 3, 4, 3, 1, 4, 3, 2, 2])[0]
    if incident:                                             # incident simulé
        rt = round(random.uniform(2.5, 8.0), 3)
        status = random.choice([500, 502, 503, 504, 200])
    level = "ERROR" if status >= 500 else "WARNING" if status >= 400 or rt > 2 else "INFO"
    return {
        "timestamp": ts.isoformat(timespec="milliseconds"),
        "level": level, "service": service, "source": "nginx",
        "http_method": method, "endpoint": endpoint, "status_code": status,
        "response_time": rt, "user_id": random.choice(USERS),
        "tenant": random.choice(TENANTS), "feature": FEATURES[service],
        "client_ip": fake.ipv4_public(), "sql_query": "",
        "message": f"{method} {endpoint} {status} {rt}s",
    }


def app_log(ts, service):
    level = random.choices(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                           weights=[15, 55, 15, 12, 3])[0]
    messages = {
        "DEBUG": f"Cache miss pour la clé {fake.uuid4()[:8]}",
        "INFO": random.choice(["Utilisateur connecté", "Projet créé", "Export terminé",
                               "Abonnement renouvelé", "Tâche mise à jour"]),
        "WARNING": random.choice(["Quota d'API bientôt atteint", "Retry sur le service email",
                                  "Session expirée"]),
        "ERROR": random.choice(["TimeoutError: database did not respond in 5s",
                                "KeyError: 'tenant_id'", "ConnectionError vers Redis",
                                "Échec de génération de la facture"]),
        "CRITICAL": random.choice(["Pool de connexions DB épuisé",
                                   "Service de paiement indisponible"]),
    }
    return {
        "timestamp": ts.isoformat(timespec="milliseconds"), "level": level,
        "service": service, "source": "flask", "http_method": "", "endpoint": "",
        "status_code": "", "response_time": "", "user_id": random.choice(USERS),
        "tenant": random.choice(TENANTS), "feature": FEATURES[service],
        "client_ip": "", "sql_query": "", "message": messages[level],
    }


def db_log(ts):
    duration = round(random.uniform(1.0, 6.0), 3)
    return {
        "timestamp": ts.isoformat(timespec="milliseconds"),
        "level": "WARNING" if duration < 4 else "ERROR", "service": "database",
        "source": "db", "http_method": "", "endpoint": "", "status_code": "",
        "response_time": duration, "user_id": "", "tenant": random.choice(TENANTS),
        "feature": "", "client_ip": "", "sql_query": random.choice(SLOW_QUERIES),
        "message": f"Requête lente ({duration}s)",
    }


def generate(rows, days, incident):
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
    # incident : hier à 14 h (toujours dans le passé)
    incident_start = start + timedelta(days=max(days - 2, 0), hours=14)
    logs = []
    for _ in range(rows):
        ts = random_time(start, days, now)
        kind = random.choices(["http", "app", "db"], weights=[70, 25, 5])[0]
        service = random.choices(list(SERVICES), weights=[45, 20, 15, 12, 8])[0]
        if kind == "http":
            in_incident = (incident and service == "billing"
                           and incident_start <= ts < incident_start + timedelta(minutes=30))
            logs.append(http_log(ts, service, in_incident))
        elif kind == "app":
            logs.append(app_log(ts, service))
        else:
            logs.append(db_log(ts))
    if incident:   # 300 requêtes concentrées pendant l'incident
        for _ in range(300):
            ts = incident_start + timedelta(seconds=random.randrange(1800))
            logs.append(http_log(ts, "billing", incident=True))
    logs.sort(key=lambda log: log["timestamp"])
    return logs


def write(logs, fmt, out):
    if fmt == "csv":
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_MINIMAL,
                               lineterminator="\n")
            w.writeheader()
            w.writerows(logs)
    else:  # une ligne JSON par log (format NDJSON lu par Logstash)
        with open(out, "w", encoding="utf-8") as f:
            for log in logs:
                clean = {k: v for k, v in log.items() if v != ""}
                f.write(json.dumps(clean, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Générateur de logs SaaSWatch")
    p.add_argument("--rows", type=int, default=5000, help="nombre de logs")
    p.add_argument("--days", type=int, default=7, help="période couverte (jours)")
    p.add_argument("--format", choices=["csv", "json"], default="csv")
    p.add_argument("--out", default="../data/uploads/logs.csv")
    p.add_argument("--incident", action="store_true", help="ajouter un incident billing")
    p.add_argument("--seed", type=int, help="graine pour des résultats reproductibles")
    a = p.parse_args()
    if a.seed is not None:
        random.seed(a.seed)
        Faker.seed(a.seed)
    data = generate(a.rows, a.days, a.incident)
    write(data, a.format, a.out)
    print(f"{len(data)} logs générés dans {a.out}")