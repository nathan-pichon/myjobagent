# 🔦 MyJobAgent

> Agent de recherche d'emploi **open-source, local-first**. Décris ton job idéal une fois ;
> ton agent le cherche, le score contre **ton** profil, t'explique pourquoi — **et rien ne quitte ta machine**.

MyJobAgent tourne **chez toi**, avec **ton propre LLM** (Ollama par défaut, ou une clé API).
Un configurateur web 100 % statique sert juste à générer ta config ;
toute la chasse et tes données restent en local.

## Pourquoi
- **Matching explicable** : « 82/100 — il te manque juste Kubernetes » (détail du rubric Stack/Rôle/Lieu/Contrat).
- **Privacy par défaut** : aucune donnée envoyée, bring-your-own-LLM.
- **DX soignée** : une CLI claire, un dashboard local, des erreurs actionnables.

> **⚠️ Statut : alpha.** Le moteur, la CLI et le dashboard local fonctionnent. Le projet
> n'est pas encore publié sur PyPI ni déployé en ligne — on installe depuis les sources
> (ci-dessous). Le configurateur web se lance en local (`web/`, voir [`web/README.md`](web/README.md)).

## Prérequis
- **Python ≥ 3.11**
- **[Ollama](https://ollama.com)** installé et lancé (pour le LLM local par défaut). Ou une clé API (OpenAI/Anthropic/…).
- **~3 Go d'espace disque** : ~2 Go pour le modèle `gemma4:e2b`, ~150 Mo pour Chromium (scraping).
- ⏱️ La 1ʳᵉ install prend ~10–15 min (téléchargements). Une chasse tourne en arrière-plan ;
  les LLM locaux sont lents (~quelques dizaines de secondes par offre), c'est normal — laisse l'agent travailler.

## Installation (depuis GitHub)
> Pas encore publié sur PyPI : on installe depuis les sources. C'est 5 commandes.

```bash
# 1. Récupérer le projet
git clone https://github.com/nathan-pichon/myjobagent.git
cd jobbeacon

# 2. Environnement Python isolé
python3 -m venv .venv
source .venv/bin/activate            # Windows : .venv\Scripts\activate

# 3. Installer MyJobAgent + le moteur de scraping
pip install -e '.[scrape]'
playwright install chromium          # navigateur headless, 1ʳᵉ fois

# 4. Préparer le LLM local (dans un autre terminal, ou en arrière-plan)
ollama serve &
ollama pull gemma4:e2b               # ~2 Go ; modèle léger validé par notre éval qualité
```

## Premier lancement
```bash
mja init --seed     # crée une config de démarrage (jobhunt.config.json)
mja doctor          # vérifie que tout est prêt (Python, LLM, sources…) — vise du vert
mja run             # première chasse
mja dashboard       # ouvre le tableau de bord local (http://127.0.0.1:4321)
```

`mja doctor` est ton ami : il liste précisément ce qui manque et la commande pour corriger.

> **Adapter à ton profil** : `mja init --seed` génère une config orientée *backend Node.js
> / Côte d'Azur* (l'exemple d'origine). Édite `jobhunt.config.json` à la main, ou regénère-la
> avec le configurateur web, puis `mja init ~/Downloads/jobhunt.config.json`.

### Modèle LLM : lequel choisir ?
- `gemma4:e2b` (défaut) — léger (~2 Go), rapide, suffisant. **Idéal pour démarrer.**
- `gemma4:e4b` — un peu plus précis sur les cas ambigus.
- `qwen2.5:7b` ou une **clé API cloud** (OpenAI/Anthropic…) — qualité maximale.

Change de modèle dans `jobhunt.config.json` (`llm.model`) ou via ⚙ Réglages dans le dashboard.
Détails et chiffres de qualité : [`eval/RESULTS.md`](eval/RESULTS.md).

### Tableau de bord local
`mja dashboard` démarre un petit serveur **sur `127.0.0.1` uniquement** (jamais exposé
au réseau) : le Kanban (drag & drop) et le feedback 👍/👎 s'enregistrent directement dans
ta base locale. Aucun backend en ligne. `--static` produit juste un fichier HTML (le
glisser-déposer y est alors mémorisé dans le navigateur + commande `mja move` à coller).

**Réglages (⚙, dans le dashboard local)** — tout se configure sans toucher au terminal :
- **Clés & identifiants** (clé API du LLM cloud, identifiants France Travail) — saisis et
  stockés **en local** (fichier `0600`), jamais envoyés en ligne. *(Le configurateur web
  *statique* ne demande jamais de clé ; seul le dashboard *local* le fait, car il tourne sur ta machine.)*
- **Chasse automatique** — active une chasse récurrente toutes les X heures + notification,
  ou « ▶ Lancer maintenant ». Géré par un planificateur local tant que le dashboard tourne.

Résolution des secrets : variable d'environnement d'abord, sinon le fichier local. Une clé
définie par variable d'env est verrouillée dans l'UI (affichée comme telle, non modifiable).

Suivi en CLI aussi : `mja move <url> <statut>` · `mja pipeline` ·
`mja feedback <url> --up/--down`.

### Sources d'offres (sourcing fiabilisé)
Le sourcing est en couches : **les sources officielles d'abord, la recherche web en repli.**

| Source | Type | Fiabilité | Texte de l'offre |
|---|---|---|---|
| **France Travail** (API v2 officielle) | API REST, OAuth2 | élevée, légale | **inclus** → pas de scraping |
| **Flux RSS** de recrutement | RSS 2.0 / Atom | **élevée, stable** | **souvent inclus** → pas de scraping |
| Web (DuckDuckGo + scraping) | recherche large | variable (rate-limit) | scrapé (Playwright), avec retry/backoff |
| LinkedIn / Indeed | — | **OFF par défaut** (CGU anti-scraping) | opt-in explicite |

Les **flux RSS** sont **pré-remplis** avec une liste par défaut (WeWorkRemotely, Remotive,
RemoteOK, Himalayas…) que tu **vois et modifies** dans le dashboard local (⚙ Réglages) :
ajoute/supprime des flux au format `Nom | url`, ou clique « ↺ Restaurer les flux par défaut ».
Si tu les supprimes tous, c'est respecté (pas de réinjection). Un flux est récupéré une fois
par run puis filtré localement par mots-clés ; le Recruteur fait le scoring précis ensuite.

Les offres qui arrivent **avec leur texte** (France Travail) sont scorées directement —
plus fiable *et* plus rapide (zéro navigateur). Si une source tombe, le run continue sur les autres.

**Activer France Travail** (recommandé) : crée une appli sur [francetravail.io](https://francetravail.io),
abonne-toi à « Offres d'emploi v2 », puis exporte les identifiants **en local** (jamais sur le web) :
```bash
export FRANCE_TRAVAIL_CLIENT_ID=...
export FRANCE_TRAVAIL_CLIENT_SECRET=...
```
`mja doctor` affiche l'état de chaque source.

## Architecture
```
jobhunt/
  config.py        # schéma jobhunt.config.json (Pydantic) — contrat web ↔ local
  llm/             # bring-your-own-LLM (ollama, openai-compat, anthropic)
  sources/         # couche sourcing : france_travail (API) · web_search (fallback)
  engine/          # scout · trieur · recruteur · filters · scrapers · loop
  store/           # SQLite local (jobs, pipeline, feedback 👍👎, runs)
  dashboard/       # rendu du tableau de bord local + serveur 127.0.0.1
  prompts/         # templates Jinja2 des agents
eval/              # harnais d'éval du matching (Phase −1, GATE qualité)
product/           # dossier produit (scope, design, roadmap, revues, décisions)
```

## Statut
Alpha (v0.1). Fonctionnel : moteur, CLI, dashboard local interactif, sources (France Travail /
RSS / web), digest, chasse planifiée, feedback. À venir : publication PyPI, déploiement du
configurateur web, app desktop. Feuille de route : [`product/03_ROADMAP.md`](product/03_ROADMAP.md).

## Contribuer
Voir [`CONTRIBUTING.md`](CONTRIBUTING.md). Principe directeur : **local-first**, aucun backend
externe en ligne, aucun secret côté web statique.

## Licence
AGPL-3.0-or-later. Voir [`LICENSE`](LICENSE).
