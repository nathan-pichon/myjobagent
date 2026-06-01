# Design — MyJobAgent

> Direction : **lumineux, clair, orienté produit, innovant**. Confiance + énergie + sérénité.
> Cible émotionnelle : « un copilote calme et pro qui bosse pour moi, pas un job board anxiogène ».

## 1. Principes de design

1. **Lumineux ≠ vide** — fonds clairs, beaucoup d'air, mais des accents vifs et un point focal par écran.
2. **Le produit explique** — jamais un score sans le « pourquoi ». La transparence est la fonctionnalité.
3. **Calme, pas gamifié à outrance** — la chasse d'emploi est stressante ; le ton rassure.
4. **Local-first visible** — un badge « 🔒 100 % sur ta machine » récurrent : c'est l'argument.
5. **DX = UX** — la CLI et les messages d'erreur sont designés autant que le web.

## 2. Identité visuelle

### Palette ⟳ corrigée pour l'accessibilité (mode clair par défaut)
```
Fond            #FBFCFE  (blanc bleuté, lumineux)
Surface         #FFFFFF
Surface alt     #F3F6FB
Texte primaire  #0E1A2B  (presque noir, jamais #000)
Texte secondaire#4A5A72  (⟳ assombri : #5B6B82 échouait AA à 14px)
Primaire        #2E6BFF  (bleu beacon — confiance, ACTION/CTA uniquement)
Primaire soft   #E8F0FF
Accent (déco)   #00C2A8  (teal — illustrations, logo, gradient SEULEMENT)
Accent texte    #007A6A  (⟳ teal accessible pour texte/badge — #00C2A8 = 2,8:1, échoue AA)
Signal (déco)   #FFC24B  (jaune phare — fonds/illustrations)
Signal texte    #B07000  (⟳ jaune accessible pour texte — #FFC24B = 1,5:1, inutilisable en texte)
Danger          #E5345B  (⟳ légèrement assombri pour AA)
Bordures        #E4EAF2
```
**Règle rampe de score** : ne PAS réutiliser le bleu primaire pour la plage 50–74 (confusion avec le CTA). Voir §ScoreBreakdown.

