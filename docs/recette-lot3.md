# Plan de recette — Lot 3 (Prêt-à-porter, Textile, Import Excel)

> Auteur : @architect pour @qa · Statut : **à valider par l'orchestrateur** · Porté par la tâche **T47** du `docs/plan-lot3.md`.
> Sources : CDC § 15, § 18, § 19, § 20.9 ; `specs.md` (§ 4.5, § 6, § 8, § 12, § 15.1) ; décisions QC-1 à QC-6 du client (2026-11-13).
> **Niveaux autorisés : unitaires et intégration seulement** (décision client : pas d'E2E). Les vérifications
> d'écran se font en **UI** (vitest + Testing Library), jamais dans un navigateur piloté.
> Hors Lot 3 : transferts, transport, modèles d'import Camions et Chauffeurs (Lot 2), **remise** (QC-2 : il n'y en a pas),
> stock au centimètre (QC-3 : le dixième est gardé). Les cas marqués **[QC-n]** suivent la décision du client du 2026-11-13.

## 0. Conventions

| Élément | Convention |
| --- | --- |
| Niveaux | **DOM** domaine (pytest pur) · **APP** cas d'utilisation + adaptateurs mémoire · **CTR** contrat de port (mémoire **et** PostgreSQL) · **HTTP** pytest + httpx sur `create_app()` · **UI** vitest + Testing Library |
| Horloge | port `Clock` figé, Douala UTC+1. `10/11 10:00 D` = heure de Douala |
| Boutique **P** | « Mode Garoua », profil Prêt-à-porter, ouverte par `OpenShop`. Lieu : Boutique. **O** propriétaire, **E** employé, **E2** second employé, **C** comptable. Articles : **CH** « Chemise lin » (base 15 000, minimum 12 000, CMP 9 000), **RB** « Robe pagne » (base 20 000, minimum 17 000, CMP 12 000) |
| Boutique **X** | « Tissus Ngaoundéré », profil Textile. Article **WX** « Wax Fleur de mariage », unité Mètre, vente à la pièce, pièce 5,49 m, base 2 500 /m et 13 000 /pièce |
| Boutique **M** | boutique Motos du Lot 1 (JDD-0 de `recette-lot1.md`), non-régression |
| Boutique **B** | autre compte commerçant, profil Prêt-à-porter, propriétaire **OB** (isolation) |
| Erreurs | format `{"error": {code, message, details}}` ; « 403 » = `403 FORBIDDEN` + « Accès refusé » au journal |

## 1. Matrice de traçabilité

### 1.1 Cas d'utilisation et règles

