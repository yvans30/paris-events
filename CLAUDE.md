# Paris Events Weekly - Veille Tech & Finance

Ce projet est execute automatiquement chaque lundi par un trigger Claude Code.
L'objectif est de trouver les evenements tech et finance a Paris pour les 2 prochaines semaines.

## Instructions d'execution

### 1. Calculer les dates

- `DATE_FROM` = date du jour (format YYYY-MM-DD)
- `DATE_TO` = date du jour + 14 jours

### 2. Lancer le pipeline Python

```bash
cd /home/user/paris-events
python fetch_events.py --from DATE_FROM --to DATE_TO | python send_report.py
```

Ce pipeline :
- Interroge les APIs Eventbrite et Meetup pour trouver les evenements tech/finance a Paris
- Filtre selon les domaines et le prix (< 50 EUR) definis dans `config.json`
- Envoie directement un email HTML a `yvankiegain@gmail.com`
- Aucun fichier rapport n'est sauvegarde dans le repo

### 3. Variables d'environnement requises

Les credentials sont lus depuis l'environnement (configures dans `.claude/settings.local.json`) :

| Variable | Description |
|----------|-------------|
| `EVENTBRITE_TOKEN` | Token API Eventbrite (OAuth personal token) |
| `MEETUP_API_KEY` | Token API Meetup |
| `GMAIL_USER` | Adresse Gmail expeditrice |
| `GMAIL_APP_PASSWORD` | App Password Gmail (16 caracteres) |

### 4. Si le pipeline echoue

Si les APIs sont inaccessibles ou ne retournent aucun resultat, completer avec WebSearch :
- `"evenements tech Paris cette semaine"` + date du jour
- `"meetup IA machine learning Paris"` + mois en cours
- `"hackathon Paris"` + mois en cours
- `"evenement fintech finance Paris"` + mois en cours

Puis passer les resultats manuellement a `send_report.py` via stdin (JSON array).

### 5. Notification si aucun evenement

Si le JSON retourne un tableau vide `[]`, `send_report.py` envoie quand meme un email avec :
"Aucun evenement tech/finance pertinent trouve a Paris pour les 2 prochaines semaines. Je reessaierai la semaine prochaine."
