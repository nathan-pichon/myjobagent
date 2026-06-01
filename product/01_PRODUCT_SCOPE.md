# Scope produit — MyJobAgent (working name)

> Open source, local-first. Le web configure et génère ; le moteur chasse chez l'utilisateur avec son LLM.

## 1. Énoncé de valeur

**Pour** les chercheurs d'emploi (tech d'abord) **qui** veulent une veille ciblée sans y passer leurs soirées et sans confier leurs données, **MyJobAgent est** un agent de recherche d'emploi autonome qui tourne sur leur machine avec leur propre LLM. **Contrairement à** LinkedIn/Indeed/alertes mail, il score chaque offre contre *leur* profil, explique pourquoi, et ne fait fuiter aucune donnée.

**Promesse en une phrase** : « Décris ton job idéal une fois. Ton agent le cherche tous les jours, en local, et te dit lesquels valent ta candidature — et pourquoi. »

> **⟳ Révisé après revue — positionnement.** Le héros du pitch est le **matching explicable contre ton profil/CV** (« 82/100, il te manque juste Kubernetes ») — c'est ce qu'aucun job board ne fait. Le **local-first/privacy** est la *preuve de confiance*, pas l'argument n°1 (il mord surtout sur le persona « dev en poste discret »). On se différencie des agents IA emploi récents (Sonara, Jobright, Simplify, AIHawk) en **refusant l'auto-apply** et en restant local.

## 2. Personas

| Persona | Besoin clé | Contrainte |
|---|---|---|
| **Dev en poste, recherche discrète** | veille passive, confidentialité absolue | pas de temps, en poste |
| **Freelance / fractional** | flux constant de missions ciblées | multi-plateformes, multi-critères |
| **Chercheur d'emploi actif** | maximiser candidatures pertinentes, suivre le pipeline | besoin d'organisation, motivation |
| **Non-tech curieux** (extension future) | « ça marche en double-clic » | zéro terminal |

Persona prioritaire MVP : **dev/freelance à l'aise avec un terminal**.

## 3. Périmètre — MoSCoW

> **⟳ Révisé après revue — MVP dégraissé.** Le configurateur web, l'import CV et le multi-LLM cloud
> sortent du MVP (le « Must » initial était un v0.3 déguisé). On prouve d'abord le moteur, en local, avec Ollama.

### Phase −1 (préalable bloquant, GATE produit)
- Jeu d'éval de 30–50 offres annotées → mesurer précision/rappel du matching sur ≥ 3 modèles. **Go/No-Go.** (cf. roadmap P−1)

### Must (MVP, v0.1)
- CLI `jobhunt` : `run`, `validate`, `doctor`, `dashboard`.
- Config via `jobhunt.config.json` **éditée à la main** (template commenté) — pas de web.
- Profil **saisi à la main** (rôles, stack, lieux, contrats, must/nice-to-have, exclusions).
- Moteur réutilisant l'existant (Scout/Trieur/Recruteur) piloté par la config, **Ollama seul**.
- Tableau de bord local lisible : matches, score, **détail explicable du rubric (verdict-first)**.
- **Déduplication** cross-plateformes (sans elle, le dashboard est cassé par les doublons).
- **Feedback 👍/👎 par match** (mesure de qualité locale).
- Source robuste par défaut (**France Travail API** + WTTJ) ; **LinkedIn OFF par défaut**.
- Persistance SQLite locale.
- Repo GitHub OSS : README, licence, quickstart < 10 min (sur machine avec Ollama déjà là).

### Should (v0.2)
- `jobhunt watch` : **digest quotidien + notification** (← feature de rétention n°1, livrer tôt).
- Import CV (PDF/DOCX) → extraction compétences/séniorité.
- Suivi de candidatures (Kanban Trouvé→…→Offre).
- Configurateur web + génération de config (après preuve de rétention).
- Multi-LLM (LM Studio, OpenAI, Anthropic, Mistral, Groq) — clé saisie **en local uniquement**.

### Could (v0.4+)
- App desktop Tauri (« package all-in-one » double-clic).
- Vue **« Why-not »** (offres écartées + motifs), **calibration** par feedback, **diff profil↔offre**, **comparateur d'offres**, **insights marché locaux**, **mode veille discrète**, **import profil GitHub** (cf. `04_REVIEWS_SYNTHESIS.md §4`).
- Galerie de templates partageables, multi-profils, sync chiffrée (premium), i18n EN.

### Won't (hors scope, assumé)
- **Génération de pitch / lettre de motivation par IA** (décision porteur). Le texte généré est impersonnel, reconnaissable, et dessert le candidat. MyJobAgent aide à *trouver et décider*, pas à *écrire à la place de*. (Une aide non-générative — checklist des points à mentionner, gaps à adresser — reste envisageable, mais aucune rédaction automatique.)
- Candidature automatique / envoi de mails à la place de l'utilisateur (risque + éthique).
- Hébergement du scraping sur un serveur **externe en ligne** (casse le local-first ; un serveur 127.0.0.1 local est OK).
- Revente / agrégation de données candidats.
- ATS / produit côté recruteur.

## 4. Parcours utilisateur cible (happy path)

1. Arrive sur le site → comprend la promesse en 10 s → « Créer mon agent ».
2. Décrit son profil + colle/upload son CV + ses critères (formulaire guidé, aperçu live).
3. Choisit son LLM (Ollama détecté ? clé API ?).
4. Obtient une **commande à copier** (`jobhunt init <code>`) ou télécharge l'app desktop.
5. Lance → `doctor` valide tout → première chasse → tableau de bord se remplit.
6. Chaque matin : digest « 5 offres ≥ 75 », il trie dans son Kanban, ouvre les offres qui valent le coup, postule (avec ses propres mots).

## 5. Métriques de succès (North Star) ⟳ révisé

> L'ancienne North Star (« candidatures envoyées ») est **non mesurable** en local-first (pas de télémétrie sortante) et **hors scope** (pas d'auto-apply). Remplacée.

- **North Star** : nb d'utilisateurs qui lancent **≥ 2 chasses sur 2 jours distincts** (proxy observable de « l'agent me rend vraiment service »).
- **Qualité (la métrique critique)** : ratio de matches notés 👍 / total notés — via le feedback local. Cible : ≥ 70 % de pertinence perçue. Suivre aussi le **taux de faux positifs** (matches ≥ seuil notés 👎).
- **Activation** : % d'utilisateurs atteignant un **1er match jugé pertinent** (pas seulement « config complétée »). Mesurer le time-to-first-match réel.
- **Rétention** : J+7 / J+14 — événement = relancer une chasse OU bouger une carte du pipeline.
- **Friction** : taux de complétion de `jobhunt doctor` (proxy de la friction d'install).
- **OSS** : ⭐ GitHub, contributeurs, **sources de scraping ajoutées par la communauté** (la vraie moat).

*Toute collecte est opt-in ; par défaut ces métriques restent locales (l'user peut les voir, rien ne sort).*

## 6. Non-négociables

1. **Privacy par défaut** — données locales, opt-in explicite pour tout ce qui sort.
2. **Bring-your-own-LLM** — jamais verrouillé sur un fournisseur.
3. **Open source** sur le cœur — confiance + contributions de sources.
4. **Time-to-first-match < 15 min** — sinon l'utilisateur abandonne.