| Réf. CDC | Cas de test (ID — vérification) | Niveau | Tâche |
| --- | --- | --- | --- |
| UC-SOC-01 (profils) | PRF-01 — ouverture Prêt-à-porter : 1 lieu « Boutique » point de vente et lieu de réception des achats (QC-5), reçu `thermal-58`, `employee_exchange_allowed` faux, `exchange_days` 7, rôles Propriétaire/Employé/Comptable (pas de Chauffeur), modules disponibles sans `transport` | APP | T27 |
| | PRF-02 — idem Textile ; `stock_units` = METER, PIECE | APP | T27 |
| | PRF-03 — `GET /profile` de P : menus exactement § 18.5 (O : Accueil · Ventes · Stock · Créances · Plus[Achats, Dépenses, Clients, Journal, Réglages] ; E : Accueil · Nouvelle vente · Mes ventes · Créances · Stock ; C : Accueil · Achats · Stock · Dépenses · Inventaire), libellé de rôle « Employé » | HTTP | T27 |
| | PRF-04 — ajouter un membre Chauffeur dans P → `422` (rôle absent du profil) | APP | T27 |
| | PRF-05 — console : les 3 types sont proposés ; ouverture Textile envoie `profile_code = textile` | UI | T38 |
| Changement de type [QC-1] | PRF-06 — boutique Motos vide → `POST /platform/shops/{id}/profile` `apparel` : 200 ; lieux Garoua-Boulaï, Ngaoundéré, Garoua désactivés, « Boutique » créée, reçu 58 mm ; journal sensible | APP, HTTP | T27 |
| | PRF-07 — boutique avec 1 article → `422 PROFILE_CHANGE_BLOCKED`, `details.blocking` contient `articles: 1` ; avec un membre Chauffeur → `blocking.members` | APP | T27 |
| | PRF-08 — O (non admin) → 403 ; profil inconnu → `400` | HTTP | T27 |
| Vocabulaire | VOC-01 — rendu des écrans Accueil, Nouvelle vente, Mes ventes, Stock, fiche article, Achats, Membres, Reçu avec le profil P puis X : aucun des mots « modèle », « châssis », « Garoua », « Vendeur », « Camion » dans le DOM | UI | T37, T39 |
| | VOC-02 — profil M : menus et libellés Motos inchangés (non-régression du profil servi) | UI | T37 |
| | VOC-03 — code de menu inconnu renvoyé par le serveur → erreur explicite (pas d'entrée muette) | UI | T37 |
| | VOC-04 — création de « Robe Bleu Marine Robe » : avertissement « mot répété » avant l'envoi (garde-fou du nom) | UI | T39 |
| Réserve [QC-5] | LOC-01 — P : Réglages → Lieux, création d'un entrepôt → avertissement « déplacement disponible plus tard » avant l'envoi ; aucun écran de transfert | UI | T39 |
| § 18.2 | ART-01 — article P sans référence → `REF-000001` ; nom en double (« chemise LIN ») → `409 DUPLICATE` | APP | T27 |
| § 18.3 Panier, sans remise [QC-2] | SCN-L3-01 ; PAN-01 — `POST /sales` multi-lignes : total = somme des lignes ; la réponse, le reçu et l'OpenAPI n'ont **aucun** champ `discount`, `gross_total` ni « Remise » | APP, HTTP | T40 (serveur du Lot 1) |
| | PAN-02 — reçu : une ligne par article avec taille, couleur, quantité × prix négocié, puis le total ; aucun coût | HTTP | T40 (serveur du Lot 1) |
| | PAN-03 — panier : prix de base pré-rempli et modifiable par ligne, total recalculé à chaque changement ; avertissement sous le minimum ; aucun texte « Remise » dans le DOM | UI | T40 |
| UC-PAP-01 [QC-4] | EXC-L3-01 — O échange CH taille M contre CH taille L à J+3 : aucun paiement, stock inchangé en quantité, deux mouvements | APP | T29 |
| | EXC-L3-02 — échange CH (15 000) contre RB (20 000) : différence 5 000 encaissée ; inverse : 5 000 rendus | APP | T29 |
| | EXC-L3-03 — à J+8 (délai 7) : E (réglage actif, sa vente) → `422 EXCHANGE_PERIOD_OVER` ; O → 201 + journal sensible « échange hors délai » | APP | T29 |
| | EXC-L3-04 — E, réglage désactivé (défaut à l'ouverture) → 403 ; réglage activé, sa vente dans le délai → 201 ; vente de E2 → 404 | HTTP | T29 |
| | EXC-L3-05 — bouton « Échanger » visible pour E seulement si le réglage est actif | UI | T42 |
| UC-PAP-02 | PHO-01 — `GET /articles?with_thumbnails=true` : un lien signé par article avec photo, expiré après 60 s ; boutique B → 404 | HTTP | T30 |
| | PHO-02 — grille de vignettes ; article sans photo : initiales, jamais une image cassée | UI | T43 |
| RG-X01, RG-X04 [QC-3] | SCN-L3-02 (stock au dixième) | DOM, APP | T31 |
| RG-X02 | SCN-L3-03 (achat en yards et en pièces) | DOM, APP | T31 |
| RG-X03, UC-TEX-01/02 | TEX-01 — vente au mètre 2,5 m : prix pré-rempli 6 250, modifiable ; 2,55 m → 400 (dixième) ; longueur > stock → `422 STOCK_INSUFFICIENT` (`available` en mètres) | APP, HTTP | T31 |
| | TEX-02 — vente à la pièce d'un article sans vente à la pièce → 400 `lines.sale_mode` | APP | T31 |
| | TEX-03 — bascule « Au mètre / À la pièce », prix de base de l'unité choisie pré-rempli | UI | T41 |
| RG-X05 | TEX-04 — raccourcis : pièce complète (5,49 m), demi-pièce (6 yards / 2 = 2,7 m arrondi au dixième), 1, 2, 3 m | HTTP, UI | T31, T41 |
| RG-X06, UC-TEX-03 | TEX-05 — chute 0,4 m : mouvement « Chute » −0,4, motif obligatoire, journal ; visible dans les écarts d'inventaire | APP | T31 |
| | TEX-06 — reçu : « 2,5 m × 2 500 », « 1 pièce (5,49 m) » | HTTP | T31 |
| UC-IMP-01 | IMP-01 — `GET /imports/templates/articles` pour P, X, M : colonnes du profil (M : Marque, Modèle ; X : Unité, Longueur d'une pièce), ligne d'exemple, feuille « Mode d'emploi », listes déroulantes (lieux, catégories, types de client) relues avec `openpyxl` | HTTP | T32 |
| | IMP-02 — modèle `trucks` ou `drivers` → 404 (type inexistant au Lot 3) | HTTP | T32 |
| UC-IMP-02 | SCN-L3-04 ; IMP-03 — aperçu : aucune écriture (compteurs de tables identiques avant/après) | APP, CTR | T32, T33 |
| | IMP-04 — 5 001 lignes → `422 IMPORT_TOO_MANY_ROWS` ; 5 000 → accepté | APP | T32 |
| | IMP-05 — fichier illisible, `.xls`, feuille vide → `400 IMPORT_FILE_INVALID` avec le détail | HTTP | T32 |
| | IMP-06 — CSV séparé par `;` et par `,`, UTF-8 avec et sans BOM → même aperçu | DOM | T32 |
| | IMP-07 — montants « 1 250 000 », « 1250000 FCFA », « 1 250 000 » (espace insécable) → 1 250 000 ; « 12,5 » → erreur « montant entier attendu » | DOM | T32 |
| | IMP-08 — clients : doublon de téléphone (dans le fichier ou en base) signalé et ignoré ; créance d'un client inconnu avec nom → client créé ; sans nom → erreur de ligne | APP | T34 |
| | IMP-09 — `preview_id` utilisé après 30 min → `410 IMPORT_PREVIEW_EXPIRED` ; utilisé deux fois → 200 et même lot (idempotent) | APP | T32, T33 |
| | IMP-10 — rapport : lignes importées, ignorées, éléments créés ; `errors.xlsx` reprend ligne, colonne, problème | HTTP | T35 |
| | IMP-11 — import créances avec `receivables` éteint → `403 MODULE_DISABLED` ; fournisseurs avec `purchases` éteint → idem | HTTP | T34 |
| UC-IMP-03 [QC-6] | SCN-L3-05 | APP | T35 |
| | IMP-12 — écran d'aperçu : « 3 articles nouveaux seront créés », erreurs « Ligne 14 : le prix est vide » ; bouton « Importer les lignes valides » | UI | T44 |
| | IMP-13 — liste des lots ; « Annuler l'import » absent pour C | UI | T45 |
| RG-T01 | AUD-L3-01 — journal : changement de type, ligne vendue sous le prix minimum, échange hors délai, chute, import (« Importer », numéro `IMP-…`), annulation de lot | APP | T27–T35 |
| RG-T05 | NUM-01 — `IMP-000001`, `IMP-000002` continus ; un lot annulé garde son numéro ; P et B commencent chacune à `IMP-000001` | CTR | T32 |
| Module `import` | MOD-L3-01 — avant T46 : activer `import` → `422 MODULE_NOT_YET_AVAILABLE` ; après T46 : activable, routes `x-module: import`, module éteint → `403 MODULE_DISABLED` et entrée « Import » absente du menu | HTTP, UI | T46 |

## 2. Scénarios de référence chiffrés

### SCN-L3-01 — Panier multi-lignes à prix négocié, sans remise (QC-2)

| # | Action (P, E, 10/11 10:00 D) | Résultat attendu exact |
| --- | --- | --- |
| 1 | Panier : 2 × CH taille M, Blanc, prix négocié **14 000** (base 15 000) ; 1 × RB taille 40 à **20 000** | lignes 28 000 et 20 000 ; total 48 000 ; aucun avertissement ; aucun champ de remise dans la réponse |
| 2 | Lecture par O | marge CH 28 000 − 2 × 9 000 = 10 000 ; marge RB 20 000 − 12 000 = 8 000 ; marge 18 000 ; ventes du jour 48 000 |
| 3 | Même panier, RB négociée à **16 500** (minimum 17 000) | total 44 500 ; avertissement « sous le prix minimum » sur la ligne RB, vente acceptée, journal sensible ; réglage « accord » actif → `422 PRICE_BELOW_MINIMUM` |
| 4 | Retour de 1 CH de l'étape 1 | remboursement 14 000 (prix de la ligne) ; ventes du jour −14 000 ; marge −5 000 |

### SCN-L3-02 — Textile : mètre, pièce, marge RG-X04 (QC-3)

Décision du client (QC-3) : le stock textile reste **au dixième de mètre** ; une pièce de 5,49 m retire 5,5 m, et l'écart se corrige par inventaire ou par chute. Aucun cas au centimètre.

| # | Action (X) | Attendu exact (stock au dixième) |
| --- | --- | --- |
| 1 | Achat 10 pièces de WX à 11 000 | stock 54,9 m ; coût au mètre 110 000 / 54,9 = 2 003,64 → **2 004** |
| 2 | Vente 2,5 m à 2 500 | total 6 250 ; marge 6 250 − 2,5 × 2 004 = **1 240** ; stock 52,4 m |
| 3 | Vente 1 pièce à 13 000 | stock retiré **5,5 m** ; marge 13 000 − 5,5 × 2 004 = **1 978** ; stock 46,9 m ; reçu « 1 pièce (5,49 m) » |
| 4 | 9 pièces vendues une à une | 8 acceptées (46,9 − 8 × 5,5 = 2,9 m) ; refus à la 9ᵉ (`422 STOCK_INSUFFICIENT`, `available` « 2.9 ») |
| 5 | Inventaire : 3,3 m comptés pour 2,9 m théoriques | écart +0,4 m validé (mouvement d'inventaire), stock 3,3 m ; à l'inverse, une chute de 0,4 m (motif Chute) retire 0,4 m — les deux voies de correction du dixième |

### SCN-L3-03 — Achat en yards et en pièces (RG-X02)

| # | Saisie | Attendu |
| --- | --- | --- |
| 1 | 20 yards à 1 000 | 20 × 0,9144 = 18,288 → **18,3 m** ; coût au mètre 20 000 / 18,3 = 1 092,9 → **1 093** |
| 2 | 0,5 yard | 0,4572 → **0,5 m** |
| 3 | 3 pièces d'un article sans longueur de pièce | 400 (`piece_length_m`) |

### SCN-L3-04 — Import Articles puis Stock de départ (P, par C)

| # | Fichier | Attendu |
| --- | --- | --- |
| 1 | Articles : 4 lignes (CH existant, 2 nouveaux, 1 sans nom) | aperçu : 2 valides, 1 doublon (CH, ignoré), 1 erreur « Ligne 5 : le nom est vide » ; « 2 articles nouveaux seront créés » ; import → `IMP-000001`, 2 articles, références `REF-…` générées |
| 2 | Stock de départ : 2 lignes (article nouveau, Boutique, 10, « 9 000 FCFA ») + 1 ligne d'un article inconnu | aperçu : article inconnu proposé à la création ; import → mouvement « Reprise de départ » +10, `unit_cost` 9 000, CMP 9 000, dernier coût 9 000, `source = import` |
| 3 | Même fichier réimporté | toutes les lignes en doublon (même article + lieu), rien d'écrit |
| 4 | E tente l'import | 403 ; C sur le modèle Clients → 403 |

### SCN-L3-05 — Annulation d'un lot (QC-6)

| # | Action | Attendu |
| --- | --- | --- |
| 1 | O annule `IMP-000002` (stock) le 15/11, aucune vente | 200 ; mouvement « Annulation » −10 ; lot « Annulé » ; journal |
| 2 | O annule `IMP-000001` (articles) après une vente d'un article importé | `422 IMPORT_CANCEL_BLOCKED`, `details.blocking` = `[{type: "sale", number: "V-000003"}]` ; rien ne change |
| 3 | Import du 10/11 annulé le 17/11 (7ᵉ jour) | 200 ; le 18/11 → `422 IMPORT_CANCEL_TOO_LATE` |
| 4 | Après annulation d'un import d'articles | articles archivés (rien d'effacé), nom et référence libérés : un nouvel import du même nom est accepté ; idem pour un import de clients : clients désactivés, téléphone libéré |
| 5 | C annule | 403 |

## 3. Sécurité

### 3.1 SEC-M — Lignes de la matrice touchées par le Lot 3

NM et ADM sans délégation : **404** sur toutes les lignes boutique (specs § 8.3).

| # | Action | Requêtes | Propriétaire | Employé | Comptable |
| --- | --- | --- | --- | --- | --- |
| M3-01 | Modèles et import articles, stock, fournisseurs | `GET /imports/templates/{articles,opening_stock,suppliers}`, `POST /imports/preview`, `POST /imports` | 200/201 | 403 | 200/201 |
| M3-02 | Import clients et créances | mêmes routes, `kind = customers`, `receivables` | 200/201 | 403 | 403 |
| M3-03 | Lots | `GET /imports`, `GET /imports/{id}`, `GET /imports/{id}/errors.xlsx` | 200 | 403 | 200 (ses modèles seulement ; lot de clients → 404) |
| M3-04 | Annuler un import | `POST /imports/{id}/cancel` | 200 | 403 | 403 |
| M3-05 | Échange | `POST /sales/{id}/returns` avec échange | 201 | 403, ou 201 sur sa vente si réglage actif | 403 |
| M3-06 | Vente multi-lignes à prix négocié (sans remise) | `POST /sales` | 201 | 201 | 403 |
| M3-07 | Changer le type de boutique | `POST /platform/shops/{id}/profile` | 403 | 403 | 403 (ADM : 200) |
| M3-08 | Déclarer une chute | `POST /adjustments` motif Chute | 201 | 403 | 201 |

### 3.2 SEC-N — Non-fuite

| ID | Rôle | Vérification |
| --- | --- | --- |
| SEC-N3-01 | Employé | aucune clé `cost`, `wac`, `margin`, `value` dans `POST/GET /sales` multi-lignes, reçu, `GET /articles?with_thumbnails=true`, vente au mètre et à la pièce (sentinelle : CMP de WX = 2 004) |
| SEC-N3-02 | Comptable | aperçu et rapport d'import : aucune vente, aucun client, aucune créance (RG-D03) ; message de blocage d'annulation lu par C : impossible (403) |
| SEC-N3-03 | Tous | un lien de vignette n'est délivré qu'après contrôle des droits ; le lien d'un fichier d'import n'est jamais renvoyé à l'employé |
| SEC-N3-04 | Garde-fou | la liste des routes balayées par SEC-N du Lot 1 inclut les routes `/imports…` (comparaison avec l'OpenAPI) |

### 3.3 SEC-I — Isolation

| ID | Requête | Attendu |
| --- | --- | --- |
| SEC-I3-01 | O de P : `POST /shops/P/imports` avec le `preview_id` d'un aperçu de B | 404, rien d'écrit |
| SEC-I3-02 | O de P : `GET /shops/P/imports/{lot de B}`, `/cancel`, `/errors.xlsx` | 404 |
| SEC-I3-03 | Import de stock dans P citant un lieu ou un article de B (par nom identique) | rattaché à P seulement ; jamais à l'objet de B |
| SEC-I3-04 | Même nom d'article, même téléphone client dans P et B | acceptés dans les deux (unicité par boutique) |
| SEC-I3-05 | ADM change le type de P : aucune donnée de B touchée | contrat |

## 4. Erreurs attendues par code

| ID | Entrée | HTTP | Code | `details` |
| --- | --- | --- | --- | --- |
| ERR3-01 | Changement de type, boutique non vide | 422 | `PROFILE_CHANGE_BLOCKED` | `blocking` par nature, avec compte |
| ERR3-02 | Échange hors délai par l'employé | 422 | `EXCHANGE_PERIOD_OVER` | `sold_on`, `exchange_days` |
| ~~ERR3-03~~ | ~~Remise > sous-total~~ — retiré (QC-2 : pas de remise) | — | — | — |
| ERR3-04 | Fichier illisible | 400 | `IMPORT_FILE_INVALID` | raison lisible |
| ERR3-05 | 5 001 lignes | 422 | `IMPORT_TOO_MANY_ROWS` | `max: 5000`, `rows` |
| ERR3-06 | Aperçu expiré | 410 | `IMPORT_PREVIEW_EXPIRED` | — |
| ERR3-07 | Annulation bloquée | 422 | `IMPORT_CANCEL_BLOCKED` | `blocking[]` (type, numéro) |
| ERR3-08 | Annulation après 7 jours | 422 | `IMPORT_CANCEL_TOO_LATE` | `imported_on` |
| ERR3-09 | Longueur au centième à la vente | 400 | `VALIDATION_ERROR` | `lines.quantity` |
| ERR3-10 | Activer `import` avant T46 | 422 | `MODULE_NOT_YET_AVAILABLE` | `module: import` |

## 5. Synthèse

| Catégorie | Nombre |
| --- | --- |
| Cas de la matrice (PRF, VOC, LOC, ART, PAN, EXC-L3, PHO, TEX, IMP, AUD-L3, NUM, MOD-L3) | 46 (DIS-01 à DIS-04 retirés, PAN-01 à PAN-03 et LOC-01 ajoutés le 2026-11-13) |
| Scénarios chiffrés | 5 (21 lignes) |
| Sécurité : matrice (8 lignes × 3 rôles), non-fuite (4), isolation (5) | 24 cellules + 9 |
| Erreurs par code | 9 (ERR3-03 retiré) |