### Palette dark (⟳ ajoutée — était « prévu » sans tokens)
```
Fond            #0D1117   Surface #161B22   Surface alt #1C2333
Texte primaire  #E6EDF3   Texte secondaire #8B949E
Primaire        #4D8EFF   Accent #3DD6BF   Signal #FFD06B   Danger #FF6E85
Bordures        #30363D
```
Règles dark : **ombres colorées → bordures** `1px solid var(--border)` (les ombres disparaissent sur fond sombre) ; gradient faisceau atténué (`opacity .6–.7`, glow subtil, pas d'aplat) ; respecter `prefers-color-scheme` + toggle manuel persistant.

Gradient signature (héros, logo, loader) : `#2E6BFF → #00C2A8` (le « faisceau ») — **jamais sous du texte** (le côté teal échoue AA).

### Typographie
- Titres : **Inter** / **General Sans** (geometric sans, moderne).
- Corps : **Inter**.
- Mono (scores, CLI, code) : **JetBrains Mono**.
- Échelle : 12 / 14 / 16 / 20 / 24 / **32** / 40 / 56 (⟳ palier 32 ajouté pour les titres de section). Line-height généreux (1.5 corps).
- **Scores dans l'UI** : Inter avec `font-variant-numeric: tabular-nums` (⟳ pas JetBrains Mono — réservé à la CLI/blocs code, évite la rupture de texture dans les cartes).

### Formes & profondeur
- Rayons : 12px (cartes), 8px (inputs), 999px (pills/badges).
- Ombres douces et colorées : `0 8px 24px rgba(46,107,255,.10)`.
- Pas de bordures dures partout : ombre + fond alt pour séparer.

### Motif signature : le « faisceau » (beacon)
Un trait de lumière en dégradé qui « balaie » — utilisé dans le logo, le loader de chasse (radar/sonar pulsé), et les états de progression. C'est l'élément innovant qui incarne « l'agent qui scanne pour toi ».

### Iconographie
- **Lucide uniquement** (⟳ une seule lib pour éviter l'incohérence de stroke), line 1.5px.
- **Emoji** : réservé à la CLI/docs. En web, le cadenas du `PrivacyBadge` = icône Lucide `lock` (⟳ résout l'incohérence « 🔒 » vs règle no-emoji).

## 3. Composants clés

- **JobCard** — la carte d'offre. Titre, entreprise, lieu, type de contrat, **score en pastille colorée** (vert ≥75 / bleu 50-74 / gris <50), tags stack, source, fraîcheur. Au survol : aperçu du rubric.
- **ScoreBreakdown** — barre segmentée Stack/Rôle/Lieu/Contrat + texte explicatif et « ce qui manque ». **Composant signature**.
- **ConfigWizard** — formulaire multi-étapes (Profil → Critères → CV → LLM → Générer) avec aperçu live de la config à droite.
- **LLMPicker** — cartes radio (Ollama / LM Studio / OpenAI / Anthropic…) + champ clé, test « ✓ connexion OK ».
- **HuntProgress** — radar/sonar animé (faisceau) + compteur live (« 23 URLs analysées, 4 matches »).
- **PipelineBoard** — Kanban suivi candidatures.
- **CommandBlock** — bloc commande à copier (`jobhunt init <code>`) avec bouton copier, hyper soigné (c'est le pont web→local).
- **PrivacyBadge** — pill « 🔒 Local » récurrente.
- **EmptyStates** illustrés et encourageants (jamais culpabilisants).

## 4. Écrans

### Web (configurateur, public, statique)
1. **Landing** — héros gradient + faisceau, promesse, démo animée du radar, CTA « Créer mon agent », section privacy, « comment ça marche en 3 étapes », OSS/GitHub.
2. **Wizard de config** — 5 étapes, aperçu live, badge privacy.
3. **Écran de génération** — la commande à copier + bouton « Télécharger l'app » + lien doc.
4. **Docs** — quickstart, troubleshooting, choix du LLM.

### Local (le tableau de bord, dans le package — web local ou fenêtre Tauri)
5. **Dashboard / Matches** — grille de JobCards, filtres (score, source, fraîcheur, lieu), tri.
6. **Détail offre** — texte extrait + ScoreBreakdown complet + bouton « Voir l'offre ↗ » + feedback 👍/👎 + actions pipeline. *(Pas de génération de pitch IA — écarté, cf. scope Won't.)*
7. **Pipeline Kanban** — suivi des candidatures.
8. **Chasse en cours** — HuntProgress (radar), logs lisibles.
9. **Réglages** — éditer la config, changer de LLM, planifier (`watch`).

## 5. Design de la CLI/DX (à designer autant que le web)

```
$ jobhunt run

  ◐ MyJobAgent — chasse en cours          🔒 local · gemma3:e2b

  Scout    ▸ "site:welcometothejungle.com backend Node.js Nice"
  Trieur   ▸ 18 URLs → 5 offres retenues
  Recruteur▸ ████████░░  scoring 4/5

  ✦ Match  Senior Backend Engineer · Acme · Nice         82/100
           Stack ████████ Rôle ████░ Lieu █████ Contrat ███

  3 nouveaux matches ≥ 75 · tableau de bord → http://localhost:4321
```
- Couleur, alignement, hiérarchie. Messages d'erreur actionnables (« Ollama introuvable → lance `ollama serve` ou choisis une clé API »).
- `jobhunt doctor` : checklist verte/rouge.

## 6. Accessibilité

- Contraste AA min (le score n'est jamais signalé par la couleur seule → toujours chiffre + label).
- Navigation clavier complète, focus visibles, `prefers-reduced-motion` (désactive le sonar animé).
- Tailles de police respectant le zoom navigateur.

## 7. Stack front recommandée

- **Web configurateur** : Astro (statique, rapide, parfait pour un site OSS) ou Next.js si on veut du dynamique. Tailwind + composants maison.
- **Dashboard local** : même design system, servi en local par le moteur (Astro/SvelteKit léger) ou embarqué dans Tauri (webview).
- Design tokens partagés (un seul `tokens.css`/Tailwind preset) entre web et local pour la cohérence.

---

## 8. Spécifications critiques (⟳ ajoutées après revue)

### 8.1 Le pont web→local — écran adaptatif, 100 % sans serveur (le moment de vérité)

Contrainte : la SPA est statique (GitHub Pages/Vercel), **aucun backend**. Le `CommandBlock` « à copier » ne suffit pas : il suppose un terminal prêt. Redesign :

1. **Router d'abord** — question unique : « Tu es à l'aise avec un terminal ? » → 2 chemins distincts (Terminal / App), jamais les deux à plat.
2. **Voie Terminal — bloc OS-aware** (onglets macOS / Linux / Windows auto-détectés via `navigator.platform`), avec **téléchargement de la config** (défaut robuste) :
   ```
   1. Installer :  pipx install jobhunt                       [Copier]
   2. Config    :  ⬇ Télécharger jobhunt.config.json
   3. Importer  :  jobhunt init ~/Downloads/jobhunt.config.json  [Copier]
   4. Lancer    :  jobhunt run
   ```
   Variante « tout-en-un » pour config courte : `jobhunt init --b64 eyJ...` (copier-coller, sans fichier).
3. **Pas de code court / pas de token serveur** (⟳ retiré : exigeait un backend). La config est soit un **fichier téléchargé** (`Blob`), soit **inline base64url** ; jamais stockée ailleurs que chez l'user.
4. **Disclosure privacy** : « Cette config reste sur ta machine. Rien n'est envoyé — [voir ce qu'elle contient] » (montre le JSON en clair).
5. **Confirmation inversée** (⟳ pas de polling depuis la SPA — `https→http://localhost` est bloqué par les navigateurs) : c'est **`jobhunt init` qui ouvre le dashboard local** (`http://localhost:4321`) à la fin. La réussite se voit en local. La SPA affiche juste « Quand c'est bon, ton dashboard s'ouvrira tout seul ».
6. **Troubleshooter inline** (pas de Python, Ollama pas lancé, port occupé) + aperçu de la sortie CLI attendue (checks verts).
7. **Voie App desktop** : deep link `jobhunt://` si installée, sinon « Bientôt — liste d'attente » (pas de bouton mort).

### 8.2 Clés API — jamais sur le web 🔴
Le configurateur web encode seulement *type + modèle* de LLM. **La clé API est saisie en local** par `jobhunt init`/`doctor`, stockée dans le keychain OS. Micro-copy explicite : « Ta clé est stockée dans ton trousseau système — elle ne transite jamais par nos serveurs. »

### 8.3 ScoreBreakdown — verdict d'abord, chiffre ensuite
Un candidat stressé lit un **verbe**, pas un nombre. Trois niveaux :
- **Niveau 1 (pastille JobCard)** : label + icône + chiffre. 4 plages, 4 labels, 4 icônes distinctes (jamais la couleur seule) :
  `≥75 Fort match ★` (teal) · `60–74 Bon match ◑` (indigo, ≠ bleu CTA) · `50–59 Match partiel ◔` (ambre) · `<50` filtré par défaut.
- **Niveau 2 (expand)** : barre segmentée avec **maxima visibles** + ✓/~/✗ par item.
  ```
  Stack    ████████░░ 32/40  ✓ Node.js, TS  △ Kubernetes (bloquant)
  Rôle     █████████░ 17/20  ✓ Backend Senior
  Lieu     ████████░░ 21/25  ✓ Nice / Remote
  Contrat  █████████  15/15  ✓ CDI
  ```
- **Niveau 3 (détail)** : verdict-phrase en tête + gaps **bloquant (rouge) vs cosmétique (gris)**, **relatifs au profil de l'user**, contextualisation (« Top 22 % de tes 18 résultats »), et **une action** : `[Voir l'offre ↗]` (+ feedback 👍/👎). *(Pas de « Générer un pitch » — écarté.)*
- **Copy anti-anxiété** : « petit décalage », « presque », « pas pour cette fois » — jamais « insuffisant »/rouge punitif.

### 8.4 États obligatoires (premier usage = autant que le happy path)
Designer nommément, illustrés (SVG inline), titre calme + 1 phrase + action :
premier run (« Lance ta première chasse ») · chasse finie 0 match (« Élargis le lieu ou baisse le score min » → `[Modifier ma config]`) · Ollama injoignable (« Lance `ollama serve` ou utilise une clé API ») · code expiré · CV non parseable (→ édition manuelle).

### 8.5 HuntProgress longue durée
Une chasse dure 5–40 min. Le radar seul lit comme un blocage. Ajouter : **étape courante en clair**, **ETA** (basée sur steps passés), **log défilant** des 10 dernières actions, état « ça travaille » pendant les pauses (rate-limit), `aria-live` pour les lecteurs d'écran. Option **Scout live** : flux narrativisé des URLs évaluées (✓82 / ✗ blog / · en cours).

### 8.6 ConfigWizard
Sauvegarde auto (`localStorage`) + reprise (« Reprendre ta configuration ? ») · validation par champ · états d'erreur de l'étape LLM (Ollama non détecté / modèle absent / clé invalide / timeout / succès) · **responsive** : aperçu live → bottom sheet sous 768px · gestion du focus entre étapes (`aria-current`).

### 8.7 Accessibilité — compléments
- Focus ring composite (marche sur tous fonds, clair+dark) : `box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px var(--primary)`.
- `prefers-reduced-motion` : couvre **tout** le motif faisceau (logo animé, transitions, sonar) → fade simple + compteur statique.
- Kanban drag&drop → **alternative clavier** obligatoire (boutons « Déplacer vers → »).
- Daltonisme : la rampe de score est différenciée par **icône** (★/◑/◔), pas seulement la couleur.

### 8.8 PrivacyBadge — règle de placement
Header (1×) + étape LLM du wizard (contextuel) + au-dessus du `CommandBlock`. **Nulle part ailleurs** (ni sur les JobCards) — sa rareté fait son poids. Copy : « Ton CV, tes critères et tes résultats restent sur ta machine. »
