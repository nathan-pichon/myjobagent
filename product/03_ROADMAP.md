# Roadmap — MyJobAgent

> Conçue pour être **exécutée par un agent type Claude Code**. Chaque tâche est atomique, testable,
> avec critères d'acceptation. Format : `[ ]` à faire · Épics ordonnées par dépendance.
> Convention : commits petits, une branche par épic, tests avant de cocher.

## Principes d'exécution (pour l'agent)
- Réutiliser le moteur existant (`autonomous_job_hunter.py`, `utils/`) — **refactor, pas rewrite**.
- Chaque PR doit laisser `jobhunt doctor` au vert.
- Pas de secret en dur ; clés LLM via env/keychain local. **Jamais de clé API saisie côté web.**
- Garder la convention langue : instructions/logs EN, résumés FR (cf. CLAUDE.md).

---

## ⟳ Révisé après revue — ordre et séquencement

Les revues (cf. `04_REVIEWS_SYNTHESIS.md`) imposent deux changements structurels avant tout le reste :

1. **Phase −1 d'abord** : prouver la qualité du matching (Go/No-Go) avant d'investir dans l'UI/web.
2. **Dashboard (P3) AVANT web (P2)** : la rétention avant l'acquisition.

**Chemin critique révisé :** `P−1 (éval) → P0 (moteur+CLI) → P1-core (profil manuel + scoring explicable + dédup + feedback 👍👎) → [GATE qualité] → P3 (dashboard local + digest) → [GATE rétention] → P2 (web) → P4 (desktop) → P5 (communauté).`

Sont **sortis du MVP v0.1** (vers v0.2+) : configurateur web, import CV, multi-LLM cloud. MVP = CLI + config fichier + scoring explicable + dashboard local + Ollama seul.

---

## Phase −1 — Prouver le matching (GATE produit) 🔴
**La chose la plus importante de toute la roadmap. ~1 semaine. À faire avant tout refactor.**

- [x] **−1.1** Jeu d'éval : harnais (`eval/run.py`) + seed (`eval/seed_from_memory.py`) + **dataset curé labellisé** (`eval/build_dataset_v1.py` → 27 offres, 12 match / 15 no_match).
- [x] **−1.2** Harnais d'éval : `python -m eval.run` calcule précision/rappel/F1/accuracy + stabilité (stdev) + MAE ; écrit `eval/report.json`.
- [x] **−1.3** Comparaison multi-modèles : gemma4:e2b / gemma4:e4b (Ollama ; baseline cloud via openai-compat dispo).
- [x] **−1.4** **GATE FRANCHIE ✅** : e2b **0,80**, e4b **0,71**, rappel **1,0** sur les deux. e2b échouait avant durcissement → **prompt Recruteur durci** (HARD GATES stack/location/not-a-job génériques). **D1 tranchée** : min `gemma4:e2b`, recommandé `gemma4:e4b`, max 7B+/cloud. Détail : `eval/RESULTS.md` + `eval/report.json`.
- [ ] **−1.5** *(amélioration continue)* Augmenter le dataset avec de vraies offres scrapées + profils non-backend ; viser 50+ offres, 2-3 répétitions (mesurer σ).

---

## Phase 0 — Fondations & extraction du moteur (v0.1-alpha) — ✅ FAIT
**But : transformer le monolithe en moteur configurable + CLI, sans changer le comportement.**

