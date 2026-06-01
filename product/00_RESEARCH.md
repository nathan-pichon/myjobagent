# Recherche — De scripts épars à un produit SaaS « local-first »

> Document de cadrage. Lu en premier. Sert de base au scope, au design et à la roadmap.

## 1. État actuel (ce qu'on a)

| Élément | Fichier | Rôle |
|---|---|---|
| Boucle autonome | `autonomous_job_hunter.py` (~1000 l.) | Orchestration mono-thread, 200 steps max |
| Config | en-tête du `.py` (hardcodé) | `FLEXIBLE_CRITERIA`, `TARGET_PLATFORMS`, seuils |
| Agent Scout | `prompts/scout.md` | Génère les requêtes de recherche |
| Agent Trieur | `prompts/trieur.md` | Filtre les URLs (offre vs bruit) |
| Agent Recruteur | `prompts/recruteur.md` | Score l'offre /100 (Stack 40 + Rôle 20 + Lieu 25 + Contrat 15) |
| Supervisor | `utils/supervisor.py` | Réécrit les prompts entre runs |
| Scraping | `utils/browser_scrapers.py` | DuckDuckGo + Playwright stealth |
| Mémoire | `memory.json` / `memory_failures.json` | État + journal d'erreurs |
| Sortie | `dashboard_*.html` | Tableau des matches |
| LLM | Ollama `gemma3:e2b` | 100 % local |

**Constat** : moteur fonctionnel et déjà « local-first », mais (a) config non éditable sans toucher au code, (b) aucune notion de profil/CV utilisateur, (c) sortie en fichier HTML statique unique, (d) aucune installation pensée pour un non-développeur, (e) pas de suivi de candidature, (f) verrouillé sur un seul modèle Ollama.

## 2. Vision produit

> **Le SaaS ne chasse pas. Il configure, génère et accompagne. La chasse tourne chez l'utilisateur, avec SON LLM.**

C'est le pari différenciant : **local-first + privacy par défaut**. Aucune offre, aucun CV, aucune donnée de recherche ne transite par nos serveurs. Le web sert à *définir* (profil + recherche) et à *produire un package prêt à l'emploi* ; le moteur s'exécute sur la machine de l'utilisateur.

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│   WEB (le configurateur) │         │   MACHINE DE L'UTILISATEUR    │
│  ───────────────────────│         │  ────────────────────────────│
│  • Profil & CV           │  génère │  • Agent (moteur open source) │
│  • Critères de recherche │ ──────► │  • SON LLM (Ollama / clé API) │
│  • Choix du LLM          │ config  │  • Résultats 100 % locaux     │
│  • Téléchargement package│ +CLI    │  • Tableau de bord local      │
└─────────────────────────┘         └──────────────────────────────┘
        public, statique                   privé, chez l'utilisateur
```

## 2bis. Contrainte d'architecture — ZÉRO backend 🔴

> **Décision du porteur : tout se passe chez l'utilisateur ; côté hébergeur, uniquement du statique (GitHub Pages ou Vercel, sans serverless functions).**

Conséquences directes (toutes alignées avec le local-first, donc *renforçantes*) :

- **Le configurateur web est une SPA 100 % client-side.** Aucune donnée envoyée, aucune base, aucun endpoint. GitHub Pages suffit ; Vercel n'apporte que les preview-deploys (functions non nécessaires).
- **Pas de « code court » (`BEACON-7F3K`)** : il exigeait un serveur pour mapper code→config. Remplacé par un transfert 100 % local (cf. §3bis).
- **Templates communautaires** = simples fichiers JSON versionnés dans le repo, lus en `fetch` depuis GitHub Pages / raw GitHub. Pas de serveur.
- **Métriques** = locales uniquement (aucun serveur pour les recevoir). L'user les voit dans son dashboard ; rien ne sort.
- **CV parsing** = côté local (le LLM est local de toute façon) — pas dans la SPA statique.
- **Le seul vrai « serveur » est celui que le moteur lance en localhost** sur la machine de l'user pour servir le dashboard.

## 3. Trois modèles de distribution étudiés

| Modèle | DX | Public | Verdict |
|---|---|---|---|
| **A. One-liner CLI** `uvx jobhunt init` + config importée | excellent pour qui a un terminal | dev / tech | **MVP** |
| **B. App desktop** (Tauri) `.dmg`/`.exe`/`.AppImage` bundlant le moteur | zéro terminal, double-clic | grand public | **v1** (« all-in-one ») |
| **C. ZIP personnalisé** généré par le web | moyen (dépendances à installer) | intermédiaire | écarté (fragile) |

**Recommandation** : commencer par **A** (rapide, prouve la valeur), converger vers **B** comme vrai « package all-in-one » double-clic pour les chercheurs d'emploi non techniques.

## 3bis. Le pont web→local SANS serveur (3 mécanismes, par robustesse)

La SPA statique génère la config en mémoire (client-side) et la transmet au moteur local par un de ces moyens — **aucun ne touche un serveur** :

1. **Téléchargement de fichier** (défaut, le plus robuste) — la SPA produit `jobhunt.config.json` via `Blob`/`URL.createObjectURL` ; l'user lance `jobhunt init ~/Downloads/jobhunt.config.json`. Marche partout, taille illimitée (CV inclus).
2. **Config inline base64url** (configs courtes) — `jobhunt init --b64 eyJ...` (copier-coller d'une commande). Pratique mais limité (~2 ko utiles, illisible si long).
3. **Deep link `jobhunt://`** (si l'app desktop est installée) — un clic ouvre l'app pré-remplie. Idéal pour le grand public, dispo seulement avec le package B.

