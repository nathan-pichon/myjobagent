# MyJobAgent — Configurateur web statique

SPA statique (Astro + Tailwind) qui génère le fichier `jobhunt.config.json` pour l'agent de recherche d'emploi local. 100 % client-side, zéro backend, zéro analytics.

## Prérequis

- Node.js >= 22 (utilise `/opt/homebrew/bin/node` ou `nvm use 22`)
- npm >= 10

## Développement local

```bash
# Depuis le dossier web/
npm install
npm run dev
# Ouvre http://localhost:4321
```

## Build production

```bash
npm run build
# Sortie statique dans web/dist/
# Tous les fichiers sont 100 % statiques (HTML + CSS + JS)
```

Pour prévisualiser le build :

```bash
npm run preview
```

## Déploiement

### GitHub Pages

1. Crée un repo GitHub et push ce dossier `web/` (ou le repo entier).
2. Dans `astro.config.mjs`, ajoute `base` si c'est une **project page** (ex : `https://user.github.io/mon-repo/`) :

```js
export default defineConfig({
  output: 'static',
  base: '/mon-repo',   // <-- uniquement si project page, pas user/org page
  // ...
});
```

3. Active GitHub Pages dans Settings > Pages > Source : **GitHub Actions**.
4. Crée `.github/workflows/deploy.yml` :

```yaml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]
    paths: ['web/**']
jobs:
  build-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: cd web && npm ci && npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: web/dist
      - id: deployment
        uses: actions/deploy-pages@v4
```

### Vercel

Vercel détecte Astro automatiquement. Zéro config nécessaire.

1. Importe le repo dans [vercel.com](https://vercel.com).
2. Dans les paramètres du projet, règle le **Root Directory** sur `web/`.
3. Vercel utilise le preset Astro : `npm run build` + dossier `dist/` comme output.
4. Aucune serverless function n'est créée (output `static` dans `astro.config.mjs`).

Ou via CLI :

```bash
cd web
npx vercel --prod
```

## Architecture

- `src/pages/index.astro` — La SPA entière (landing + wizard multi-étapes)
- `src/styles/global.css` — Design tokens MyJobAgent + composants CSS
- `src/layouts/Layout.astro` — HTML shell avec fonts Google
- `public/` — Assets statiques (favicon)

## Contrainte absolue

Zéro backend. Zéro appel réseau sortant. Zéro analytics. Tout se passe dans le navigateur :
- Génération du JSON via `JSON.stringify` côté client
- Téléchargement via `Blob + URL.createObjectURL`
- Commande base64url inline via `btoa`
- Persistance de session via `localStorage` (draft auto-save)
