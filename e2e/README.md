# E2E — Gestion de boutique

Tests de bout en bout **Playwright** (Chromium seul) + **axe-core**, préparant la recette T24
(`../docs/recette-lot1.md` § 5, `../specs.md` § 12). Projet npm autonome, TypeScript strict.

## Prérequis

- Node ≥ 24 ; `uv` (Python 3.12 géré par uv) ;
- dépendances installées : `npm ci` ici, `npm ci` dans `../frontend`, `uv sync` dans `../backend` ;
- navigateur : `npm run install:browsers` (CI : `npx playwright install --with-deps chromium`).

## Commandes

| Commande | Rôle |
| --- | --- |
| `npm test` | toute la suite (démarre et arrête les serveurs) |
| `npm run test:ui` | mode interactif de Playwright |
| `npm run install:browsers` | télécharge Chromium |
| `npm run typecheck` | `tsc --noEmit` |
| `npx playwright show-report` | rapport HTML du dernier lancement (`playwright-report/`) |

Sous Windows, si `uv` n'est pas dans le PATH :
`UV_BIN=/c/Users/<vous>/AppData/Roaming/Python/Python310/Scripts/uv.exe npm test`.

## Serveurs démarrés (`playwright.config.ts`, `webServer`)

| Serveur | Adresse | Détail |
| --- | --- | --- |
| backend jetable | `127.0.0.1:8100` | `uv run --frozen uvicorn app.bootstrap.container:build_app --factory`, `ENVIRONMENT=test`, `PERSISTENCE_BACKEND=memory`, `JWT_SECRET` aléatoire tiré à chaque lancement (jamais écrit), limitation de débit coupée |
| frontend | `127.0.0.1:5273` | Vite de `../frontend` avec `servers/vite.e2e.config.mjs` : même configuration, seul `server` change (port, proxy `/api` → 8100) |

Les serveurs de développement (8000, 5173) ne sont jamais utilisés : ces ports sont refusés, et
un serveur déjà présent sur 8100 / 5273 fait échouer le lancement (aucune réutilisation).
Pourquoi une configuration Vite à part : `frontend/vite.config.ts` fixe le proxy sur
`127.0.0.1:8000` sans variable d'environnement ; on ne modifie pas `frontend/`.

## Variables

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `UV_BIN` | `uv` | exécutable uv |
| `E2E_BACKEND_PORT` | `8100` | port du backend jetable (8000 interdit) |
| `E2E_FRONTEND_PORT` | `5273` | port du frontend (5173 interdit) |
| `CI` | — | `forbidOnly`, 1 nouvel essai, 2 workers |

## Projets

- `mobile-360` : 360 × 800, `isMobile`, `hasTouch`, `fr-FR`, `Africa/Douala` (CDC § 21) ;
- `desktop-1280` : 1280 × 800 ; exclut les tests marqués `@mobile-only` (toucher, largeur 360).

Traces conservées en cas d'échec (`trace: retain-on-failure`) ; `test-results/` et
`playwright-report/` sont ignorés par git.

## Arborescence

- `support/` : réglages (`env.ts`), axe (`axe.ts`, `color-contrast` active), mesures
  (`layout.ts` : défilement horizontal, cibles ≥ 48 px, écart ≥ 8 px), écran de connexion ;
- `fixtures/seed.ts` : amorçage des données de recette — **bloqué (T10)**, voir ci-dessous ;
- `tests/smoke/` : tests exécutables aujourd'hui (chargement 360 px, axe, toucher, erreur de
  connexion générique, coupure réseau, `/api/v1/health` via le proxy) ;
- `tests/journeys/` : squelettes des parcours E2E-01 à E2E-04, non-fuite des coûts, isolation,
  en `test.fixme` avec la tâche qui les débloque.

## Amorçage des données

Persistance mémoire : les données vivent dans le processus uvicorn ; seule l'API (ou une
commande du backend) peut les créer. Mécanisme prévu : un script hors dépôt de production
(`seed/seed.py`, lancé par `uv run --project ../backend`) crée l'administrateur plateforme,
puis la fixture crée JDD-0 par l'API publique (`POST /platform/shops`, membres, catalogue…).
**Bloqué par T10** : aucune commande ni route ne crée encore l'administrateur plateforme. Les
fixtures `shopA` / `shopB` échouent explicitement si on les utilise.

## Défauts connus (`test.fail`)

- **A11Y-02** : liens « Connexion administrateur plateforme » et « Retour à la connexion des
  boutiques » (`frontend/src/features/auth/LoginPage.tsx`) : 328 × 24 px, attendu ≥ 48 px de
  haut. Quand le défaut sera corrigé, ces tests échoueront (« passés de façon inattendue ») :
  retirer `test.fail`.
