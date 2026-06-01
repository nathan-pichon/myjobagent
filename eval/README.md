# Phase −1 — Harnais d'éval du matching (GATE qualité)

> **La chose la plus importante de la roadmap.** Prouver que le moteur score correctement
> AVANT de construire le web / le desktop. Voir `product/03_ROADMAP.md` Phase −1.

## Idée
On constitue un petit jeu d'offres annotées à la main (`dataset.jsonl`), on fait scorer
chaque offre par le **Recruteur** avec différents modèles LLM, et on mesure :
- **précision / rappel** sur la décision « match » (score ≥ seuil) vs le label humain,
- la **stabilité** (variance du score sur N re-runs identiques),
- le **MAE** entre le score du modèle et le score humain (si fourni).

## Format du dataset (`eval/dataset.jsonl`)
Une ligne JSON par offre :
```json
{"id":"wttj-001","text":"<texte de l'offre>","label":"match","human_score":82,"note":"backend node remote"}
```
- `label` : `"match"` ou `"no_match"` (vérité terrain humaine).
- `human_score` : optionnel (0–100) pour le MAE.
- `text` : le texte extrait de l'offre (5000 chars max, comme en prod).

Un dataset de démarrage est généré depuis `memory.json` (offres déjà trouvées) via
`python -m eval.seed_from_memory` — **à relabelliser à la main** (les scores de
l'ancien run ne sont PAS une vérité terrain fiable, ce sont des prédictions).

## Lancer
```bash
python -m eval.run --models qwen2.5:7b,gemma4:e2b --threshold 50 --repeats 2
```
Sort un tableau comparatif + écrit `eval/report.json`.

## GATE
Si la **précision perçue < 70 %** sur le meilleur modèle local raisonnable →
corriger le rubric / prompt / modèle minimum avant de coder le reste (décision D1).
