# Paris Events Weekly - Veille Tech & Finance

Ce projet est execute automatiquement chaque lundi par un trigger Claude Code remote.
L'objectif est de trouver les evenements tech et finance a Paris pour les 2 prochaines semaines.

## Instructions d'execution

### 1. Calculer les dates

- `DATE_FROM` = date du jour (format YYYY-MM-DD)
- `DATE_TO` = date du jour + 14 jours

### 2. Lancer le pipeline Python

```bash
cd /Users/yvank/Documents/paris-events
python fetch_events.py --from DATE_FROM --to DATE_TO
```

Le pipeline interroge Eventbrite (API + scraping fallback), Meetup (API) et Luma (scraping).
Il filtre par domaines tech/finance et prix (< 50 EUR), deduplique, et retourne un JSON sur stdout.

### 3. Evaluer le resultat et envoyer l'email

Lire le JSON de sortie du pipeline :

- **Si >= 3 evenements** : piper directement dans `send_report.py` :
  ```bash
  python fetch_events.py --from DATE_FROM --to DATE_TO | python send_report.py
  ```

- **Si < 3 evenements** : completer avec WebSearch + WebFetch (voir section 5), merger les resultats avec ceux du pipeline, puis passer le JSON complet a `send_report.py` via stdin.

L'email est envoye par SMTP via `send_report.py`. NE PAS utiliser Gmail MCP (il ne cree que des brouillons).

### 4. Variables d'environnement requises

Les credentials sont lus depuis l'environnement :

| Variable | Description |
|----------|-------------|
| `EVENTBRITE_TOKEN` | Token API Eventbrite (OAuth personal token) |
| `MEETUP_API_KEY` | Token API Meetup |
| `GMAIL_USER` | Adresse Gmail expeditrice |
| `GMAIL_APP_PASSWORD` | App Password Gmail (16 caracteres) |
| `GMAIL_RECIPIENTS` | Liste des destinataires separes par des virgules |

### 5. Fallback WebSearch (si < 3 events du pipeline)

Si le pipeline retourne moins de 3 evenements, completer avec ces recherches :
- `"evenements tech Paris cette semaine"` + date du jour
- `"meetup IA machine learning Paris"` + mois en cours
- `"conference data science Paris"` + mois en cours
- `"hackathon Paris"` + mois en cours
- `"evenement fintech finance Paris"` + mois en cours
- `"conference finance investissement Paris"` + mois en cours
- `"afterwork networking tech finance Paris"` + mois en cours

Pour les resultats prometteurs, utiliser WebFetch pour extraire les details (date, lieu, prix, lien).
Filtrer : uniquement Paris, 2 prochaines semaines, tech ou finance, gratuit ou < 50 EUR.
Formater en JSON array avec les champs : title, date, time, venue, address, type, price, url, description, source.
Merger avec les events du pipeline, puis passer le tout a `send_report.py` via stdin.

### 6. Notification si aucun evenement

Si le JSON retourne un tableau vide `[]`, `send_report.py` envoie quand meme un email avec :
"Aucun evenement tech/finance pertinent trouve a Paris pour les 2 prochaines semaines."
