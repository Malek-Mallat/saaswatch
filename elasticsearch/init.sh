#!/bin/sh
# Crée l'index template logs-saas au démarrage
echo "Création de l'index template logs-saas..."
curl -s -X PUT "http://elasticsearch:9200/_index_template/logs-saas" \
     -H "Content-Type: application/json" \
     --data-binary @/init/index_template.json
echo ""
echo "Index template créé."