- [x] **0.1** Package `jobhunt/` créé. Logique de `autonomous_job_hunter.py` déplacée dans `jobhunt/engine/` (scout, trieur, recruteur, filters, scrapers, loop). *Scrapers importés en lazy ; le monolithe reste en place comme référence.*
- [x] **0.2** Schéma `jobhunt.config.json` (Pydantic, `schema_version` 1.0) : `profile`, `llm`, `search`, `sources`, `scoring`, `filters`. `jobhunt validate` OK/erreurs explicites.
- [x] **0.3** Config hardcodée externalisée → `jobhunt/config.py` (`default_config()`), pilotée par fichier. Aucun critère en dur dans le moteur.
- [x] **0.4** Couche LLM `jobhunt/llm/` abstraite (Protocol) : Ollama (défaut), OpenAI-compat (OpenAI/LM Studio/Mistral/Groq), Anthropic. Clés lues **en local** uniquement. Modèle changé via config.
- [x] **0.5** CLI `jobhunt` (Typer) : `init`, `validate`, `doctor`, `run`, `dashboard`, `version`.
- [x] **0.6** Persistance SQLite (`jobhunt/store/`) : tables `jobs` (+ breakdown, status pipeline, feedback 👍👎), `runs`, `visited`, `searches`. Dédup par clé titre+entreprise+lieu.
- [x] **0.7** Packaging `pyproject.toml` (hatchling) : `pip install -e .`, extra `[scrape]`, entry point `jobhunt`. README quickstart.
- [x] **0.8** `jobhunt doctor` : checklist actionnable (Python, config, extra scrape, LLM joignable avec message « ollama pull … », warning LinkedIn opt-in).
- [x] **0.9** Tests offline (pytest, **12 verts**) : util/JSON, dédup, normalisation Recruteur, b64 roundtrip, dashboard, digest, why-not, rejections. Validé end-to-end sur `gemma4:e2b/e4b`.
- [x] **0.10** Import legacy `memory.json` → SQLite (`jobhunt/store/migrate.py`) : 81 matches + 974 URLs importés, dédup (78 offres). **Supervisor branché** : `jobhunt/engine/supervisor.py` consomme le feedback 👎 + commandes `jobhunt feedback`/`jobhunt tune` (opt-in, jamais silencieux, garde-fous anti-dégénérescence). CI/CD GitHub Actions (`.github/workflows/ci.yml` + `deploy-web.yml`).

## Phase 1 — Profil, CV & scoring explicable (v0.1)
**But : passer de critères génériques à un matching personnalisé et transparent.**

