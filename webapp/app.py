"""SaaSWatch — application Flask (Sprint 2 : vérification de l'environnement).

Pour l'instant, l'application vérifie seulement qu'elle communique avec
Elasticsearch, MongoDB et Redis. Les vraies pages arrivent au Sprint 3.
"""
import os
from flask import Flask, jsonify
from elasticsearch import Elasticsearch
from pymongo import MongoClient
import redis

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev")

es = Elasticsearch(os.getenv("ES_HOST", "http://elasticsearch:9200"))
mongo = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=2000)
cache = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))


def check(fn):
    """Exécute un test de connexion et renvoie 'ok' ou le message d'erreur."""
    try:
        fn()
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"erreur : {exc.__class__.__name__}"


@app.get("/health")
def health():
    """Simple test utilisé par le healthcheck Docker."""
    return jsonify(status="ok")


@app.get("/status")
def status():
    """Vérifie la connexion à chaque service de l'architecture."""
    services = {
        "elasticsearch": check(lambda: es.info()),
        "mongodb": check(lambda: mongo.admin.command("ping")),
        "redis": check(lambda: cache.ping()),
    }
    try:
        nb_logs = es.count(index="logs-saas-*")["count"]
    except Exception:  # noqa: BLE001
        nb_logs = 0
    tout_ok = all(v == "ok" for v in services.values())
    return jsonify(application="SaaSWatch", services=services,
                   logs_indexes=nb_logs, statut="opérationnel" if tout_ok else "dégradé"), (200 if tout_ok else 503)


@app.get("/")
def index():
    return ("<h1>SaaSWatch</h1><p>Environnement opérationnel. "
            "Voir <a href='/status'>/status</a>.</p>")
