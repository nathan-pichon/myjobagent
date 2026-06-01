# Revues croisées — Synthèse (Designer UX/UI + Product Owner)

> Plusieurs passes de revue par des agents jouant le **Lead Designer UX/UI** et le **Product Owner senior**.
> Note moyenne : **Design 6,5/10**, **Produit 6/10**. Verdict commun : *bonne vision, bien écrite, mais
> on a designé et planifié l'enveloppe avant de prouver la seule chose qui tue le produit — la qualité du matching.*

## 1. Les 6 consensus forts (tous les reviewers, à appliquer)

### C1 — Prouver le matching AVANT de construire quoi que ce soit d'autre 🔴
Le risque existentiel n°1 est que `gemma3:e2b` (~2 B params) score mal (faux positifs, JSON halluciné). **Aucune feature ne sauve un moteur médiocre.** → Ajouter une **Phase −1 « éval matching »** : 30–50 offres réelles annotées à la main, mesurer précision/rappel sur 2–3 modèles (gemma3, qwen2.5:7b, + baseline cloud). **Go/No-Go produit.** (cf. roadmap mise à jour.)

### C2 — Dégraisser le MVP 🔴
Le « Must » actuel est un v0.3 déguisé. Sortir du MVP : **configurateur web, import CV, multi-LLM**. MVP réel = `jobhunt` (CLI) + `jobhunt.config.json` édité à la main + **scoring explicable** + SQLite + dashboard local lisible + Ollama seul. Livrable en 4–6 semaines vs 12+.

### C3 — Re-séquencer : dashboard AVANT web 🔴
Le web est de l'**acquisition**, pas de la preuve de valeur. Construire le wizard avant de savoir si le matching est bon = funnel vers une déception. Nouvel ordre : **Éval → P0 → P1(cœur) → P3(dashboard) → P2(web) → P4 → P5.**

### C4 — Re-designer le pont web→local (le maillon le plus faible) 🔴
C'est l'écran que 100 % des utilisateurs voient et où le funnel chute. Le `CommandBlock` « à copier » suppose un terminal prêt — vrai pour personne au premier contact. Redesign en **écran adaptatif** (cf. `02_DESIGN.md §4bis`).

### C5 — Corriger l'accessibilité et définir le dark mode maintenant 🔴
Plusieurs couleurs **échouent WCAG AA** en texte : teal `#00C2A8` (~2,8:1), jaune `#FFC24B` (~1,5:1), texte secondaire `#5B6B82` à 14px. Le score ne doit JAMAIS dépendre de la couleur seule (vert/bleu/gris = mauvais trio daltonien). Dark mode « prévu » sans tokens = dark mode jamais fait. → tokens sémantiques + palette dark dès le `tokens.css`, avant tout code.

### C6 — La clé API n'est JAMAIS saisie sur le web 🔴
Pour un produit dont l'argument est la privacy, un champ « clé OpenAI » sur le configurateur web public serait un contresens fatal. Le web encode seulement *type+modèle* ; la clé est saisie **en local** par `jobhunt init`/`doctor`, stockée dans le keychain OS.

## 2. Points produit majeurs

