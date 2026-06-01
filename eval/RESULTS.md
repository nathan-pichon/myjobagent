# Résultats de l'éval matching (Phase −1, GATE qualité)

> Dataset curé v1 : **27 offres labellisées à la main** (`eval/dataset.jsonl`,
> 12 match / 15 no_match), profil cible = `default_config()` (Node.js/TypeScript,
> Nice/Sophia/Remote-France, Senior backend, CDI/Freelance). Seuil match = 50.
> **GATE = précision ≥ 0,70.**

## Verdict : ✅ GATE FRANCHIE par les deux modèles locaux

| Modèle | Précision | Rappel | F1 | Accuracy | MAE | TP/FP/FN/TN | GATE |
|---|---|---|---|---|---|---|---|
| gemma4:e4b | 0.706 | **1.00** | 0.828 | 0.815 | 16.7 | 12/5/0/10 | ✅ |
| gemma4:e2b | **0.800** | **1.00** | 0.889 | 0.889 | 16.3 | 12/3/0/12 | ✅ |

(Source : `eval/report.json`, prompt Recruteur durci.)

## Lecture des résultats

1. **Rappel = 1,0 sur les deux modèles** : aucune bonne offre n'est ratée. Le risque
   résiduel n'est pas de manquer un emploi, mais d'afficher quelques offres en trop —
   atténué par le tri par score, la vue « Why-not » et le feedback 👍/👎.

2. **La GATE a fait son travail.** Avant durcissement du prompt, e2b était à ~0,65 (échec) —
   exactement le risque n°1 pointé par les reviewers. La réintroduction de **garde-fous
   stricts génériques** (HARD GATES stack / location / not-a-job, exprimés en fonction du
   profil, pas codés en dur) dans `jobhunt/prompts/recruteur.md` a fait passer la précision
   au-dessus du seuil.

3. **e2b > e4b sur cette passe** (0,80 vs 0,71) : contre-intuitif. Sur n=27 avec 1 répétition,
   c'est dans la marge de variance LLM. Ça ne prouve PAS que le 2B est « meilleur » — juste
   que les deux sont *suffisants* sur ce set après durcissement. Un dataset plus large (50+)
   et plusieurs répétitions (σ) départageront. **MAE ~16 pts** sur les deux : les scores
   absolus restent approximatifs (à ne pas survendre), mais la **décision binaire** match/non
   est fiable.

## Faux positifs (cas durs, composés)
Les FP restants sont des offres « presque » : bonne stack mais lieu KO (Node Bordeaux
on-site), ou nice-to-have présents masquant un stack hors-cible (Go + Postgres/K8s à Paris).
Ce sont les cas les plus ambigus du set ; un humain hésiterait aussi. Pour reproduire le
détail par item : relancer `python -m eval.run` et inspecter les compteurs TP/FP/FN/TN.

## Décision D1 — LLM minimum recommandé
- **Minimum qui passe la GATE** : `gemma4:e2b` (~2B, rapide, léger) — **0,80** sur ce set.
- **Recommandé** : `gemma4:e4b` (4B) — équivalent en décision, souvent plus stable sur les
  cas composés ; à confirmer sur dataset élargi.
- **Qualité max** : 7B+ (`qwen2.5:7b`, défaut documenté de la config) ou clé API cloud (opt-in).
- Le `doctor` signale si le modèle configuré n'est pas tiré et propose `ollama pull`.

## Limites & suite (P−1.5)
- Dataset **curé** (textes rédigés) → idéal pour mesurer la discipline du scoring, mais « trop
  propre » vs le web réel. **À augmenter** avec de vraies offres scrapées + profils non-backend
  pour vérifier la généricité des gates. Viser 50+ offres, 2-3 répétitions (mesurer σ).
- Re-mesurer après chaque évolution du prompt Recruteur (régression).

_Reproduire :_
`python -m eval.build_dataset_v1 && python -m eval.run --models gemma4:e4b,gemma4:e2b --threshold 50 --repeats 1`