- [ ] **1.1** Modèle de profil étendu **saisi à la main** (séniorité, années d'xp, must-have/nice-to-have, exclusions, dispo, TJM/salaire cible). *Pas d'import CV au MVP.*
- [ ] **1.3** Enrichir le prompt Recruteur avec le profil ; sortie structurée du **détail du rubric par sous-critère** + « ce qui manque », avec **gap bloquant vs cosmétique** et items **relatifs au profil de l'user**. *AC : chaque match a un `breakdown` JSON (stack/role/loc/contract + gaps typés).*
- [ ] **1.4** Déduplication cross-plateformes (hash titre+entreprise+lieu, fuzzy). *AC : doublons fusionnés en 1 carte avec ses sources.* **(au MVP, pas optionnel)**
- [ ] **1.5** Détection fraîcheur/repost (date offre, repost flag). *AC : badge « fraîche/ancienne » sur la carte.*
- [ ] **1.6** **Feedback 👍/👎 par match** stocké en SQLite (seule source de vérité locale sur la qualité ; carburant du Supervisor). *AC : un avis utilisateur est persisté et requêtable.*
- [x] **1.7** **Sourcing fiabilisé** : couche `jobhunt/sources/` (abstraction `Source`/`Offer`, registry ordonné). **France Travail API v2** (officielle, OAuth2, texte inclus → zéro scraping) + **flux RSS** (`rss.py`, RSS 2.0/Atom en stdlib, texte souvent inclus, cache par run + pré-filtre mots-clés) en tête ; **web search en repli** avec retry/backoff. Boucle refactorée : offres avec texte scorées direct, URL-only scrapées. Si une source tombe, le run continue. RSS configurable (dashboard ⚙ + config `rss_feeds` + web statique). LinkedIn/Indeed OFF par défaut. `doctor` affiche l'état par source. Credentials FT lus **en local**. Testé (parsing RSS/Atom, mapping FT, ordre, cache, e2e mocké, API + panneau jsdom). **20 tests verts.**
- [ ] **1.2** *(déplacé hors MVP → v0.2)* Import CV : parsing PDF/DOCX local → compétences/séniorité. *AC : un CV uploadé pré-remplit le profil.*

## Phase 2 — Configurateur web + génération du package (v0.2)
**But : le web qui définit profil+recherche et produit la config/commande.**

- [ ] **2.1** Init du projet web **statique** (Astro + Tailwind + `design-tokens.css`), **SPA 100 % client-side, zéro backend**. *AC : déployable sur GitHub Pages OU Vercel sans serverless function ; aucun appel réseau sortant.*
- [ ] **2.2** Landing (héros faisceau, promesse, privacy, 3 étapes, GitHub). *AC : Lighthouse ≥ 95.*
- [ ] **2.3** ConfigWizard 5 étapes (Profil→Critères→CV→LLM→Générer) avec aperçu live. *AC : produit un `jobhunt.config.json` valide vs schéma 0.2.*
- [ ] **2.4** Écran génération adaptatif (cf. `02_DESIGN.md §8.1`) : **téléchargement `jobhunt.config.json`** (`Blob`) + variante `--b64` inline + OS-aware. *AC : la config produite côté client importe correctement dans la CLI.*
- [ ] **2.5** Import local : `jobhunt init <fichier|--b64 …>` décode et valide la config localement ; en fin d'import, **ouvre le dashboard local** (`http://localhost:4321`). *AC : web→local sans compte, sans serveur, sans polling depuis la SPA.*
- [ ] **2.6** Pages docs (quickstart, LLM, troubleshooting). *AC : un nouvel utilisateur va du web au 1er match en < 15 min.*

## Phase 3 — Dashboard local & expérience quotidienne (v0.3)
**But : l'écran où l'utilisateur vit chaque jour.**

- [x] **3.1** Dashboard servi par un **mini-serveur local 127.0.0.1** (`jobhunt server`/`dashboard`, stdlib, zéro dépendance, jamais exposé en ligne — accord porteur : local OK, pas de host externe). API `/api/move` + `/api/feedback` écrivent direct en SQLite ; sécurité token par session + contrôle d'Origin. Drag & drop et 👍/👎 **vraiment persistants**. Mode `--static` conservé en fallback (localStorage + commande). Testé (serveur in-process + jsdom).
- [ ] **3.2** Grille de JobCards + filtres/tri (score, source, lieu, fraîcheur). *AC : filtrage instantané.*
- [ ] **3.3** Vue détail offre + `ScoreBreakdown` complet. *AC : « pourquoi ce score » visible.*
- [x] **3.4** Pipeline Kanban (Trouvé→Intéressé→Postulé→Entretien→Offre/Refus). 6 colonnes + CLI `jobhunt move`/`pipeline`, persistant SQLite. **Drag & drop** entre colonnes (+ boutons fallback clavier), **clic carte → modale détail** (ScoreBreakdown complet + bouton « Voir l'offre »), **lien « Voir l'offre ↗ » sur chaque carte**. Persistance optimiste localStorage + commande `jobhunt move` auto-copiée (zéro backend). Vérifié par exécution réelle en jsdom (drag/modale/Échap/persistance/lien).
- [ ] **3.5** `HuntProgress` (radar/sonar + compteurs live) pendant le run. *AC : feedback temps réel.*
- [x] **3.6** `jobhunt watch` (+ `--once`, `--every`, `--notify`) : chasse planifiée + **digest** verdict-first + notification OS native (macOS/Linux). Digest aussi affiché en fin de `jobhunt run`. `jobhunt/engine/digest.py`, testé. *Livré tôt comme prévu (feature de rétention n°1).*
- [~] **3.7** ~~Génération de pitch/lettre par LLM~~ — **ÉCARTÉ (décision porteur, sess. 3)**. La génération de texte par IA est trop impersonnelle et reconnaissable ; elle dessert le candidat et brouille le positionnement (MyJobAgent aide à *trouver et décider*, pas à écrire à sa place). Voir `01_PRODUCT_SCOPE.md` → Won't. *Alternative possible plus tard : aide non-générative (points clés à mentionner, gaps à adresser) — à valider, pas de rédaction auto.*
- [ ] **3.8** États designés nommément : premier run, chasse finie 0 match (CTA « élargis tes critères »), Ollama injoignable, code expiré. *AC : aucun écran mort.*
- [x] **3.9** Vue **« Why-not »** : table `rejected` en SQLite + motif inféré du breakdown (lieu/stack/rôle/seuil/expirée), section repliée dans le dashboard avec récap par motif. La boucle enregistre chaque rejet. Testé.
- [ ] **3.10** `HuntProgress` robuste longue durée : étape courante, ETA, log défilant, état « ça travaille » pendant les pauses, `aria-live`. *AC : pas de faux blocage perçu sur une chasse de 20 min.*
- [x] **3.11** **Réglages dans le dashboard local** (mode serveur) : panneau ⚙ avec (a) **clés & identifiants** (clé LLM, France Travail) stockés en local via `jobhunt/secrets.py` (fichier 0600, env-wins, jamais en ligne) — API `/api/secrets` ; (b) **chasse automatique** (activer/intervalle/notif + « Lancer maintenant ») via un `Scheduler` thread local + API `/api/schedule` (persistée dans la config) `/api/run-now` `/api/settings`. Schéma config : bloc `schedule`. Secrets résolus par tous les providers LLM + France Travail. Testé (store 0600, scheduler, routes API, panneau jsdom). 18 tests verts.

## Phase 4 — Package all-in-one desktop (v0.4)
**But : le « double-clic » pour les non-techniques.**

- [ ] **4.1** App Tauri embarquant le moteur Python (sidecar) + webview du dashboard. *AC : `.dmg`/`.exe`/`.AppImage` lance tout sans terminal.*
- [ ] **4.2** Post-install : téléchargement Chromium + check Ollama, onboarding guidé. *AC : 1er run réussi depuis l'app.*
- [ ] **4.3** Auto-update + signature des binaires. *AC : releases GitHub signées, MAJ in-app.*
- [ ] **4.4** Multi-providers LLM complet (LM Studio, OpenAI, Anthropic, Mistral, Groq) avec test connexion. *AC : bascule de provider depuis Réglages.*

## Phase 5 — Communauté & open-core (v1.0)
- [ ] **5.1** Galerie de templates de recherche partageables (import en 1 clic).
- [~] **5.2** Système de « sources » extensible. **Base posée** (P1.7) : abstraction `Source`/`Offer` + registry dans `jobhunt/sources/`, une nouvelle source s'ajoute sans toucher au cœur. *Reste : doc contributeur + chargement de sources tierces en plugin.*
- [ ] **5.3** Multi-profils.
- [ ] **5.4** Sync chiffrée optionnelle entre machines (premium, opt-in).
- [ ] **5.5** i18n EN. Gouvernance OSS (CONTRIBUTING, CoC, licence, issues templates).

---

## Jalons & dépendances ⟳ révisés
```
P−1 (éval/GATE) ──► P0 ──► P1-core ──► [GATE qualité] ──► P3 ──► [GATE rétention] ──► P2 ──► P4 ──► P5
```
- **v0.1** = P−1 + P0 + P1-core + P3-core (moteur configurable + matching explicable + dashboard local + digest CLI). MVP réel, Ollama seul, sans web ni CV.
- **v0.2** = import CV (1.2) + dashboard complet (Kanban) + multi-LLM cloud.
- **v0.3** = + P2 (web configurateur) ← *seulement après preuve de rétention*.
- **v0.4** = + P4 (desktop grand public).
- **v1.0** = + P5 (communauté/open-core).

**Deux GATES bloquantes** : (1) qualité matching ≥ 70 % de précision perçue avant P3 ; (2) rétention J+7 ≥ 40 % sur 10–20 beta-users avant d'investir P2.

## Définition de « Done » globale
README clair · `jobhunt doctor` vert sur 3 OS · time-to-first-match < 15 min · tests sur le moteur · licence OSS · privacy vérifiable (aucun appel réseau sortant non opt-in).
