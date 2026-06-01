# Dossier produit — MyJobAgent (working name)

Transformation des scripts `Agent-Jobs` en produit **open-source, local-first** : un configurateur web
définit profil + recherche et génère un package ; le moteur (agents LLM Scout/Trieur/Recruteur) tourne
**chez l'utilisateur avec son propre LLM**.

## Lire dans l'ordre
1. [`00_RESEARCH.md`](00_RESEARCH.md) — cadrage, vision local-first, distribution, verrous techniques.
2. [`01_PRODUCT_SCOPE.md`](01_PRODUCT_SCOPE.md) — value prop, personas, MoSCoW, métriques.
3. [`02_DESIGN.md`](02_DESIGN.md) — design system lumineux, composants, écrans, CLI, a11y, dark mode.
4. [`03_ROADMAP.md`](03_ROADMAP.md) — phases exécutables par un agent (Claude Code), avec critères d'acceptation.
5. [`04_REVIEWS_SYNTHESIS.md`](04_REVIEWS_SYNTHESIS.md) — revues croisées UX/UI + Product Owner et arbitrages.
6. [`05_DECISIONS.md`](05_DECISIONS.md) — décisions ouvertes + gates de validation.
7. [`design-tokens.css`](design-tokens.css) — tokens partagés (couleurs AA, dark mode) prêts à l'emploi.

## Contrainte d'architecture verrouillée
**Zéro backend.** Tout le calcul et les données chez l'utilisateur ; côté hébergeur, uniquement du **statique** (GitHub Pages ou Vercel, sans serverless functions). Le configurateur est une SPA client-side ; le transfert de config vers le moteur local se fait par **fichier téléchargé** ou **base64 inline** (jamais via un serveur). Détails : `00_RESEARCH.md §2bis & §3bis`.

## Les 3 idées-force
- **Local-first / privacy** : aucune donnée ne quitte la machine ; bring-your-own-LLM.
- **Matching explicable** contre TON profil (« 82/100, il te manque Kubernetes ») = le vrai wedge.
- **DX = UX** : CLI soignée + onboarding `web → uvx/pipx → 1ʳᵉ chasse` pensé comme un parcours.

## Prochaine action recommandée
Exécuter la **Phase −1** de la roadmap : prouver la qualité du matching (Go/No-Go) avant tout refactor.
