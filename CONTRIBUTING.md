# Contribuer à MyJobAgent

Merci de ton intérêt ! MyJobAgent est **local-first** : tout tourne chez l'utilisateur,
aucun backend externe hébergé en ligne. Garde ce principe en tête pour toute contribution.

## Démarrer en dev
```bash
git clone https://github.com/nathan-pichon/myjobagent.git
cd myjobagent
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[scrape,dev]'
playwright install chromium
pytest -q                       # la suite doit être verte
```

## Architecture (vue d'ensemble)
- `jobhunt/config.py` — schéma de config (contrat web ↔ moteur). **À ne pas casser.**
- `jobhunt/sources/` — sources d'offres (France Travail, RSS, web). **Ajouter une source ici**
  sans toucher au cœur : implémente `Source` (voir `base.py`).
- `jobhunt/engine/` — boucle Scout → Trieur → Recruteur.
- `jobhunt/store/` — SQLite local. `jobhunt/server.py` — serveur dashboard 127.0.0.1.
- `eval/` — harnais d'éval qualité du matching (GATE). Faire tourner après tout changement de prompt.

## Règles
- **Aucun secret en dur**, aucune clé demandée côté web statique (uniquement en local). Voir `jobhunt/secrets.py`.
- **Pas de backend externe en ligne** : le web doit rester 100 % statique (déployable GitHub Pages/Vercel).
- Langue : instructions/logs des agents en **anglais**, résumés utilisateur en **français** (cf. prompts).
- Ajoute un test dans `tests/test_core.py` pour tout nouveau comportement. Garde la suite verte.
- Si tu changes un prompt du Recruteur, relance `python -m eval.run` et vérifie que la précision reste ≥ 0,70.

## Ajouter une source d'offres
1. Crée `jobhunt/sources/ma_source.py` avec une classe implémentant `Source` (`name`, `available`, `fetch`).
2. Si elle fournit le texte de l'offre, renseigne `Offer.text` → pas de scraping nécessaire.
3. Enregistre-la dans `jobhunt/sources/base.py:get_sources()` (sources fiables avant le web).
4. Ajoute un toggle dans la config (`SourcesConfig`) si pertinent, + un test.

## Proposer un changement
- Branche dédiée, PR claire, suite de tests verte.
- Décris l'impact sur le local-first / la privacy si applicable.
