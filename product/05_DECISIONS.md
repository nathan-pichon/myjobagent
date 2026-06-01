# Décisions ouvertes à trancher

> Issues des revues. Chaque décision a une **reco** par défaut pour ne pas bloquer l'agent ; à confirmer par le porteur.

> **🔒 Contrainte verrouillée (porteur)** : tout chez l'utilisateur ; hébergement **100 % statique** (GitHub Pages ou Vercel sans serverless functions). Aucun backend, aucune base, aucune donnée reçue côté hébergeur. Voir `00_RESEARCH.md §2bis & §3bis`.

| # | Décision | Options | Reco | À trancher avant |
|---|---|---|---|---|
| **D1** | LLM minimum viable | gemma3:e2b (2B) / qwen2.5:7b / cloud par défaut | **Dépend de l'éval P−1.** Reco a priori : recommander **qwen2.5:7b** comme minimum « bon », gemma3 comme « rapide/léger », cloud opt-in pour qualité max | P0 |
| **D2** | Modèle économique (sous contrainte zéro-backend) | GitHub Sponsors / app desktop payante / support / SaaS opt-in séparé plus tard | Tant qu'on reste statique : **Sponsors + app desktop payante (one-shot/don) + support**. Une sync premium nécessiterait un backend → à isoler dans un service opt-in distinct si jamais (ne pas casser le local-first par défaut) | P2 |
| **D3** | Import config web→local | ~~stockage éphémère serveur~~ exclu / fichier `.json` / base64 inline / deep link | **TRANCHÉ** : zéro serveur → **fichier `.json` téléchargé** (défaut) + **base64url inline** (configs courtes) + `jobhunt://` (app desktop). Confirmation = le CLI ouvre le dashboard local | ✓ |
| **D4** | Engine | garder Python / réécrire TS | **Garder Python** (moteur prouvé) ; Tauri via sidecar Python en P4 | P4 (idéal. P2) |
| **D5** | Marché | France d'abord / international | **France d'abord** (moteur déjà FR-centré), i18n EN en P5 | P2 |
| **D6** | Nom & licence | **TRANCHÉ** : marque **MyJobAgent**, commande CLI **`mja`** (package interne `jobhunt` conservé). Repo cible `github.com/nathan-pichon/myjobagent` (pas encore créé). Licence **AGPL-3.0**. *Reste à vérifier : dispo PyPI du nom `myjobagent`, et la marque.* | ✓ (vérifs PyPI/marque à faire) |

## Gates de validation (rappel)
- **GATE 1 (après P−1)** : précision perçue du matching ≥ 70 % → sinon corriger rubric/modèle.
- **GATE 2 (après P3)** : rétention J+7 ≥ 40 % sur 10–20 beta-users → sinon ne pas investir le web (P2).
