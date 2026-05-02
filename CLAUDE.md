# Paris Events Weekly - Veille Tech & Finance

Ce projet est execute automatiquement chaque lundi par un trigger Claude Code.
L'objectif est de trouver les evenements tech et finance a Paris pour les 2 prochaines semaines.

## Instructions d'execution

### 1. Lire la configuration

Lire `config.json` pour obtenir les domaines, types d'events, email, et sources.

### 2. Rechercher les evenements

Effectuer plusieurs recherches web (`WebSearch`) pour couvrir un maximum de sources :

**Recherches a effectuer :**
- `"evenements tech Paris cette semaine"` + date du jour
- `"meetup IA machine learning Paris"` + mois en cours
- `"conference data science Paris"` + mois en cours
- `"hackathon Paris"` + mois en cours
- `"evenement fintech finance Paris"` + mois en cours
- `"afterwork networking tech Paris"` + mois en cours
- `site:eventbrite.fr "Paris" "tech" OR "data" OR "IA"` + mois en cours
- `site:meetup.com "Paris" "tech" OR "developer" OR "data"` + mois en cours
- `site:lu.ma "Paris" "tech"` + mois en cours

Pour chaque recherche, utiliser `WebFetch` sur les pages de resultats les plus pertinentes pour extraire les details des evenements.

### 3. Filtrer les evenements

Garder uniquement les evenements qui :
- Se deroulent dans les **2 prochaines semaines**
- Sont a **Paris** (ou proche banlieue) en presentiel ou hybride
- Sont lies a un des **domaines** listes dans `config.json`
- Sont **gratuits ou a prix accessible** (< 50 EUR)

### 4. Generer le rapport

Creer un fichier `reports/YYYY-MM-DD.md` (date du jour) avec le format suivant :

```markdown
# Evenements Tech & Finance - Paris
## Semaine du DD/MM/YYYY au DD/MM/YYYY

### [Nom de l'evenement](lien_inscription)
- **Date** : Jour DD/MM a HHhMM
- **Lieu** : Nom du lieu, adresse
- **Type** : Meetup / Conference / Hackathon / Workshop / Networking
- **Prix** : Gratuit / XX EUR
- **Description** : Description courte (2-3 phrases)
- **Interet** : Networking / Skills / Les deux

---
(repeter pour chaque evenement)
```

Trier les evenements par date chronologique.

### 5. Envoyer par email

Utiliser le tool Gmail MCP pour envoyer un email a `yvankiegain@gmail.com` :

- **Sujet** : `Evenements Tech & Finance Paris - Semaine du DD/MM`
- **Corps** : Version HTML du rapport avec mise en forme lisible :
  - Titre en gras
  - Liens cliquables
  - Separateurs entre evenements
  - Emojis pour les types (meetup, conference, etc.)

### 6. Commiter le rapport

```bash
cd /Users/yvank/Documents/paris-events
git add reports/
git commit -m "rapport hebdo YYYY-MM-DD"
```

### 7. Notification

Si aucun evenement n'est trouve, envoyer quand meme un email avec le message :
"Aucun evenement tech/finance pertinent trouve a Paris pour les 2 prochaines semaines. Je reessaierai la semaine prochaine."