- **Repositionner le pitch** : le héros doit être **« matching explicable contre TON CV »**, le local-first devient la *preuve de confiance*, pas l'argument n°1. (Le privacy mord surtout sur le persona « dev en poste discret » — segment réel mais étroit.)
- **North Star non mesurable** : « candidatures envoyées » est invisible en local-first et hors scope (pas d'auto-apply). → Remplacer par **« utilisateurs qui lancent ≥ 2 chasses sur 2 jours distincts »** (proxy de service rendu) + **pouce 👍/👎 par match** (seule source de vérité locale sur la qualité, et carburant du Supervisor).
- **Rétention — débat tranché** : le **digest quotidien** (« l'agent a bossé cette nuit, voici 3 offres ≥ 80 ») est le vrai moteur d'habitude, pas le Kanban (organisateur passif, en doublon de Notion/Trello). → Avancer `jobhunt watch` + notif tôt (mode CLI), garder le Kanban mais le dé-prioriser.
- **Sources** : ne pas tout miser sur `ddgs` (fragile, rate-limit). Ajouter une source structurée robuste dès le MVP (**API France Travail officielle**, flux RSS WTTJ). **LinkedIn OFF par défaut**, opt-in avec disclaimer (ToS anti-scraping, hiQ a évolué en défaveur des scrapers).
- **Monétisation open-core à trancher tôt** : sinon side-project OSS sans revenu. Frontière proposée : *OSS = moteur + CLI + dashboard local* ; *premium = sync chiffrée multi-machines + templates hébergés + (option) LLM cloud plug-&-play*.

## 3. Points design majeurs

- **ScoreBreakdown — verdict d'abord, chiffre ensuite.** Un candidat stressé lit un verbe, pas un score. 3 niveaux : pastille (label+icône+chiffre) → barre segmentée annotée (maxima visibles, ✓/~/✗) → détail (gaps **bloquant vs cosmétique**, relatifs à SON profil, + action « Voir l'offre »). Copy anti-anxiété (« petit décalage », jamais « insuffisant »). Contextualiser (« Top 22 % de tes 18 résultats »). *(NB sess. 3 : l'action « Générer un pitch » initialement suggérée par les revues a été écartée par le porteur — voir scope Won't.)*
- **États manquants** : premier run, chasse finie 0 match (CTA « élargis tes critères », jamais culpabilisant), Ollama crash, code expiré. À designer nommément.
- **HuntProgress longue durée** : une chasse dure 5–40 min. Ajouter étape courante, ETA, log défilant, état « ça travaille » pendant les pauses (sinon le radar lit comme un blocage). `aria-live` pour les lecteurs d'écran.
- **ConfigWizard** : sauvegarde auto (localStorage), validation par champ, états d'erreur (surtout étape LLM : Ollama non détecté / modèle absent / clé invalide), responsive mobile (aperçu live → bottom sheet < 768px).
- **Détails à trancher** : une seule lib d'icônes (**Lucide**) ; **Inter `tabular-nums`** pour les scores en cartes (réserver JetBrains Mono à la CLI) ; emoji réservé CLI / icône `lock` en web ; palier typo **32px** ; règle de placement du `PrivacyBadge` (header + étape LLM + écran génération, nulle part ailleurs) ; sortir le bleu de la rampe de score (réserver le bleu beacon au CTA).

## 4. Idées innovantes retenues (ajoutées au scope « Could/Should »)

| Idée | Valeur | Source |
|---|---|---|
| **Calibration / pouce 👍👎 → ajuste le profil** | scoring qui apprend le goût de l'user, 100 % local, incopiable par LinkedIn | les deux panels |
| **Vue « Why-not » des offres écartées** | rassure (« rien raté ») + calibre les critères par feedback | PO + UX |
| **Hunt Replay / Scout live** | activité narrativisée en temps réel → confiance + engagement pendant l'attente | UX |
| **Diff profil ↔ offre (style git)** | carte de navigation pour la candidature, exclusif au matching profilé | UX |
| **Comparateur 2 offres côte-à-côte** | la décision est une priorisation entre offres comparables | UX |
| **Insights marché locaux (heatmap SQLite)** | l'agent devient une fenêtre sur le marché, 100 % privé | UX |
| **Mode veille discrète (menubar, blur screenshot-safe)** | répond au persona n°1 (recherche en poste) | UX |
| **Import profil GitHub (client-side)** | wizard de 10 → 2 min, « le produit me comprend » | UX |
| **Beacon digest comme rituel du matin** | incarne le motif faisceau au moment le plus émotionnel = rétention | UX + PO |

## 5. Décisions ouvertes à trancher (cf. `05_DECISIONS.md`)
1. **LLM minimum viable** (gemma3:e2b suffit ? ou qwen2.5:7b ? ou cloud par défaut ?) — dépend de l'éval C1.
2. **Modèle économique** open-core précis + timeline.
3. **Mécanisme d'import config** web→local (token inline base64 vs fichier `.json` vs stockage éphémère).
4. **Engine** : garder Python (reco) vs réécrire TS (impacte P4 Tauri).
5. **Marché** : France d'abord vs international au lancement (impacte i18n, docs).
6. **Nom & licence** : « MyJobAgent » dispo ? Licence (AGPL protège contre forks SaaS).

---
*Les changements C1–C6 et la section 2–4 ont été intégrés dans `01_PRODUCT_SCOPE.md`, `02_DESIGN.md` et `03_ROADMAP.md` (voir leurs sections « ⟳ Révisé après revue »).*