**Confirmation que ça a marché — sans que la SPA n'appelle le local.** Un navigateur en HTTPS (GitHub Pages/Vercel) **ne peut pas appeler `http://localhost` de façon fiable** (mixed-content + Private Network Access bloquent souvent le `fetch`). Donc on inverse : c'est **le moteur local qui ouvre le dashboard** (`http://localhost:4321`) dans le navigateur à la fin de `jobhunt init`. La confirmation vit en local, pas via un polling depuis la SPA. Le canon d'édition de config est d'ailleurs le **dashboard local lui-même** ; la SPA statique ne sert qu'à la découverte + la première config.

## 4. Le LLM de l'utilisateur (« leur LLM »)

Abstraire le fournisseur derrière une couche unique :

| Fournisseur | Type | Coût | Note |
|---|---|---|---|
| Ollama | local | gratuit | défaut, privacy max (gemma3, llama3.x, qwen2.5…) |
| LM Studio | local | gratuit | API compatible OpenAI |
| OpenAI / Anthropic / Mistral / Groq | cloud (clé user) | à leur charge | qualité supérieure, opt-in |

Le configurateur web détecte/propose, le package teste la connexion au 1er lancement (`jobhunt doctor`).

## 5. Verrous techniques à lever (recherche)

1. **Bundling Playwright** : Chromium ≈ 150 Mo. Pour l'app desktop, télécharger le navigateur au 1er lancement (post-install) plutôt que de l'embarquer → installeur léger. Alternative : `requests` + parseur HTML pour les plateformes statiques, Playwright seulement en repli.
2. **Robustesse scraping** : DuckDuckGo/`ddgs` rate-limite ; prévoir backoff + sources multiples + cache. Respect des ToS (cf. §7).
3. **Extraction d'un binaire Python** : `uv`/`pipx` pour A ; PyInstaller ou sidecar Python pour B (Tauri).
4. **Modèle de profil/CV** : parsing CV (PDF/DOCX) → structuré (compétences, séniorité, contraintes) qui enrichit le scoring Recruteur.
5. **Persistance locale évolutive** : passer de `memory.json` à SQLite (suivi de candidatures, historique, dédup).
6. **Portabilité config** : schéma versionné `jobhunt.config.json` (validation Pydantic/JSON-Schema).

## 6. Ce qui rend l'outil VRAIMENT utile (au-delà du « scoring »)

Le scoring brut ne suffit pas. Différenciateurs centrés chercheur d'emploi :

1. **Match CV ↔ offre explicable** — « Pourquoi ce 82/100 ? » avec le détail du rubric et les écarts (« il te manque : Kubernetes »).
2. **Suivi de candidatures (pipeline Kanban)** — Trouvé → Intéressé → Postulé → Entretien → Offre/Refus. C'est ça qui fait revenir l'utilisateur chaque jour.
3. ~~**Brouillon de candidature généré localement**~~ — **ÉCARTÉ (décision porteur, sess. 3)** : la génération de texte par IA est impersonnelle et reconnaissable, elle dessert le candidat. MyJobAgent aide à *trouver et décider*, pas à écrire. (Aide non-générative — points clés / gaps à adresser — éventuellement plus tard, sans rédaction auto.)
4. **Déduplication cross-plateformes** — la même offre sur 4 sites = 1 carte.
5. **Anti-ghosting / fraîcheur** — détecter les offres repostées/périmées.
6. **Digest quotidien** — « 6 nouvelles offres ≥ 70 ce matin », notification locale, zéro spam.
7. **Privacy comme argument** — « ton CV ne quitte jamais ta machine » : décisif pour des candidats en poste qui cherchent discrètement.

## 7. Risques & garde-fous

- **ToS des plateformes** : LinkedIn/Indeed interdisent le scraping. Garde-fou : privilégier flux/API publics, throttling, usage « personnel » documenté, opt-in explicite par source, désactivable. Position : outil personnel d'agrégation, pas de revente de données.
- **Qualité des petits LLM** : gemma3:e2b peut halluciner le JSON. Garde-fou : validation stricte + repli + permettre un modèle plus gros.
- **Open source & monétisation** : cœur OSS (moteur+CLI) ; le SaaS (configurateur, sync optionnelle, digests cloud premium) finance. Modèle « open-core ».
- **Légal RGPD** : local-first résout 90 % du sujet (pas de traitement côté serveur).

## 8. Décisions ouvertes (à trancher avec le porteur)

- Nom de produit (working name : **MyJobAgent** / **Hunt** — à valider).
- Langue du produit (FR d'abord, i18n EN ensuite ?).
- Engine : garder Python (recommandé) vs réécrire en TS pour une CLI `npx` unifiée.
- Niveau de sync cloud optionnelle (premium) vs 100 % local pur.
