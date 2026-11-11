# Gestion de boutiques

Application web (PWA) de gestion complète d'une boutique : stock sur plusieurs lieux, achats,
ventes et reçus, crédits clients, dépenses, déplacements de stock, camions et chauffeurs,
tableau de bord du jour et journal de toutes les actions. Interface très simple, pensée pour un
téléphone Android : une vente simple se fait en 4 gestes.

Trois versions de boutique reposent sur le même socle et ne diffèrent que par leurs réglages :
**Motos et camions** (première livrée, Garoua), **Prêt-à-porter** et **Textile**.

> **État du projet : spécification.** Aucun code n'est encore écrit. Les commandes de
> démarrage seront ajoutées ici au Lot 1.

## Documents

| Document | Contenu |
| --- | --- |
| `Cahier des charges — Application de gestion de boutiques.md` | Besoin fonctionnel : rôles, cas d'utilisation, règles de gestion, entités — **document confidentiel, gardé en local, hors du dépôt** |
| [`specs.md`](specs.md) | Spécification technique : architecture, données, API, sécurité, tests, risques |
| [`design-system.md`](design-system.md) | Identité visuelle : couleurs, typographie, espacements, composants |
| [`CLAUDE.md`](CLAUDE.md) | Règles de travail du projet |

## Stack prévue

| Partie | Technologies |
| --- | --- |
| `backend/` | Python 3.12, FastAPI, Clean Architecture (domaine pur, cas d'utilisation, ports et adaptateurs), SQLAlchemy 2 + Alembic dans l'adaptateur PostgreSQL |
| `frontend/` | React 18, TypeScript strict, Vite, Tailwind, TanStack Query, PWA installable |
| `e2e/` | Playwright + axe-core |
| Infrastructure | VPS + Docker Compose (Caddy, API, worker, PostgreSQL, MinIO, sauvegardes) ; frontend servi aussi par Vercel |

## Principes d'architecture

- **Base de données interchangeable** : le domaine et les cas d'utilisation ne dépendent que de
  ports (interfaces). PostgreSQL est un adaptateur parmi d'autres ; une même suite de tests de
  contrat tourne sur l'adaptateur en mémoire et sur PostgreSQL.
- **Boutiques isolées** : chaque dépôt de données est construit pour une seule boutique.
- **Droits vérifiés par le serveur** : un vendeur ne reçoit jamais un coût ni une marge.
- **Rien n'est effacé** : annulation avec motif, journal en ajout seul.
- **Échec explicite** : aucune erreur silencieuse ; une configuration invalide arrête le démarrage.
- **Fichiers courts** : 200 lignes au plus par fichier.
- **Hors-ligne** : ossature prête mais désactivée en V1 (future fonction premium).

## Feuille de route

| Lot | Contenu |
| --- | --- |
| 1 | Socle, console plateforme, catalogue et stock, achats, ventes et reçus, créances, dépenses, tableau de bord, alertes, journal |
| 2 | Déplacements de stock, transport (camions, chauffeurs, voyages, paie) |
| 3 | Import Excel, versions Prêt-à-porter et Textile |
