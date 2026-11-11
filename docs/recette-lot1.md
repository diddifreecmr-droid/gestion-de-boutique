# Plan de recette — Lot 1 (boutique Motos)

> Auteur : @qa · Statut : **à valider par l'orchestrateur** · Porté par la tâche **T24** du `docs/plan-lot1.md`.
> Sources : CDC (`Cahier des charges — Application de gestion de boutiques.md`), `specs.md` (§ 3, § 6, § 8, § 12),
> `design-system.md` § 8.
> Périmètre : socle, plateforme, catalogue, stock, achats, ventes et reçus, créances, dépenses, tableau de bord,
> alertes, journal. Le hors-ligne est **présent mais désactivé** (droit `offline_capture` = faux). Transferts,
> transport et import Excel sont **hors Lot 1** : leurs UC/RG n'apparaissent ici que pour dire qu'ils ne sont pas testés.
> Les questions ouvertes du § 6 sont citées dans les cas concernés sous la forme **[Q-nn]** : la valeur attendue
> de ces cas reste **à confirmer** et ils ne sont pas bloquants pour la recette tant que la réponse manque.

## 0. Conventions

| Élément | Convention |
| --- | --- |
| Niveaux | **DOM** domaine (pytest, Python pur) · **APP** cas d'utilisation + adaptateurs mémoire · **CTR** contrat de port (même suite `--backend=memory` et `--backend=postgres`) · **HTTP** pytest + httpx sur `create_app()` · **UI** vitest + Testing Library · **E2E** Playwright Chromium 360 × 800 + axe-core |
| Horloge | Toujours le port `Clock` figé (jamais l'heure système). Douala = UTC+1, sans heure d'été. Notation `10/11 23:30 D` = heure de Douala ; `22:30Z` = UTC |
| Données de base (**JDD-0**) | Boutique A « Motos Garoua », profil Motos, ouverte par `OpenShop`. Lieux : Garoua-Boulaï (entrepôt), Ngaoundéré (entrepôt), Garoua (boutique, point de vente). Utilisateurs : **O** propriétaire, **V** vendeur (lieu habituel Garoua), **V2** second vendeur, **C** comptable, **CH** chauffeur. Article **HJ** = Haojue HJ125-8, prix de base 780 000. Modes : Espèces, Orange Money (OM), MTN Mobile Money (MTN), Virement, Chèque, Autre |
| Boutique témoin | Boutique **B** « Motos Ngaoundéré » (autre compte commerçant), propriétaire **OB**, mêmes données de départ |
| Erreurs | Toujours le format `{"error": {"code", "message", "details"}}` (specs § 6.1). « 403 » sans autre mention = `403 FORBIDDEN` **et** une entrée « Accès refusé » au journal (RG-D01) |
| Montants | Entiers FCFA. Affichage vérifié en UI/E2E sous la forme « 1 250 000 FCFA » (espace insécable fine ou normale, à figer dans `shared/format`) |

## 1. Matrice de traçabilité

Légende des cas : les identifiants `SCN-*` (§ 2), `SEC-*` (§ 3), `ERR-*` (§ 4) et `E2E-*` (§ 5) sont détaillés plus bas ;
les autres sont décrits directement dans la matrice.

### 1.1 Cas d'utilisation

| UC | Cas de test (ID — vérification) | Niveau | Tâche |
| --- | --- | --- | --- |
| UC-SOC-01 | PLT-01 — `OpenShop` Motos crée 3 lieux (types et point de vente exacts), 6 modes de paiement, 5 catégories de dépense, réglages par défaut (reçu 80 mm, 1 exemplaire, seuil 2, prix minimum désactivé), propriétaire `must_change_pin = true` | APP | T10 |
| | PLT-02 — téléphone déjà connu : rattachement à la nouvelle boutique, aucun second `USER` [Q-27] | APP, CTR | T10 |
| | PLT-03 — nom, ville ou téléphone manquant → `400 VALIDATION_ERROR` (`details.fields`) | HTTP | T10 |
| | PLT-04 — `POST /platform/shops` par O (non admin) → 403 ; par l'admin → 201 | HTTP | T10 |
| | PLT-05 — console plateforme : ouvrir une boutique puis se connecter comme son propriétaire | E2E | T12 |
| UC-SOC-02 | AUTH-01 — connexion correcte → JWT d'accès + cookie de rafraîchissement `HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth` | HTTP | T08 |
| | AUTH-02 — `must_change_pin` : toute route métier → `403 PIN_CHANGE_REQUIRED`, seules `/auth/change-pin` et `/me` répondent | HTTP | T08 |
| | AUTH-03 — rechargement de page : la session reste ouverte (rafraîchissement unique, un seul appel `/auth/refresh` pour 5 requêtes parallèles en 401) | UI, E2E | T12 |
| | SEC-L01 à SEC-L09 (blocage), SEC-X01 à SEC-X06 (compte désactivé), E2E-08 | HTTP, E2E | T08, T12 |
| UC-SOC-03 | AUTH-04 — `GET /me` liste les boutiques et le rôle de chacune ; E2E-09 (changement de boutique) ; SEC-I01 à SEC-I14 | HTTP, E2E | T08, T12 |
| UC-SOC-04 | MEM-01 — ajout d'un vendeur : lieu habituel obligatoire et point de vente (Ngaoundéré → `422`) | APP | T10 |
| | MEM-02 — code provisoire de 6 chiffres renvoyé une seule fois, jamais relisible ; `must_change_pin = true` | APP, HTTP | T08, T10 |
| | MEM-03 — changement de rôle V → C : effet dès la requête suivante, sans reconnexion (`GET /sales` → 403) | HTTP | T08 |
| | MEM-04 — `reset-pin` : ancien code refusé, nouveau code provisoire accepté, `must_change_pin = true` | APP | T08 |
| | SEC-X01 à SEC-X06 (désactiver/réactiver), SEC-R01 à SEC-R06 (déconnexion à distance), SEC-X05 (dernier propriétaire, RG-D08) | APP, HTTP | T08, T10 |
| | Ajouter un chauffeur crée sa fiche chauffeur — **non testé (module 13, Lot 2)** [Q-26] | — | — |
| UC-SOC-05 | LOC-01 — créer et renommer un lieu ; le nom reste unique (`409 DUPLICATE`) | APP, HTTP | T10 |
| | LOC-02 — désactiver Garoua avec 1 moto en stock → refusé (`422`, code à préciser [Q-31]) ; à 0 → accepté | APP | T10, T14 |
| | LOC-03 — désactiver le dernier point de vente → refusé | APP | T10 |
| UC-SOC-06 | SET-01 — chaque réglage modifié (format, pied de page, exemplaires, seuil, prix minimum, modes, catégories) crée une entrée de journal avec valeur avant/après | APP | T09, T10 |
| | SET-02 — exemplaires 0 ou 4 → 400 ; pied de page de 201 caractères → 400 | HTTP | T10 |
| | SET-03 — ajout d'un mode de paiement « Wave » : proposé à la vente suivante | APP, E2E | T10, T21 |
| UC-SOC-07 | PIN-01 — 123456, 654321, 000000, 111111, 121212 → `422 PIN_TOO_SIMPLE` ; 482915 → 200 et `must_change_pin = false` | APP, HTTP | T08 |
| | PIN-02 — code actuel faux → 401, compté comme essai faux [Q-28] | APP | T08 |
| | PIN-03 — les deux saisies du nouveau code diffèrent → message sous le champ, aucune requête | UI | T12 |
| UC-SOC-08 | PWA-01 — manifeste valide (nom, icônes 192 et 512, `display: standalone`, `start_url`), service worker actif, page servie hors réseau = coquille + « Connexion nécessaire » | E2E | T12 |
| | Bannière « Installer l'application » réelle sur Android — **test terrain seulement** (non automatisable) | Terrain | T24 |
| UC-SOC-09 | ALR-01 — cloche : compteur = alertes non lues de l'utilisateur dans la boutique active ; `POST /alerts/{id}/read` le décrémente | HTTP, E2E | T09, T22 |
| | ALR-02 — un appui ouvre l'élément lié (vente, article, créance, demande de prix) | E2E | T22 |
| | ALR-03 — V ne voit jamais les alertes de O ; `POST /alerts/{id_de_O}/read` par V → 404 | HTTP | T09 |
| | ALR-04 — déduplication (`dedup_key`) : même stock bas deux fois → une seule alerte (voir LOW-01) | CTR | T09 |
| UC-STK-01 | CAT-01 — marque « Haojue » + modèle « HJ125-8 » → `display_name` « Haojue HJ125-8 » | DOM, APP | T13 |
| | CAT-02 — même couple → `409 DUPLICATE` avec `details.existing_id` ; variante « haojue / hj125-8 » [Q-33] | APP, HTTP | T13 |
| | CAT-03 — C crée un article sans prix → 201 ; C envoie `base_price` → 403 [Q-14] | HTTP | T13 |
| | CAT-04 — article sans prix de base : à la vente le champ prix est vide et obligatoire (« Le prix est vide ») | UI | T21 |
| UC-STK-02 | CAT-05 — modification : journal avec valeur avant/après | APP | T13 |
| | CAT-06 — renommage après une vente : la vente garde `article_name_snapshot` d'origine | APP | T13, T16 |
| | CAT-07 — `PATCH` avec `version` périmée → `409 VERSION_CONFLICT` (voir ERR-VER-01) | HTTP | T13 |
| UC-STK-03 | CAT-08 — `PUT /prices` 780 000 → 800 000 : `PRICE_HISTORY` (Base, 780 000, 800 000, auteur O, date) ; idem pour Minimum | APP | T13 |
| | CAT-09 — vente faite avant le changement garde `base_price_snapshot` = 780 000 | APP | T13, T16 |
| | CAT-10 — V et C sur `PUT /prices` → 403 ; prix minimum > prix de base [Q-34] | HTTP | T13 |
| UC-STK-04 | CAT-11 — archivage à stock 0 : absent de la recherche de vente et d'achat, présent dans l'historique et le tableau de bord | APP, E2E | T13, T20 |
| | CAT-12 — archivage avec 1 moto à Garoua → refusé (`422`, code [Q-31]) ; C sur archive → 403 | APP, HTTP | T13 |
| | CAT-13 — réactivation : l'article revient dans les listes | APP | T13 |
| UC-STK-05 | STK-01 — `GET /stock` : une ligne par article, une colonne par lieu actif dans l'ordre d'affichage, « En route » (toujours 0 au Lot 1), « Total » | HTTP | T14 |
| | STK-02 — V reçoit quantités et prix de base, **aucun** coût (SEC-N01) | HTTP | T14 |
| | STK-03 — pastille orange « Stock bas » sous le seuil, rouge « Rupture » à 0, toujours mot + icône | UI, E2E | T20 |
| | STK-04 — recherche dès la 1ʳᵉ lettre, filtre par lieu, tri par quantité | UI | T20 |
| UC-STK-06 | STK-05 — `GET /articles/{id}/movements` : plus récent en premier ; type, lieu, quantité signée, `balance_after`, document lié, auteur. V → 403 | HTTP | T14 |
| UC-STK-07 | INV-01 — lancement à Garoua → `INV-000001`, statut En cours ; la quantité théorique est **absente** de la réponse tant que l'inventaire est en cours | HTTP | T14 |
| | INV-02 — comptage partiel, reprise plus tard (`PUT counts` deux fois) sans perte | APP | T14 |
| | INV-03 — validation : écart = compté − théorique, valeur = écart × CMP ; motif obligatoire si écart ≠ 0 (sinon 400) | APP | T14 |
| | INV-04 — chaque écart crée un ajustement ; O reçoit une alerte avec la valeur totale des écarts | APP | T09, T14 |
| | INV-05 — second inventaire en cours sur Garoua → refusé ; sur Ngaoundéré → accepté | APP, CTR | T14 |
| | INV-06 — 2 ventes pendant le comptage : message « 2 ventes enregistrées depuis le début du comptage » ; théorique 10 au départ, 2 ventes, 7 comptées → écart −1 (théorique à la validation) **ou** −3 (au lancement) [Q-17] | APP | T14 |
| UC-STK-08 | ADJ-01 — Ajustement −1, motif Casse : stock −1, mouvement « Ajustement − » | APP | T14 |
| | ADJ-02 — motif Autre sans note → 400 ; quantité 0 → 400 ; 1,5 moto → 400 (RG-T08) | DOM, HTTP | T04, T14 |
| | ADJ-03 — ajustement par C → alerte « ajustement » à O ; par O → aucune alerte | APP | T09, T14 |
| | ADJ-04 — ajustement − supérieur au stock → `422 STOCK_INSUFFICIENT` (ERR-STK-04) | APP | T14 |
| | ADJ-05 — ajustement + : CMP inchangé (RG-T12) ; coût du mouvement d'entrée [Q-16] | DOM, APP | T14, T15 |
| UC-STK-09 | LOW-01 — seuil HJ = 5. Stock 6 → vente → 5 : alerte ? [Q-18]. Stock 6 → vente de 2 → 4 : **une** alerte à O et C ; → 3 : aucune nouvelle alerte ; achat +4 → 7 ; vente de 3 → 4 : nouvelle alerte | APP, CTR | T09, T14 |
| | LOW-02 — article sans seuil : le seuil par défaut de la boutique (2) s'applique | APP | T14 |
| UC-STK-10 | VAL-01 — `GET /stock/value` : par lieu et total, quantité × CMP ; vue complémentaire quantité × dernier coût ; stock abîmé et en route à part (voir SCN-09) | HTTP | T14, T19 |
| | VAL-02 — V et CH → 403 | HTTP | T14 |
| UC-ACH-01 | SCN-01 étape 1, SCN-02, SCN-03 | DOM, APP | T15 |
| | PUR-01 — lieu de réception pré-rempli Garoua-Boulaï (profil Motos) [Q-01] ; date du jour pré-remplie | UI | T20 |
| | PUR-02 — écart de prix avec le dernier coût 520 000 : 52 000 → message « Le dernier achat était à 520 000 FCFA. Confirmer 52 000 FCFA ? » ; 364 000 (−30 % exact) → pas de message ; 363 999 → message | UI | T20 |
| | PUR-03 — article introuvable → « Créer l'article » sans quitter l'écran ; la ligne reprend l'article créé | E2E | T20 |
| | PUR-04 — quantité 0, négative ou décimale → 400 ; prix unitaire 0 [Q-35] | HTTP | T15 |
| | PUR-05 — numéros `A-000001`, `A-000002` continus (voir ERR-VER-03) | CTR | T06, T15 |
| UC-ACH-02 | SUP-01 — création ; nom en double → `409 DUPLICATE` ; création rapide depuis l'achat | APP, E2E | T15, T20 |
| | SUP-02 — fournisseur avec achats : seule la désactivation existe (aucune route `DELETE`) ; fiche : total acheté sur la période | HTTP | T15 |
| UC-ACH-03 | SCN-04 (rejeu du CMP) | DOM, APP | T15 |
| | PUR-06 — 10 reçues à Garoua, 8 vendues : correction à 8 → acceptée (stock 0) ; à 7 → refusée [Q-07] | APP | T15 |
| | PUR-07 — C corrige un achat daté du 03/11 : le 10/11 → 200 ; le 11/11 → refusé [Q-08] ; O → toujours 200 | APP, HTTP | T15 |
| | PUR-08 — motif absent → 400 ; journal avant/après | APP | T15 |
| UC-ACH-04 | PUR-09 — O annule l'achat P2 de SCN-04 (variante 1, avant correction) : mouvements « Annulation » −5, CMP rejoué = 500 000, achat barré | APP | T15 |
| | PUR-10 — annulation refusée si une partie a quitté le lieu (1 vendue) ; C → 403 [Q-13] | APP, HTTP | T15 |
| UC-ACH-05 | PUR-11 — liste par date décroissante ; filtres période, fournisseur, article, lieu ; totaux en tête | HTTP | T15 |
| UC-ACH-06 | PUR-12 — achat de 10 800 000 : paiement 4 000 000 → « Payé en partie » ; + 6 800 000 → « Payé » ; + 1 → `422 OVERPAYMENT` (ERR-OVR-05) | APP | T15 |
| UC-VEN-01 | SCN-09 (S1 : deux modes), E2E-01 | APP, E2E | T16, T21 |
| | SAL-01 — 2 lignes dans la même vente ; paiement 300 000 Espèces + 200 000 OM pour 500 000 | APP | T16 |
| | SAL-02 — montant remis 800 000 pour 780 000 → « Monnaie à rendre : 20 000 FCFA » (non envoyé au serveur ou ignoré du total) | UI | T21 |
| | SAL-03 — V envoie `location_id` = Garoua : 201 ; un autre lieu → refusé [Q-36] ; O choisit tout point de vente ; lieu non point de vente → 422 | APP | T16 |
| | SAL-04 — dernier mode utilisé présélectionné ; quantité 1 par défaut ; stock du lieu affiché | UI | T21 |
| | SAL-05 — vente comptant dont les paiements sont inférieurs au total [Q-12] | APP | T16 |
| | SAL-06 — idempotence : même `id` rejoué → 200, même numéro, un seul mouvement de stock ; même `id` avec un autre contenu [Q-37] | HTTP | T16 |
| | ERR-STK-01 à ERR-STK-05 | APP, HTTP | T14, T16 |
| UC-VEN-02 | SCN-01 étape 7, E2E-02 | APP, E2E | T16, T17, T21 |
| | SAL-07 — crédit sans client → 400 ; client créé en ligne (nom + téléphone + type) ; acompte 0 accepté | APP | T16 |
| | SAL-08 — rappel, garant, pièces jointes enregistrés sur la créance ouverte | APP | T17 |
| | ERR-CRD-01 à ERR-CRD-04 | APP, HTTP | T16 |
| UC-VEN-03 | ERR-PRM-01 à ERR-PRM-09 ; E2E-06 | APP, HTTP, E2E | T16, T21 |
| UC-VEN-04 | RCP-01 — DTO de reçu : en-tête (nom, ville, téléphone, NIU/RCCM si renseignés), « Reçu de vente », numéro, date et heure, vendeur, client, lignes avec couleur et châssis (RG-M03), total, payé par mode, reste, monnaie rendue, mentions, pied | HTTP | T16 |
| | RCP-02 — aucun coût ni marge dans le DTO, **même pour O** (SEC-N04) | HTTP | T16 |
| | RCP-03 — 1ʳᵉ impression sans mention ; 2ᵉ → « Duplicata » [Q-25] ; vente annulée → « Annulé » | UI, E2E | T21 |
| | RCP-04 — rendu `thermal-58`, `thermal-80`, `a4-a5` : `@page` à 58 mm / 80 mm / A5 ; aucun débordement horizontal (émulation `print`) | E2E | T21 |
| | RCP-05 — « Partager » : PDF produit côté client, module chargé à la demande (absent du bundle initial) ; repli téléchargement | E2E | T21 |
| | RCP-06 — impression sur l'imprimante thermique du commerçant — **test terrain** | Terrain | T24 |
| UC-VEN-05 | SAL-09 — liste du jour par défaut, plus récente en haut ; nombre et total de la période ; filtres période, vendeur, article, mode, comptant/crédit ; pastilles « Crédit » / « Annulée » | HTTP, E2E | T16, T21 |
| | SAL-10 — V ne voit que ses ventes et ses totaux (SEC-M, ligne « Voir les ventes ») | HTTP | T16 |
| | SAL-11 — recherche par châssis « LBX123 » → la vente (RG-M02) | APP | T16 |
| UC-VEN-06 | RPT-01 — V signale une erreur sur sa vente → alerte « Erreur signalée » à O ; sur la vente de V2 → 404 | APP, HTTP | T16 |
| | RPT-02 — O répond et passe le signalement à « Traité » : V voit la réponse | APP | T16 |
| UC-VEN-07 | MOD-01 — O change le prix 780 000 → 760 000 (motif) sur la vente de SCN-01 : coûts figés inchangés, marge 240 000 → 220 000, créance 480 000 → 460 000, journal avant/après | APP | T16, T17 |
| | MOD-02 — changer l'article ou la quantité → refusé (passer par retour/annulation) ; motif absent → 400 ; V → 403 | APP, HTTP | T16 |
| | MOD-03 — baisse du prix sous le montant déjà payé ; changement de date (quel jour porte l'écart ?) [Q-06] | APP | T16 |
| UC-VEN-08 | SCN-06 | APP | T16, T17 |
| UC-VEN-09 | SCN-05 | APP | T16, T19 |
| | EXC-01 — échange : retour de HJ (780 000) + nouvelle vente d'un modèle à 800 000 → seule la différence 20 000 est payée ; les deux mouvements de stock existent | APP | T16 |
| | EXC-02 — retour d'une quantité supérieure au reste non rendu → refusé (code [Q-31]) | APP | T16 |
| UC-VEN-10 | OFF-01 à OFF-10 (ossature désactivée, puis droit activé en configuration de test) ; E2E-05 | HTTP, E2E | T23 |
| UC-VEN-11 | CUS-01 — recherche par nom ou téléphone ; fiche : total acheté, total dû, historique | HTTP | T16 |
| | CUS-02 — téléphone en double dans la boutique → `409 DUPLICATE` (ERR-DUP-04) ; même téléphone dans B → accepté | APP, CTR | T16 |
| | CUS-03 — V ne voit que les clients de ses ventes [Q-20] ; photo de pièce d'identité : O et vendeur responsable seulement (SEC-N06) | HTTP | T16 |
| UC-CRE-01 | SCN-01 étape 7 ; REC-01 — vendeur responsable = vendeur de la vente ; changement par O [Q-21] | APP | T17 |
| UC-CRE-02 | SCN-08 (créance ancienne) ; REC-02 — V → 403 [Q-15] | APP, HTTP | T17 |
| UC-CRE-03 | SCN-07 ; E2E-03 | APP, E2E | T17, T21 |
| | REC-03 — client avec 2 créances (01/09 et 01/10) : versement sans choix → la plus ancienne ; choix explicite respecté | APP | T17 |
| UC-CRE-04 | REC-04 — en tête : total à recevoir, nombre de clients débiteurs, versements reçus aujourd'hui ; tri par reste décroissant | HTTP | T17 |
| | REC-05 — filtres d'ancienneté : ouvertes il y a 30, 31, 60, 61, 90, 91 jours → classes « < 30 » [Q-19], « 31–60 », « 61–90 », « > 90 » ; « rappel dépassé » ; « sans versement depuis plus de 30 jours » | APP | T17 |
| UC-CRE-05 | REC-06 — relevé de SCN-07 : vente 780 000 → acompte 300 000 (reste 480 000) → versement 200 000 (reste 280 000) → versement 280 000 (reste 0) | HTTP | T17 |
| UC-CRE-06 | REM-01 — rappel au 01/12 : le 01/12 (worker, `Clock` 01/12 00:00 D) alerte « Rappel créance » au vendeur responsable et à O, une seule fois même si la tâche tourne deux fois | APP | T09, T17 |
| | REM-02 — reporter, marquer « fait » ; aucun envoi au client (aucun port d'envoi n'existe) | APP | T17 |
| UC-CRE-07 | GUA-01 — garant (nom, téléphone, lien) ; pièce d'identité : URL signée 60 s pour O et le vendeur responsable, 403 pour V2 et C (SEC-N06) | HTTP | T17 |
| UC-CRE-08 | SCN-07 (annulation du versement soldant) | APP | T17 |
| UC-CRE-09 | SCN-08 | APP | T17 |
| UC-DEP-01 | EXP-01 — 25 000 Carburant → `D-000001`, mode Espèces par défaut ; « Autre » sans description → 400 ; montant 0 → 400 ; tag créé à la volée | APP, HTTP | T18 |
| | EXP-02 — saisie sans réseau → « Connexion nécessaire », formulaire conservé (E2E-05) | E2E | T22, T23 |
| UC-DEP-02 | EXP-03 — les 5 catégories de base se renomment mais ne se désactivent pas (422) ; une catégorie ajoutée se désactive ; C sur catégories → 403 | APP, HTTP | T18 |
| | EXP-04 — tag « Groupe » puis « groupe » → même tag ; fusion « groupe » → « groupe électrogène » par O : dépenses ré-étiquetées, totaux par tag fusionnés ; C sur fusion → 403 | APP | T18 |
| UC-DEP-03 | EXP-05 — liste du jour, totaux, répartition par catégorie, filtres période, catégorie, tag, lieu, auteur, mode | HTTP | T18 |
| UC-DEP-04 | EXP-06 — C saisit le 10/11 à 15:00 D : modification à 23:59:59 D → 200 ; à 00:00:00 D le 11/11 → refusé (code [Q-31]) ; O → toujours 200 ; annulation sans motif → 400 ; annulée hors totaux [Q-11] | APP | T18 |
| UC-DEP-05 | EXP-07 — « Refaire cette dépense » : montant, catégorie, tags, bénéficiaire repris, date du jour, nouveau numéro | UI, APP | T18, T22 |
| UC-TDB-01 | SCN-09 ; E2E-04 | APP, E2E | T19, T22 |
| | DSB-01 — sections 1 à 4 et 6 présentes ; section 5 « Camions » absente au Lot 1 [Q-29] | UI | T22 |
| UC-TDB-02 | DSB-02 — périodes Aujourd'hui, Hier, Cette semaine (lundi → aujourd'hui), Ce mois, Mois dernier, Période libre (voir SCN-09) ; graphique par jour, total et moyenne | APP, UI | T19, T22 |
| UC-TDB-03 | DSB-03 — « Voir aussi au CMP » : marge au CMP + écart (SCN-09 : 720 000, écart 60 000) | APP, E2E | T19, T22 |
| UC-TDB-04 | DSB-04 — détails : ventes du jour, paiements par mode, dépenses par catégorie, créances (SCN-09) | HTTP | T19 |
| UC-TDB-05 | DSB-05 — accueil V : « Nouvelle vente », « Versement », ses ventes du jour (nombre, montant), ses rappels du jour ; aucune donnée de V2 | HTTP, E2E | T19, T22 |
| | DSB-06 — accueil C : « Achat », « Dépense », « Inventaire » (« Déplacer du stock » absent au Lot 1), alertes de stock, valeur du stock, dépenses du jour ; aucune donnée de vente (SEC-N02) | HTTP, E2E | T19, T22 |
| | Accueil Chauffeur — **non testé (Lot 2)** ; au Lot 1 seul SEC-N03 s'applique | — | — |
| UC-JRN-01 | AUD-01 — liste la plus récente en haut ; phrase « 10/11 14 h 32 — Paul (Vendeur) a enregistré la vente V-000124 : 1 moto Haojue HJ125-8, 780 000 FCFA » ; filtres période, utilisateur, type, module | HTTP, UI | T09, T22 |
| | AUD-02 — pastille « sensible » sur : annulation, modification de prix, vente sous le minimum, ajustement, changement de droits | APP | T09 |
| UC-JRN-02 | AUD-03 — onglet « Historique » d'une vente modifiée : date, auteur, champ, ancienne et nouvelle valeur, motif | HTTP | T09 |
| UC-JRN-03 | AUD-04 — activité de V : actions et connexions (date, appareil « Android — Chrome ») [Q-23] | HTTP | T08, T09 |

**UC du périmètre sans test automatisé** : UC-SOC-08 (installation réelle, terrain seulement) ; la partie « fiche
chauffeur » d'UC-SOC-04 et l'accueil Chauffeur d'UC-TDB-05 (dépendent du Lot 2) ; la section « Camions » d'UC-TDB-01
(Lot 2) ; l'impression thermique réelle d'UC-VEN-04 (terrain). UC-VEN-10 n'est testé que comme fonction désactivée,
plus son ossature avec le droit activé. Hors Lot 1 et non testés : UC-TRF-*, UC-TRA-*, UC-IMP-*, et UC-CRE-02 par import.

### 1.2 Règles de gestion

| RG | Cas de test | Niveau | Tâche |
| --- | --- | --- | --- |
| RG-D01 | SEC-M (toute la matrice) : chaque refus = 403 + entrée « Accès refusé » ; masquer un bouton ne suffit pas (appel direct à l'API) | HTTP | T07, T09 |
| RG-D02 | SEC-N01, SEC-N04, SEC-N05 ; E2E-01 (aucun coût dans le DOM vendeur) | HTTP, E2E | T07, T16, T24 |
| RG-D03 | SEC-N02 ; DSB-06 | HTTP | T07, T19 |
| RG-D04 | **Hors Lot 1** (déplacements) | — | — |
| RG-D05 | SEC-N03 (au Lot 1 : le chauffeur n'obtient aucun prix sur aucune route) | HTTP | T07 |
| RG-D06 | SEC-X01 à SEC-X06 | APP, HTTP | T08 |
| RG-D07 | SEC-R01 à SEC-R06 | APP, HTTP | T08 |
| RG-D08 | SEC-X05 | APP | T10 |
| RG-T01 | AUD-05 — test paramétré : chaque UC qui modifie l'état, chaque connexion, déconnexion, réglage → ≥ 1 entrée de journal du bon type, dans la même transaction (un échec du journal annule l'action) ; impression [Q-25] ; connexion d'un utilisateur à plusieurs boutiques [Q-23] | APP | T09 |
| RG-T02 | AUD-06 — l'OpenAPI ne contient **aucune** route `DELETE` métier ; modifications avec avant/après | HTTP | T02, T09 |
| RG-T03 | SCN-06 ; UI : ligne barrée, pastille « Annulée », « Annulé le 10/11/2026 par O — motif : … », exclue de tous les totaux | APP, UI | T16, T21 |
| RG-T04 | AUD-07 — `captured_at` (= `X-Captured-At`), `received_at` (serveur), `device_id` (= `X-Device-Id`), `created_by` présents sur vente, achat, dépense, versement ; `X-Device-Id` absent → 400 | HTTP | T05, T16 |
| RG-T05 | ERR-VER-03 (20 ventes concurrentes sans trou) ; numérotation indépendante par boutique (SEC-I09) et par type (`V`, `R`, `A`, `D`, `INV`) ; un document annulé garde son numéro | CTR | T05, T06 |
| RG-T06 | OFF-05 (droit activé) | APP | T23 |
| RG-T07 | MNY-01 — `Money` refuse négatif et décimal ; montant négatif dans une saisie → 400 ; formatage « 1 250 000 FCFA », « 0 FCFA », « 780 000 FCFA » | DOM, UI | T03, T04 |
| RG-T08 | ADJ-02 ; `Quantity` refuse 1,5 en unité entière, accepte « 2.5 » en mètre (pour le Lot 3) | DOM | T04 |
| RG-T09 | ERR-DAT-01 à ERR-DAT-09 | APP, HTTP | T04, T16 |
| RG-T10 | SCN-01 étape 1, SCN-03 | DOM | T15 |
| RG-T11 | SCN-02, SCN-04 ; deux achats à la même date [Q-04] | DOM | T15 |
| RG-T12 | SCN-02, SCN-04 ; ventes, ajustements et retours ne changent pas le CMP | DOM, APP | T15 |
| RG-T13 | SCN-01, SCN-04 variante 2 (coûts figés non modifiés par une correction) | APP | T16 |
| RG-T14 | SCN-01, SCN-09 (marge et marge au CMP) | DOM, APP | T16, T19 |
| RG-T15 | SCN-10 (vente sans coût connu) [Q-16] | APP | T16, T19 |
| RG-T16 | CTR-STK-01 — projection `stock_level` = somme des mouvements après toute séquence (test de propriétés hypothesis : achats, ventes, retours, ajustements, annulations aléatoires) | DOM, CTR | T14 |
| RG-T17 | ERR-STK-01 à ERR-STK-05 | APP, HTTP | T14, T16 |
| RG-T18 | OFF-06 (droit activé seulement) | APP | T23 |
| RG-T19 | SET-03 ; référence facultative enregistrée et affichée sur le reçu | APP | T10, T16 |
| RG-T20 | SAL-01 ; ERR-OVR-02, ERR-OVR-03 | APP | T16 |
| RG-T21 | SCN-01, SCN-05, SCN-09 | APP | T19 |
| RG-T22 | OFF-01 à OFF-03 ; E2E-05 | HTTP, E2E | T23 |
| RG-T23 | OFF-07 (droit activé) | E2E | T23 |
| RG-T24 | OFF-08 (droit activé) | E2E | T23 |
| RG-T25 | E2E-05 (tableau de bord sans réseau : aucun montant affiché, pas même en cache) ; OFF-02 | E2E | T22, T23 |
| RG-T26 | ATT-01 — JPG, PNG, PDF ≤ 5 Mo acceptés ; GIF → 400 ; 5 Mo + 1 octet → 400 ; image 4000 px réduite à ≤ 1600 px côté client avant envoi ; MinIO indisponible → `503 STORAGE_UNAVAILABLE` | UI, HTTP | T16, T21 |
| RG-T27 | ALR-01 à ALR-04 ; « notification sur le téléphone » **non testée** (supprimée en V1 par D19) ; aucun port d'envoi vers un client | APP | T09 |
| RG-M01 | ERR-DUP-01 à ERR-DUP-03 | APP, CTR | T16 |
| RG-M02 | SAL-11 | APP | T16 |
| RG-M03 | RCP-01 | HTTP | T16 |
| RG-J01 | AUD-08 — le port de journal n'expose que `append` (CTR) ; aucune route de modification ; en PostgreSQL, `UPDATE`/`DELETE` sur `audit_entry` avec le rôle de l'API → refus de permission | CTR | T06, T09 |
| RG-J02 | **Non testable en recette** (conservation 10 ans) : vérifiée par la politique de sauvegarde (T25) | — | T25 |
| H5, H7, H13 | SCN-01, SCN-04, SCN-09 ; OFF-06 | APP | T16, T19, T23 |
| H9, H10 | ERR-PRM-* ; SEC-M ligne « Modifier ou annuler une vente » | APP, HTTP | T16 |
| H11 | SCN-06, SCN-07, SCN-08 (rien n'est effacé, tout reste lisible) | APP | T16, T17 |
| H20 | SAL-07 (client facultatif au comptant, obligatoire à crédit) | APP | T16 |

**RG du périmètre sans test** : RG-J02 (conservation, vérifiée par l'exploitation) ; la partie « notification sur le
téléphone » de RG-T27 (supprimée par décision D19) ; la journalisation de l'**impression** exigée par RG-T01, car aucune
route ne la reçoit [Q-25]. RG-T06, RG-T18, RG-T23 et RG-T24 ne sont testées qu'avec le droit `offline_capture` activé
en configuration de test. Hors Lot 1 : RG-D04, RG-X01 à RG-X06.

## 2. Scénarios de référence chiffrés

Tous les scénarios partent de JDD-0 et s'exécutent au niveau **APP** (adaptateurs mémoire), puis sont rejoués en
**HTTP** sur PostgreSQL (`tests/e2e_api`). Ils sont la base des critères A2 et A3.

### SCN-01 — Parcours CDC § 17.5, étapes Lot 1 (critère A2)

Les étapes 2 à 6 et 8 (voyage, déplacements, réception, clôture) sont hors Lot 1. **Adaptation Lot 1** : l'achat est
reçu à **Garoua**, car sans déplacement une moto reçue à Garoua-Boulaï ne peut pas être vendue [Q-01].

| # | Action (`Clock` 10/11 09:00 D) | Résultat attendu exact |
| --- | --- | --- |
| 1 | C : achat, 20 × HJ à 520 000, frais Douane 400 000, lieu Garoua, aucun fournisseur | `A-000001` ; total marchandise 10 400 000 ; total des frais 400 000 ; total 10 800 000 ; `fee_share` de la ligne 400 000 ; `final_unit_cost` 540 000 ; dernier coût HJ 540 000 ; CMP HJ 540 000 ; stock Garoua 20 ; mouvement « Entrée achat » +20, `unit_cost` 540 000, `balance_after` 20 ; statut de paiement « À payer » ; 1 entrée de journal « Créer » |
| 7 | V (10:30 D) : vente à crédit, client nouveau « Moussa A. » +237690000000 Particulier, 1 × HJ à 780 000, acompte 300 000 Espèces | 201 ; `V-000001` ; `total` 780 000, `paid` 300 000, `remaining` 480 000 ; créance ouverte : montant initial 480 000, statut En cours, vendeur responsable V, date d'ouverture 10/11/2026 ; stock Garoua 19 ; mouvement « Sortie vente » −1 |
| 7a | Lecture par O de `GET /sales/{id}` | ligne : `frozen_last_cost` 540 000, `frozen_wac` 540 000, `margin` 240 000, `margin_wac` 240 000 |
| 7b | Même lecture par V | aucune des 4 clés ci-dessus (SEC-N01) |
| 7c | `GET /dashboard?period=today` par O | ventes du jour 780 000 ; nombre 1 ; argent encaissé 300 000 ; marge 240 000 ; marge au CMP 240 000 ; taux de marge 30,8 % (240 000 / 780 000 = 30,769 %) [Q-10] ; total à recevoir 480 000 ; versements reçus aujourd'hui 0 ; valeur du stock 19 × 540 000 = 10 260 000 ; ventes sans coût connu 0 |
| 7d | Reçu (`GET /sales/{id}/receipt`) | mention « Vente à crédit » ; total 780 000 ; payé Espèces 300 000 ; reste à payer 480 000 ; aucun coût |

**Variante CDC littérale** (achat reçu à Garoua-Boulaï) : la vente de l'étape 7 à Garoua → `422 STOCK_INSUFFICIENT`,
`details.available = "0"`, `details.other_locations` contient Garoua-Boulaï : `"20"`. Ce résultat documente le trou
fonctionnel du Lot 1 [Q-01].

### SCN-02 — Exemple de CMP du CDC (critère A3)

| Niveau | Entrée | Attendu |
| --- | --- | --- |
| DOM | `Costing.new_wac(q_stock=10, wac=500 000, q_in=5, unit_cost=530 000)` | 510 000 |
| APP | Achat P1 (01/11) 10 × 500 000 à Garoua ; achat P2 (02/11) 5 × 530 000 | après P1 : CMP 500 000, dernier coût 500 000 ; après P2 : CMP **510 000**, dernier coût 530 000, stock 15 ; valeur du stock 7 650 000 (vue dernier coût 7 950 000) |
| DOM (propriétés) | séquences aléatoires d'achats sans sortie | CMP toujours entre le plus petit et le plus grand coût unitaire ; égal au coût quand le stock de départ est 0 |
| DOM | (10 × 500 000 + 3 × 530 000) ÷ 13 = 506 923,08 | arrondi à l'entier [Q-03] |

### SCN-03 — Répartition des frais au prorata (RG-T10)

| Cas | Lignes | Frais | Attendu |
| --- | --- | --- | --- |
| a | L1 2 × 600 000 (1 200 000) ; L2 1 × 300 000 (300 000) | Transport 100 000 | `fee_share` L1 80 000, L2 20 000 ; coût unitaire L1 640 000, L2 320 000 ; total 1 600 000 |
| b | L1 1 × 100 000 ; L2 1 × 200 000 | Autre « manutention » 100 000 | parts exactes 33 333,33 / 66 666,67 → L1 33 333, L2 **66 667** (le reste d'arrondi va à la ligne de plus forte valeur, specs § 5.3) ; somme des parts = 100 000 exactement |
| c | L1 3 × 100 000 | Douane 100 000 | `fee_share` 100 000 ; coût unitaire 133 333,33 → arrondi [Q-03] ; vérifier que 3 × coût unitaire et le total de l'achat restent cohérents |
| d | Frais « Autre » sans libellé | — | 400 `VALIDATION_ERROR` |

### SCN-04 — Correction d'achat et rejeu du CMP (UC-ACH-03, RG-T12, RG-T13)

**Variante 1 (aucune vente intercalée — attendu ferme)**

| # | Action | Attendu |
| --- | --- | --- |
| 1 | P1 (01/11) 10 × 500 000 | CMP 500 000 |
| 2 | P2 (02/11) 5 × **350 000** (faute de frappe pour 530 000) | CMP (5 000 000 + 1 750 000) ÷ 15 = 450 000 ; dernier coût 350 000. Note : écart de −30 % exact avec le dernier coût → pas de message de confirmation (PUR-02) |
| 3 | C corrige P2 le 03/11 : prix 530 000, motif « faute de frappe » | 200 ; CMP **510 000** ; dernier coût 530 000 ; stock 15 inchangé ; numéro `A-000002` conservé ; `version` +1 ; journal : `unit_price` 350 000 → 530 000, motif |

**Variante 2 (vente intercalée après P2 — coûts figés)** : après l'étape 2, V vend 1 × HJ à 700 000 le 02/11.
Figé sur la ligne : dernier coût 350 000, CMP 450 000, marge 350 000, marge au CMP 250 000. Après la correction :
la vente garde **exactement** ces 4 valeurs ; CMP 510 000 ; dernier coût 530 000 ; stock 14.

**Variante 3 (vente intercalée entre P1 et P2 — valeur à confirmer)** : P1 (01/11) 10 × 500 000 ; vente de 5 le
01/11 (stock 5) ; P2 (02/11) 5 × 350 000 → CMP (2 500 000 + 1 750 000) ÷ 10 = 425 000. Correction de P2 à 530 000 :

| Interprétation | Calcul | CMP attendu |
| --- | --- | --- |
| A — formule RG-T12 rejouée avec le stock réel au moment de P2 (« comme si saisi juste dès le départ ») | (5 × 500 000 + 5 × 530 000) ÷ 10 | **515 000** |
| B — `replay_wac` sur les seuls « mouvements d'entrée » (specs § 5.3) | (10 × 500 000 + 5 × 530 000) ÷ 15 | 510 000 |

Le test est écrit pour A (lecture littérale du CDC) et marqué « à confirmer » [Q-02].

### SCN-05 — Retour (UC-VEN-09, § 14.1)

Stock Garoua 10 HJ, dernier coût = CMP = 540 000 (choisis égaux pour ne pas dépendre de [Q-05]).

| Jour | Action | Attendu |
| --- | --- | --- |
| J (12/11) | V : vente comptant 2 × HJ à 780 000 Espèces | total 1 560 000 ; marge 2 × 240 000 = 480 000 ; stock 8 |
| J | Tableau de bord J | ventes 1 560 000 ; nombre 1 ; encaissé 1 560 000 ; marge 480 000 |
| J+1 | O : retour de 1 unité, état Vendable, motif « moteur bruyant », remboursement 780 000 Espèces | mouvement « Retour client » +1 Vendable ; stock 9 ; CMP inchangé 540 000 |
| J+1 | V : vente comptant 1 × HJ à 800 000 Espèces | stock 8 |
| J+1 | Tableau de bord J+1 | ventes 800 000 − 780 000 = **20 000** ; nombre **1** (un retour ne retire pas de vente) ; encaissé 800 000 − 780 000 = **20 000** ; marge 260 000 − 240 000 = **20 000** |
| J | Tableau de bord J relu après le retour | **inchangé** : 1 560 000 / 1 560 000 / 480 000 |
| J+1 | Second retour de 2 unités sur la même vente | refusé : 1 seule unité reste non rendue (EXC-02) |
| J+1 | Variante état Abîmé | stock vendable inchangé ; stock abîmé Garoua +1 ; valeur du stock hors abîmé ; `GET /stock/damaged` liste 1 HJ |

Cas non chiffrés tant que [Q-05] n'est pas tranché : remboursement différent de la valeur de la ligne (750 000 pour
780 000), retour d'une vente à crédit (baisse de créance et remboursement de l'acompte), retour sans aucune vente le
jour même (ventes du jour négatives).

### SCN-06 — Annulation de vente (UC-VEN-08, RG-T03)

| # | Action (10/11) | Attendu |
| --- | --- | --- |
| 1 | V : crédit 1 × HJ 780 000, châssis « LBX123 », acompte 300 000 Espèces | `V-000001` ; créance 480 000 ; stock Garoua 19 |
| 2 | V : versement 100 000 OM | `R-000001` ; reste 380 000 |
| 3 | V : `POST /sales/{id}/cancel` | 403 |
| 4 | O : annulation sans motif | 400 `VALIDATION_ERROR` |
| 5 | O : annulation, motif « client a renoncé », versements marqués « à rembourser » | 200 ; vente « Annulée » (annulée par O, date, motif) ; mouvement « Annulation » +1 → stock 20 ; créance « Annulée », hors total à recevoir (480 000 → 0 pour ce client) ; versement R-000001 marqué « à rembourser » |
| 6 | Tableau de bord du 10/11 | ventes 0 ; nombre 0 ; marge 0 ; total à recevoir 0. Argent encaissé : 400 000 tant que rien n'est remboursé, ou 0 [Q-09] |
| 7 | O annule à nouveau | `422 INVALID_STATE_TRANSITION` |
| 8 | Nouvelle vente avec le châssis « LBX123 » | 201 (le châssis d'une vente annulée est libre, RG-M01) ; numéro `V-000002` (V-000001 reste attribué, aucun trou) |
| 9 | `GET /sales?from=2026-11-10&to=2026-11-10` | V-000001 visible avec la pastille « Annulée » |

### SCN-07 — Versement qui solde une créance (UC-CRE-03, UC-CRE-08)

Créance de SCN-01 (reste 480 000), jour 15/11.

| # | Action | Attendu |
| --- | --- | --- |
| 1 | V : versement 200 000 OM | `R-000001` ; reste 280 000 ; statut En cours ; reçu : client, 200 000, OM, total déjà versé 500 000, reste 280 000 |
| 2 | V : versement 300 000 | `422 OVERPAYMENT`, `details.remaining = 280 000` ; rien n'est écrit |
| 3 | V : versement 280 000 Espèces | `R-000002` ; reste 0 ; statut **Soldée** ; reçu porte « Soldé » ; total à recevoir −280 000 |
| 4 | V : versement 1 | `422 OVERPAYMENT` |
| 5 | Tableau de bord du 15/11 | encaissé 480 000 ; versements reçus aujourd'hui 480 000 ; ventes 0 ; marge 0 |
| 6 | V : annulation de R-000002 | 403 |
| 7 | O : annulation de R-000002, motif « chèque sans provision » | statut revient **En cours** ; reste 280 000 ; R-000002 barré ; encaissé du 15/11 = 200 000 [Q-09 pour un versement annulé un autre jour] |

### SCN-08 — Mise en perte puis récupération (UC-CRE-02, UC-CRE-09)

| # | Action | Attendu |
| --- | --- | --- |
| 1 | O : créance ancienne, client « Ali B. », 300 000, origine 01/03/2026, description « 1 moto Haojue, cahier 2026 » | statut En cours ; ventes, nombre et marge du jour **inchangés** ; total à recevoir +300 000 |
| 2 | O : versement 50 000 (10/11) | reste 250 000 ; encaissé du 10/11 +50 000 |
| 3 | V : passage en perte | 403 |
| 4 | O : passage en perte, motif « client parti » (11/11) | statut **En perte** ; date et motif enregistrés ; total à recevoir −250 000 ; journal sensible |
| 5 | O : versement 100 000 (20/11) | accepté ; nature « Récupération sur perte » ; statut reste En perte ; encaissé du 20/11 +100 000 [Q-09] ; reste affiché 150 000 [Q-22] |
| 6 | O : versement 200 000 | refusé `OVERPAYMENT` si le plafond est le reste avant perte [Q-22] |
| 7 | O : passage en perte d'une créance Soldée | `422 INVALID_STATE_TRANSITION` |

### SCN-09 — Indicateurs § 14.1 sur une journée à cheval sur minuit

Données : P1 (05/11) 10 × 510 000 et P2 (06/11) 10 × 550 000, tous deux à Garoua → stock 20, CMP 530 000, dernier
coût 550 000. Créance ancienne « CA » de 300 000 ouverte le 05/11. Journée testée **D = mardi 10/11/2026**. Chaque
vente est enregistrée avec `Clock` figée à l'instant indiqué et sans date fournie (date = journée de Douala).

| Réf. | Instant UTC | Heure de Douala | Opération | Journée |
| --- | --- | --- | --- | --- |
| S0 | 09/11 22:55Z | 09/11 23:55 | comptant 1 × 800 000 Espèces | D−1 |
| S1 | 09/11 23:10Z | 10/11 00:10 | comptant 1 × 780 000 : 500 000 Espèces + 280 000 OM | D |
| S2 | 10/11 08:00Z | 10/11 09:00 | crédit 1 × 760 000, acompte 200 000 MTN → créance C2 560 000 | D |
| R1 | 10/11 09:00Z | 10/11 10:00 | versement 100 000 Espèces sur CA | D |
| S3 | 10/11 10:00Z | 10/11 11:00 | crédit 1 × 790 000, acompte 0 ; **annulée** à 12:00 D | D |
| E1 | 10/11 14:00Z | 10/11 15:00 | dépense 25 000 Carburant | D |
| E2 | 10/11 14:30Z | 10/11 15:30 | dépense 10 000 Repas, **annulée** à 16:00 D | D |
| S4 | 10/11 22:50Z | 10/11 23:50 | comptant 1 × 770 000 Espèces | D |
| S5 | 10/11 23:05Z | 11/11 00:05 | comptant 1 × 800 000 Espèces | D+1 |

Coûts figés de chaque ligne : dernier coût 550 000, CMP 530 000.

| Indicateur | D−1 (09/11) | **D (10/11)** | D+1 (11/11) |
| --- | --- | --- | --- |
| Ventes du jour | 800 000 | **2 310 000** (780 000 + 760 000 + 770 000) | 800 000 |
| Nombre de ventes | 1 | **3** (S3 exclue) | 1 |
| Argent encaissé | 800 000 | **1 850 000** (780 000 + 200 000 + 100 000 + 770 000) | 800 000 |
| Marge du jour | 250 000 | **660 000** (230 000 + 210 000 + 220 000) | 250 000 |
| Marge au CMP | 270 000 | **720 000** (250 000 + 230 000 + 240 000) ; écart 60 000 | 270 000 |
| Taux de marge | 31,3 % | **28,6 %** (660 000 / 2 310 000 = 28,571 %) [Q-10] | 31,3 % |
| Dépenses du jour | 0 | **25 000** (E2 exclue) | 0 |
| Résultat simple | 250 000 | **635 000** | 250 000 |
| Total à recevoir (fin de journée) | 300 000 | **760 000** (CA 200 000 + C2 560 000) | 760 000 |
| Versements reçus aujourd'hui | 0 | **100 000** (acompte de S2 exclu) [Q-24] | 0 |
| Valeur du stock (fin de journée) | 19 × 530 000 = 10 070 000 | **16 × 530 000 = 8 480 000** (vue dernier coût 8 800 000) | 15 × 530 000 = 7 950 000 |
| Comparaison avec hier (ventes) | — | +188,75 % ; encaissé +131,25 % ; marge +164 % [Q-10] | −65,4 % |

Détail « paiements du jour par mode » pour D : Espèces 1 370 000 (500 000 + 100 000 + 770 000), OM 280 000, MTN
200 000 ; total 1 850 000 = argent encaissé.

Contrôles de frontière (niveau HTTP, `GET /dashboard?period=today`) :

| `Clock` | Journée « aujourd'hui » attendue | Ventes affichées |
| --- | --- | --- |
| 10/11 22:59:59Z | 10/11 | 2 310 000 |
| 10/11 23:00:00Z | 11/11 | 0 (S5 n'existe pas encore à cet instant) |
| 10/11 23:10:00Z | 11/11 | 800 000 |
| `period=custom&from=2026-11-10&to=2026-11-10` | 10/11 | 2 310 000 |
| `period=week` avec `Clock` 10/11 12:00 D | lundi 09/11 → mardi 10/11 | 3 110 000 ; nombre 4 ; marge 910 000 ; moyenne par jour 1 555 000 |

### SCN-10 — Vente sans coût connu (RG-T15)

Article « Tricycle T1 » sans achat ; O passe un ajustement +2 à Garoua (motif « Erreur de saisie »), puis V vend 1 à
900 000. Attendu : ligne avec `margin = null` (« non calculable », jamais 900 000) ; tableau de bord : « 1 vente
sans coût connu » ; la marge du jour n'inclut pas cette ligne ; ventes du jour +900 000 [Q-16 : coût d'entrée d'un
ajustement +].

## 3. Tests de sécurité

### 3.1 SEC-M — Matrice des droits § 4.2, cellule par cellule (critère A10)

Test paramétré HTTP (T07 pour la `Policy`, T24 pour le balayage HTTP). Chaque cellule est un couple
(rôle, requête) avec son code attendu. **NM** = utilisateur authentifié sans rattachement à la boutique ;
**ADM** = administrateur plateforme sans délégation. Les colonnes NM et ADM valent **404** sur toutes les lignes
(specs § 8.3) ; elles ne sont pas répétées.

| # | Action § 4.2 | Requêtes testées | Propriétaire | Vendeur | Comptable | Chauffeur |
| --- | --- | --- | --- | --- | --- | --- |
| M01 | Gérer les utilisateurs et les réglages | `GET/POST /members`, `POST /members/{uid}/reset-pin`, `/revoke-devices`, `/unlock`, `PATCH /settings`, `POST/PATCH /payment-modes` | 200/201 | 403 | 403 | 403 |
| M02 | Gérer les lieux | `POST /locations`, `PATCH /locations/{id}` | 201/200 | 403 | 403 | 403 |
| M03 | Voir les lieux | `GET /locations` | 200 | 403 [Q-30] | 200 | 403 |
| M04 | Créer et modifier un article | `POST /articles`, `PATCH /articles/{id}` (sans prix) | 201/200 | 403 | 201/200 | 403 |
| M05 | Fixer prix de base et minimum | `PUT /articles/{id}/prices` ; `POST /articles` avec `base_price` | 200/201 | 403 | 403 [Q-14] | 403 |
| M06 | Archiver un article (UC-STK-04) | `POST /articles/{id}/archive` | 200 | 403 | 403 | 403 |
| M07 | Voir le stock (quantités) | `GET /stock`, `GET /articles` | 200 (avec coûts) | 200 (sans coût) | 200 (avec coûts) | 403 |
| M08 | Voir prix d'achat et valeur du stock | `GET /stock/value`, `GET /articles/{id}/movements`, `GET /stock/damaged` | 200 | 403 | 200 | 403 |
| M09 | Inventaire, ajustement | `POST /adjustments`, `POST /inventories`, `PUT /inventories/{id}/counts`, `POST /inventories/{id}/validate` | 201/200 | 403 | 201/200 | 403 |
| M10 | Enregistrer un achat, gérer les fournisseurs | `GET/POST /suppliers`, `GET/POST /purchases`, `PATCH /purchases/{id}`, `POST /purchases/{id}/payments` | 200/201 | 403 | 200/201 | 403 |
| M11 | Annuler un achat (UC-ACH-04) | `POST /purchases/{id}/cancel` | 200 | 403 | 403 [Q-13] | 403 |
| M12 | Enregistrer une vente | `POST /sales` | 201 | 201 | 403 | 403 |
| M13 | Voir les ventes | `GET /sales` ; `GET /sales/{id}` d'une vente de V2 | 200 (toutes) ; 200 | 200 (les siennes seulement) ; **404** | 403 | 403 |
| M14 | Modifier, annuler, retour | `PATCH /sales/{id}`, `POST /sales/{id}/cancel`, `POST /sales/{id}/returns` | 200/201 | 403 | 403 | 403 |
| M15 | Signaler une erreur | `POST /sales/{id}/error-reports` sur sa vente | 201 [Q-32] | 201 | 403 | 403 |
| M16 | Vendre sous le prix minimum | `POST /sales` à 719 999 (minimum 720 000, réglage actif) | 201 | **422** `PRICE_BELOW_MINIMUM` | 403 | 403 |
| M17 | Décider une demande de prix | `POST /price-requests` ; `POST /price-requests/{id}/decision` | 201 ; 200 | 201 ; 403 | 403 ; 403 | 403 ; 403 |
| M18 | Créer et voir les créances | `GET /receivables` ; `POST /receivables` (ancienne) | 200 (toutes) ; 201 | 200 (les siennes) ; 403 [Q-15] | 403 | 403 |
| M19 | Enregistrer un versement | `POST /receivables/{id}/installments` (créance de V ; créance de V2) | 201 ; 201 | 201 ; **404** | 403 | 403 |
| M20 | Annuler un versement, passer en perte | `POST /installments/{id}/cancel`, `POST /receivables/{id}/write-off` | 200 | 403 | 403 | 403 |
| M21 | Rappel, garant | `POST /receivables/{id}/reminders`, `/guarantors` (créance de V) | 201 | 201 (siennes) | 403 | 403 |
| M22 | Clients | `GET/POST/PATCH /customers`, `GET /customers/{id}/statement` | 200/201 | 200/201 (les siens ; client de V2 → 404) | 403 | 403 |
| M23 | Enregistrer une dépense | `GET/POST /expenses`, `PATCH /expenses/{id}`, `POST /expenses/{id}/cancel` | 200/201 | 403 | 200/201 (UC-DEP-04 : les siennes le jour même) [Q-11] | 403 |
| M24 | Catégories de dépense ; tags | `POST/PATCH /expense-categories` ; `GET /tags` ; `POST /tags/merge` | 201/200 ; 200 ; 200 | 403 ; 403 ; 403 | 403 ; 200 ; 403 | 403 |
| M25 | Tableau de bord complet | `GET /dashboard`, `GET /dashboard/details/{metric}` | 200 | 403 | 403 | 403 |
| M26 | Accueil de son rôle | `GET /home` | 200 | 200 (vendeur) | 200 (comptable) | 200 (vide au Lot 1) |
| M27 | Journal | `GET /audit`, `GET /audit/entities/{type}/{id}`, `GET /audit/users/{uid}` | 200 | 403 | 403 | 403 |
| M28 | Profil, alertes, soi-même | `GET /profile`, `GET /alerts`, `GET /me` | 200 | 200 | 200 | 200 |
| M29 | Console plateforme | `POST/GET/PATCH /platform/shops` | 403 | 403 | 403 | 403 (ADM : 200/201) |
| M30 | Synchronisation | `POST /sync`, `GET /offline-snapshot` | 403 `FEATURE_DISABLED` | idem | idem | idem |

Lignes § 4.2 hors Lot 1, **non testées** : déplacements, camions et chauffeurs, voyages, étapes et dépenses de voyage,
validation des dépenses de voyage, primes/avances/paie, import Excel. Pour chacune, un test vérifie seulement que la
route n'existe pas encore (404) afin qu'aucune route Lot 2 ne soit livrée sans droits.

Contrôles transverses : chaque 403 de la matrice crée **une** entrée « Accès refusé » (utilisateur, rôle, route) ; le
menu de chaque rôle (E2E) ne contient que les entrées de la colonne autorisée, au plus 5 (§ 17.4) [Q-29].

### 3.2 SEC-N — Non-fuite des données (RG-D02, RG-D03, RG-D05 ; critère A4)

Méthode : balayage récursif de **tout** le JSON reçu (y compris `error.details`, tableaux imbriqués, alertes) sur
chaque route accessible au rôle, avec le jeu SCN-01 enrichi d'**une valeur sentinelle** : coût unitaire de HJ =
**543 210**, prix de vente = **777 777**, prix de base = 780 000. On vérifie (1) l'absence des clés interdites
(expression régulière sur les noms de clés) et (2) l'absence de la valeur sentinelle dans le corps sérialisé.

| ID | Rôle | Clés interdites (motif) | Sentinelle absente | Routes balayées |
| --- | --- | --- | --- | --- |
| SEC-N01 | Vendeur | `cost`, `wac`, `margin`, `value`, `fee_share`, `unit_cost`, `stock_value`, `margin_rate` (toute clé qui les contient) | 543 210 | `POST/GET /sales`, `GET /sales/{id}`, `GET /sales/{id}/receipt`, `PATCH /sales/{id}/error-reports`, `GET /stock`, `GET /articles`, `GET /articles/{id}`, `GET /home`, `GET /alerts`, `GET /receivables`, `POST /receivables/{id}/installments`, `GET /customers/{id}/statement`, `GET /me`, `GET /profile`, réponses d'erreur `STOCK_INSUFFICIENT`, `PRICE_BELOW_MINIMUM` [Q-38], `CREDIT_LIMIT_EXCEEDED` |
| SEC-N02 | Comptable | `sale`, `sales`, `customer`, `receivable`, `revenue`, `cash_in`, `margin`, `installment`, `unit_price` de vente | 777 777 | `GET /home`, `GET /stock`, `GET /stock/value`, `GET /articles/{id}`, `GET /articles/{id}/movements` (le mouvement « Sortie vente » ne montre ni prix, ni total, ni client [Q-39]), `GET /alerts`, `GET /purchases`, `GET /expenses` |
| SEC-N03 | Chauffeur | `price`, `base_price`, `min_price`, `unit_price`, `amount`, `total`, `cost`, `wac`, `margin`, `value` | 780 000, 543 210, 777 777 | `GET /me`, `GET /profile`, `GET /home`, `GET /alerts` (toutes les autres routes → 403, SEC-M) |
| SEC-N04 | Propriétaire, sur le reçu | `cost`, `wac`, `margin` | 543 210 | `GET /sales/{id}/receipt` (UC-VEN-04 : jamais de coût sur un reçu) |
| SEC-N05 | Vendeur, interface | texte « 543 210 » et mots « Marge », « CMP », « Coût » absents du DOM | 543 210 | E2E sur Nouvelle vente, Mes ventes, Stock, Reçu, Accueil |
| SEC-N06 | Pièces d'identité | URL signée accordée à O et au vendeur responsable ; V2 → 404, C → 403 ; URL expirée après 60 s (`Clock` +61 s) → refus | — | `GET /attachments/{id}/url` |

Le présentateur est testé à part (HTTP) : pour la même vente, la réponse de O contient les 4 clés de coût (SCN-01 7a)
et celle de V aucune ; un test « garde-fou » échoue si une nouvelle route n'est pas déclarée dans la liste balayée
(comparaison avec l'OpenAPI).

### 3.3 SEC-I — Isolation entre deux boutiques (critère A5)

Jeu : boutiques A et B remplies chacune de SCN-01. L'utilisateur **U** est vendeur dans A et comptable dans B.

| ID | Requête | Attendu |
| --- | --- | --- |
| SEC-I01 | O (A seulement) : `GET /shops/B/sales` | 404 `NOT_FOUND` |
| SEC-I02 | O : `GET /shops/A/sales/{id d'une vente de B}` | 404 |
| SEC-I03 | O : `POST /shops/A/sales` avec `article_id` de B | 404, aucune écriture |
| SEC-I04 | O : vente dans A avec `customer.id`, `mode_id` ou `location_id` de B | 404 |
| SEC-I05 | O : `PATCH /shops/A/articles/{id de B}`, `POST /shops/A/sales/{id de B}/cancel`, `POST /shops/A/receivables/{id de B}/installments` | 404 ; l'objet de B est inchangé (`version` identique) |
| SEC-I06 | O : `GET /shops/A/dashboard` | ne compte que A (780 000, pas 1 560 000) |
| SEC-I07 | U dans A : `POST /sales` → 201 ; U dans B : `POST /sales` → 403 ; U dans B : `GET /stock/value` → 200 ; U dans A : `GET /stock/value` → 403 | rôle relu par boutique à chaque requête |
| SEC-I08 | Même téléphone client, même couple marque + modèle, même châssis dans A et B | acceptés tous les trois (unicité par boutique) |
| SEC-I09 | Première vente de A et première vente de B | `V-000001` dans les deux |
| SEC-I10 | Alertes et journal de A | aucune entrée de B ; la recherche par châssis dans A ne trouve pas une vente de B |
| SEC-I11 | ADM sans délégation : `GET /shops/A/sales` | 404 ; avec délégation active : 200 et accès journalisé ; délégation expirée → 404 [Q-40] |
| SEC-I12 | Contrat de dépôt : un dépôt construit pour A, à qui l'on passe l'`id` d'un objet de B | « introuvable » (mémoire et PostgreSQL) |
| SEC-I13 | Contrat : aucune méthode de dépôt n'accepte un `shop_id` en argument (inspection des signatures) | vrai pour tous les ports |
| SEC-I14 | Pièce jointe de B demandée par `GET /shops/A/attachments/{id}/url` | 404 |

### 3.4 SEC-L — Blocage après 5 codes faux (UC-SOC-02, TR-16)

`Clock` figée ; le compte de V est actif et son code est 482915.

| ID | Action | Attendu |
| --- | --- | --- |
| SEC-L01 | Essais faux 1 à 4 | `401 UNAUTHENTICATED`, message générique identique (« Numéro ou code incorrect ») ; journal de chaque échec [Q-23] |
| SEC-L02 | Essai faux 5 à t₅ | 401, et `locked_until = t₅ + 15 min` (ou 423 dès ce 5ᵉ essai [Q-28]) |
| SEC-L03 | Code juste à t₅ + 1 s | `423 ACCOUNT_LOCKED`, `details.until = t₅ + 15 min` |
| SEC-L04 | Code juste à t₅ + 14 min 59 s | 423 |
| SEC-L05 | Code juste à t₅ + 15 min | 200 ; `failed_attempts` remis à 0 |
| SEC-L06 | 4 faux, 1 juste, 4 faux | jamais bloqué (le compteur repart de 0 après une réussite) |
| SEC-L07 | O : `POST /members/{V}/unlock` pendant le blocage | 200 ; connexion de V possible aussitôt |
| SEC-L08 | Numéro inconnu | même code, même message que SEC-L01 (pas d'énumération des comptes) |
| SEC-L09 | Limitation de débit par IP et par numéro sur `/auth/*` | au-delà du seuil → 429 [Q-41 : seuil non chiffré] |

### 3.5 SEC-R — Déconnexion à distance (RG-D07)

| ID | Action | Attendu |
| --- | --- | --- |
| SEC-R01 | V connecté sur D1 (« Android — Chrome ») et D2 ; O : `POST /members/{V}/revoke-devices` | 200 ; les deux `DEVICE_SESSION` ont `revoked = true` ; journal « changement de droits » sensible |
| SEC-R02 | D1 : requête métier avec un jeton d'accès encore valide (< 15 min) | `401 SESSION_REVOKED` (le `sid` est vérifié à chaque requête) [Q-42] |
| SEC-R03 | D1 et D2 : `POST /auth/refresh` | `401 SESSION_REVOKED` |
| SEC-R04 | V se reconnecte sur D1 avec son code | 200 (la révocation n'est pas une désactivation) |
| SEC-R05 | Réutilisation d'un jeton de rafraîchissement déjà tourné | la session de cet appareil est révoquée ; l'autre appareil continue |
| SEC-R06 | V : `POST /members/{V2}/revoke-devices` | 403 |

### 3.6 SEC-X — Compte désactivé (RG-D06, RG-D08)

| ID | Action | Attendu |
| --- | --- | --- |
| SEC-X01 | O désactive V ; V se connecte avec le bon code | refus, message « Compte désactivé, contactez le propriétaire » ; code HTTP et code d'erreur [Q-31] |
| SEC-X02 | Session de V déjà ouverte : requête métier, puis `/auth/refresh` | refus aux deux (specs § 8.1) |
| SEC-X03 | Ventes et versements passés de V | toujours listés, avec le nom de V comme vendeur |
| SEC-X04 | O réactive V | connexion de nouveau possible |
| SEC-X05 | O seul propriétaire : se désactiver lui-même, ou passer son rôle à Comptable | refusés (RG-D08) ; avec un second propriétaire actif → acceptés |
| SEC-X06 | U vendeur dans A et comptable dans B ; OB désactive U | portée de la désactivation (compte entier ou rattachement à B) [Q-27] |

## 4. Cas limites et erreurs attendues par code

`Clock` 10/11 10:00 D sauf mention. Stock de départ : Garoua 2 HJ, Garoua-Boulaï 5 HJ, Ngaoundéré 0.

| ID | Entrée | HTTP | Code | `details` / effet attendu |
| --- | --- | --- | --- | --- |
| ERR-STK-01 | V : 3 HJ à Garoua | 422 | `STOCK_INSUFFICIENT` | `available: "2"`, `other_locations: [{Garoua-Boulaï, "5"}]` (Ngaoundéré à 0 : présent ou non [Q-43]) ; aucun mouvement, aucun numéro consommé |
| ERR-STK-02 | V : 2 lignes de HJ (2 + 1) dans la même vente | 422 | `STOCK_INSUFFICIENT` | contrôle sur la somme des lignes d'un même article |
| ERR-STK-03 | V : 2 HJ (= stock) | 201 | — | stock 0 ; pastille « Rupture » ; alerte de stock bas (LOW-01) |
| ERR-STK-04 | C : ajustement −3 à Garoua | 422 | `STOCK_INSUFFICIENT` | `available: "2"` |
| ERR-STK-05 | Deux ventes concurrentes de la dernière unité (stock 1) | 201 + 422 | `STOCK_INSUFFICIENT` | jamais deux 201 ; stock final 0 (CTR PostgreSQL, verrou optimiste + réessai) |
| ERR-PRM-01 | Réglage « prix minimum » actif, minimum 720 000 ; V vend à 719 999 | 422 | `PRICE_BELOW_MINIMUM` | `min_price: 720000`, `request_required: true` [Q-38] |
| ERR-PRM-02 | V vend à 720 000 | 201 | — | « en dessous » est strict |
| ERR-PRM-03 | O vend à 600 000 | 201 | — | journal sensible « vente sous le minimum » |
| ERR-PRM-04 | Réglage inactif ; V vend à 600 000 | 201 | — | le minimum est ignoré |
| ERR-PRM-05 | V : `POST /price-requests` (HJ, 700 000) ; O accepte ; V vend à 700 000 avec `price_request_id` | 201 | — | la demande est liée à la vente |
| ERR-PRM-06 | Demande refusée, puis vente avec ce `price_request_id` | 422 | `PRICE_BELOW_MINIMUM` | — |
| ERR-PRM-07 | Demande acceptée, `Clock` + 30 min, vente | 422 | `PRICE_BELOW_MINIMUM` ou `INVALID_STATE_TRANSITION` [Q-31] | statut « Expirée » (frontière exacte à 30:00 [Q-44]) ; durée de validité d'une demande acceptée [Q-44] |
| ERR-PRM-08 | Demande acceptée pour 700 000 utilisée à 690 000, ou pour un autre article, ou une seconde fois | 422 | `PRICE_BELOW_MINIMUM` | [Q-44] |
| ERR-PRM-09 | Demande en attente au-delà de 30 min (worker) | — | — | statut « Expirée », alerte retirée ou close |
| ERR-CRD-01 | Client plafond 1 000 000, déjà dû 400 000 ; V : crédit 780 000, acompte 100 000 (nouvelle dette 680 000 → 1 080 000) | 422 | `CREDIT_LIMIT_EXCEEDED` | `limit: 1000000`, `due_after: 1080000` |
| ERR-CRD-02 | Même vente, acompte 180 000 (dû après = 1 000 000) | 201 | — | égalité acceptée si « dépasser » est strict [Q-45] |
| ERR-CRD-03 | O : même vente qu'ERR-CRD-01 | 201 + avertissement | — | `warnings` contient `CREDIT_LIMIT_EXCEEDED` ; faut-il une confirmation explicite (`override`) [Q-45] |
| ERR-CRD-04 | Client sans plafond | 201 | — | aucun contrôle |
| ERR-OVR-01 | Versement 300 000 pour un reste de 280 000 | 422 | `OVERPAYMENT` | `remaining: 280000` (SCN-07) |
| ERR-OVR-02 | Comptant 780 000 payé 500 000 Espèces + 300 000 OM | 422 | `OVERPAYMENT` [Q-12] | RG-T20 |
| ERR-OVR-03 | Crédit 780 000 avec acompte 800 000 | 422 | `OVERPAYMENT` | — |
| ERR-OVR-04 | Versement sur une créance Soldée | 422 | `OVERPAYMENT` | reste 0 |
| ERR-OVR-05 | Paiements fournisseur dépassant le total de l'achat | 422 | `OVERPAYMENT` | — |
| ERR-DAT-01 | V : vente datée du 03/11 (J−7) | 201 | — | [Q-46 : 7 jours inclus ?] |
| ERR-DAT-02 | V : vente datée du 02/11 (J−8) | 422 | `DATE_OUT_OF_RANGE` | `details.min_date: 2026-11-03` |
| ERR-DAT-03 | V ou O : vente datée du 11/11 | 422 | `DATE_OUT_OF_RANGE` | date future |
| ERR-DAT-04 | O : vente datée du 01/01/2025 | 201 | — | le propriétaire remonte sans limite |
| ERR-DAT-05 | C : dépense ou achat daté du 02/11 | 422 | `DATE_OUT_OF_RANGE` | — |
| ERR-DAT-06 | Rappel de créance au 01/12/2026 | 201 | — | seule date future admise ; rappel dans le passé [Q-47] |
| ERR-DAT-07 | `Clock` 10/11 23:30Z (= 11/11 00:30 D) : vente datée du 11/11 | 201 | — | la journée est celle de Douala |
| ERR-DAT-08 | `Clock` 10/11 22:30Z (= 10/11 23:30 D) : vente datée du 11/11 | 422 | `DATE_OUT_OF_RANGE` | — |
| ERR-DAT-09 | `X-Captured-At` 11 min dans le futur | 422 | `DATE_OUT_OF_RANGE` | seuil de 10 min [Q8 des specs] ; à 9 min → accepté |
| ERR-DUP-01 | Châssis « LBX123 » déjà sur V-000001 valide ; nouvelle vente avec « LBX123 » | 409 | `DUPLICATE` | `details.sale_number: "V-000001"` |
| ERR-DUP-02 | Variantes « lbx123 », « LBX 123 », « LBX123 » + espace final | 409 ou 201 [Q-33] | `DUPLICATE` | normalisation à décider |
| ERR-DUP-03 | Même châssis sur deux unités de la même vente | 409 | `DUPLICATE` | — |
| ERR-DUP-04 | Client +237690000000 existe ; création avec « 690 00 00 00 » | 409 | `DUPLICATE` | normalisation du téléphone [Q-33] ; client d'un autre vendeur [Q-20] |
| ERR-DUP-05 | `POST /members` avec le téléphone d'un utilisateur existant | 201 rattachement ou 409 [Q-27] | — | — |
| ERR-DUP-06 | Article Haojue HJ125-8 en double ; fournisseur au même nom ; lieu au même nom | 409 | `DUPLICATE` | `details.existing_id` |
| ERR-VER-01 | Deux `PATCH /articles/{id}` avec la même `version` | 200 + 409 | `VERSION_CONFLICT` | le second ne modifie rien |
| ERR-VER-02 | O modifie une vente pendant que la créance liée reçoit un versement | l'un des deux 409 ou réessai transparent | `VERSION_CONFLICT` | état final cohérent (reste = total − payé) |
| ERR-VER-03 | 20 ventes concurrentes (critère A8, PostgreSQL) | 20 × 201 | — | numéros `V-000001` à `V-000020`, sans trou ni doublon ; aucun 409 renvoyé au client (3 réessais internes) |
| ERR-FEA-01 | `POST /sync` (droit inactif), chaque rôle, corps valide contenant une vente | 403 | `FEATURE_DISABLED` | aucune vente, aucun mouvement, aucun numéro consommé |
| ERR-FEA-02 | `POST /sync` corps vide ou invalide (droit inactif) | 403 | `FEATURE_DISABLED` | le droit est vérifié avant la validation du corps |
| ERR-FEA-03 | `GET /offline-snapshot` (droit inactif) | 403 | `FEATURE_DISABLED` [Q-48] | — |
| ERR-FEA-04 | Admin active `offline_capture` pour A (`PATCH /platform/shops/{A}`) ; sans redéploiement, `POST /sync` dans A | 200 | — | B reste en 403 `FEATURE_DISABLED` |
| ERR-MSC-01 | Transition interdite (annuler deux fois, perte d'une créance soldée, archiver avec stock) | 422 | `INVALID_STATE_TRANSITION` | — |
| ERR-MSC-02 | Champ inconnu, type faux, quantité `2.5` pour une moto, montant négatif | 400 | `VALIDATION_ERROR` | `details.fields` nomme chaque champ |
| ERR-MSC-03 | Requête sans jeton | 401 | `UNAUTHENTICATED` | — |
| ERR-MSC-04 | Toute exception imprévue | 500 | code stable, sans trace interne dans la réponse | journalisée côté serveur (fail-fast, aucune erreur avalée) |

### 4.1 Hors-ligne : ossature avec le droit activé (configuration de test, T23)

| ID | Cas | Attendu |
| --- | --- | --- |
| OFF-01 | Droit inactif : coupure pendant une vente | « Connexion nécessaire » ; file d'envoi Dexie vide (`count() = 0`) ; aucune requête `/sync` (E2E-05) |
| OFF-02 | Droit inactif : instantané hors ligne jamais téléchargé ; tableau de bord sans réseau sans aucun montant | E2E |
| OFF-03 | Droit inactif : seules les 4 saisies éligibles existent dans `SalesGateway`/`ExpensesGateway`, et elles lèvent `OfflineNotAllowed` | UI |
| OFF-04 | Droit actif : vente hors ligne → reçu provisoire `V-HL-3F2A-0001` imprimable ; au retour du réseau → `V-00000n` ; message « Vente V-HL-3F2A-0001 → V-00000n » ; recherche par le numéro provisoire | E2E |
| OFF-05 | Droit actif : même `op_id` envoyé deux fois → `duplicate`, une seule vente | HTTP |
| OFF-06 | Droit actif : vente différée qui rend le stock négatif → acceptée, `stock_to_verify = true`, alerte « Stock à vérifier » à O **et** C | APP |
| OFF-07 | Droit actif : 3 opérations dont la 2ᵉ refusée (vendeur sous le minimum) → 1ʳᵉ et 3ᵉ acceptées dans l'ordre ; 2ᵉ marquée refusée avec motif + alerte « Saisie refusée » ; compteur « 3 saisies en attente d'envoi » avant envoi | E2E, HTTP |
| OFF-08 | Droit actif : déconnexion avec saisies en attente bloquée ; double confirmation ; entrée `offline_ops_discarded` au journal à la reconnexion | E2E |
| OFF-09 | Droit actif : opération non autorisée (`purchase.create`) dans `/sync` → `rejected` | HTTP |
| OFF-10 | Droit actif : nouvelle version du service worker activée sans vider la file (migration Dexie) | E2E |

## 5. Parcours E2E (Playwright)

Configuration commune : Chromium, viewport **360 × 800**, `isMobile`, `hasTouch`, locale `fr-FR`, fuseau
`Africa/Douala`, base PostgreSQL réinitialisée par parcours, compte déjà connecté sauf mention. Profil « réseau
lent » : CDP `Network.emulateNetworkConditions` (latence 300 ms, 700 kbit/s descendant, 300 kbit/s montant) et
`Emulation.setCPUThrottlingRate(4)`. Un **geste** = une cible touchée ou un champ rempli (taper « hao » puis toucher la
suggestion compte pour un seul geste « article »).

| ID | Parcours | Étapes | Critère mesurable |
| --- | --- | --- | --- |
| E2E-01 | Vente comptant (A1) | V sur l'accueil → « Nouvelle vente » → (1) taper « hao », toucher « Haojue HJ125-8 » → (2) prix pré-rempli 780 000 conservé → (3) Espèces (déjà présélectionné après une première vente) → (4) « Valider la vente » | ≤ 4 gestes après l'ouverture de l'écran [Q-49] ; toast exact « Vente enregistrée — reçu n° V-000001 » ; durée automatisée ouverture → toast **< 10 s** en profil réseau lent (médiane de 5 essais), appui sur Valider → toast < 2 s ; champ prix `inputmode="numeric"` ; « Stock disponible à Garoua : 20 » affiché ; aucun coût dans le DOM (SEC-N05) ; **test terrain** : un vendeur réel < 30 s sur 5 essais sur un Android d'entrée de gamme |
| E2E-02 | Vente à crédit | Article, prix 780 000, « À crédit », client nouveau (nom, téléphone), acompte 300 000 Espèces | résumé affiché « Total : 780 000 — Versé : 300 000 — Reste à payer : 480 000 » ; sans client → message sous le champ, pas d'envoi ; après validation, reçu « Vente à crédit », reste 480 000 FCFA |
| E2E-03 | Versement | V : « Versement » → client « Moussa » → 200 000 → OM → Valider | avant validation « Reste à payer après ce versement : 280 000 FCFA » ; reçu `R-000001` ; saisie 300 000 → message d'erreur affiché sous le champ (`aria-live`), rien d'envoyé ou 422 traduit |
| E2E-04 | Accueil propriétaire | Données SCN-01 ; O se connecte | 1ᵉʳ écran : « Ventes du jour 780 000 FCFA », « 1 vente », « Argent encaissé du jour 300 000 FCFA », « Marge du jour 240 000 FCFA », lien « Voir aussi au CMP » ; un appui sur Ventes ouvre la liste (V-000001) ; barre du bas ≤ 5 entrées ; affichage < 2 s après connexion en profil lent (service worker déjà installé) |
| E2E-05 | Coupure réseau | V remplit une vente puis `context.setOffline(true)` → Valider ; puis tableau de bord de O hors réseau ; puis `setOffline(false)` | bannière « Connexion nécessaire » (icône + mot) ; formulaire conservé intégralement ; file Dexie vide ; aucune requête `/sync` ; tableau de bord : aucun montant affiché [Q-50] ; au retour du réseau, un seul appui renvoie la vente |
| E2E-06 | Prix sous le minimum | V saisit 700 000 (minimum 720 000) ; second contexte O accepte | le bouton devient « Demander l'accord du propriétaire » ; O voit l'alerte (article, prix demandé, minimum, vendeur) ; après acceptation, V valide |
| E2E-07 | Annulation par O | O ouvre V-000001 → « Annuler la vente » → motif → confirmer | ligne barrée, pastille « Annulée », mention « Annulé le 10/11/2026 par … — motif : … » ; stock revenu |
| E2E-08 | Première connexion et blocage | nouveau vendeur avec code provisoire → choix d'un code (123456 refusé) → accueil vendeur ; puis 5 codes faux | message « code trop simple » ; puis message de blocage avec l'heure de fin |
| E2E-09 | Changement de boutique | U ouvre la liste via le nom de boutique, passe de A à B | le menu passe de celui du vendeur à celui du comptable ; aucune donnée de A visible dans B |
| E2E-10 | Achat avec création d'article | C : « Nouvel achat » → article inconnu → « Créer l'article » → retour à l'achat → frais sous « Plus de détails » | coût unitaire final 540 000 affiché avant validation (cas SCN-01) |

### 5.1 Accessibilité (design-system § 8, bloquant)

| ID | Contrôle | Seuil |
| --- | --- | --- |
| A11Y-01 | `@axe-core/playwright` sur chaque écran visité par E2E-01 à E2E-10, plus `/_ui`, connexion, changement de code, dialogues ouverts | 0 violation `serious` ou `critical` |
| A11Y-02 | Taille de toucher : boîte de chaque élément interactif visible | ≥ 48 × 48 px et ≥ 8 px entre deux cibles |
| A11Y-03 | Taille du texte calculée de tout nœud texte | ≥ 16 px (hors mentions légales du reçu imprimé) ; unités `rem` |
| A11Y-04 | Focus clavier (bureau 1280 px) : Tab sur chaque écran | anneau de focus visible sur chaque arrêt, ordre logique |
| A11Y-05 | Chaque champ a un `<label>` relié ; erreurs annoncées en `aria-live="polite"` | 100 % des champs |
| A11Y-06 | Zoom 200 % (viewport 720 px de CSS ramené à 360) | aucun contenu tronqué ; pas de défilement horizontal de la page |
| A11Y-07 | Contraste vérifié par axe ; badges toujours mot + icône | ≥ 7:1 texte principal, ≥ 4,5:1 autre texte, ≥ 3:1 contours |

### 5.2 Budgets de performance (TR-20)

| ID | Mesure | Outil | Seuil |
| --- | --- | --- | --- |
| PERF-01 | Poids total de la première ouverture (HTML + JS + CSS + polices + icônes, compressés) | size-limit + Lighthouse `total-byte-weight` | **< 2 Mo visé** (avertissement CI au-delà) ; **3 Mo maximum** (échec CI) |
| PERF-02 | JS initial | size-limit | ≤ 250 Ko gzip |
| PERF-03 | Module PDF absent du bundle initial | analyse du bundle | chargé seulement au premier « Partager » |
| PERF-04 | Lighthouse CI, mobile, throttling « 3G » (RTT 300 ms, 700 kbit/s, CPU × 4), pages connexion, accueil propriétaire, nouvelle vente | Lighthouse CI | navigation suivante (service worker actif) : écran utilisable < 2 s ; 1ʳᵉ visite : mesurée et rapportée [Q-51] |
| PERF-05 | Recherche d'article : résultat après la 1ʳᵉ lettre | E2E chronométré | < 300 ms, sans appel réseau |
| PERF-06 | `GET /dashboard` sur 1 an de données (≈ 300 ventes/jour) | test de charge API | p95 < 300 ms (specs § 10) |

## 6. Questions et ambiguïtés à remonter à l'orchestrateur

Aucune n'est tranchée ici. Les cas qui en dépendent sont marqués « à confirmer ».

| # | Sujet | Constat | Cas concernés |
| --- | --- | --- | --- |
| Q-01 | Lieu de réception par défaut | Le profil Motos reçoit les achats à Garoua-Boulaï (entrepôt, non point de vente) ; sans déplacement (Lot 2), ce stock est invendable au Lot 1. Faut-il un autre défaut au Lot 1, ou accepter que l'achat soit reçu à Garoua ? Le parcours § 17.5 n'est pas reproductible tel quel | SCN-01, PUR-01 |
| Q-02 | Rejeu du CMP | specs § 5.3 « `replay_wac(mouvements d'entrée)` » contre CDC RG-T12 (stock réel au moment de l'achat). Avec une vente intercalée : 515 000 contre 510 000 | SCN-04 v3 |
| Q-03 | Arrondi | Règle d'arrondi du CMP et du coût unitaire final (506 923,08 ; 133 333,33) : au plus proche, demi vers le haut, troncature ? Et cohérence quantité × coût unitaire = total de l'achat | SCN-02, SCN-03 c |
| Q-04 | Dernier coût | Deux achats à la même date : lequel est « le plus récent » (heure de saisie, numéro) ? Achat antidaté : change-t-il le dernier coût ? | RG-T11 |
| Q-05 | Retour | Montant retiré des ventes du jour : remboursement ou valeur de la ligne ? Coût de ré-entrée en stock (CMP courant ou coût figé) ? Retour d'une vente à crédit : répartition entre baisse de créance et remboursement de l'acompte ? Ventes du jour négatives possibles ? | SCN-05 |
| Q-06 | Modification de vente | Baisse du prix sous le montant déjà payé ; changement de date (quel jour porte l'écart de marge et de ventes ?) | MOD-03 |
| Q-07 | Correction d'achat | « Au-dessous de ce qui a déjà été vendu » : contrôle sur le stock du lieu (le stock est par modèle, pas par lot) ou sur le lot ? Code d'erreur ? | PUR-06 |
| Q-08 | Délai de 7 jours | Correction d'achat par le comptable « pendant 7 jours après la date de l'achat » et RG-T09 « 7 jours au plus » : bornes incluses ? Code d'erreur au-delà (403 ou 422) ? | PUR-07, ERR-DAT-01 |
| Q-09 | Argent encaissé et annulations | Une vente annulée (ou un versement annulé) un autre jour que sa saisie : retire-t-on l'argent du jour d'origine (chiffres passés qui bougent, contraire à H5) ou du jour de l'annulation ? Les acomptes et versements « à rembourser » restent-ils dans l'encaissé tant que le remboursement n'est pas noté ? Une récupération sur perte compte-t-elle dans l'encaissé ? | SCN-06, SCN-07, SCN-08 |
| Q-10 | Affichage des taux | Arrondi du taux de marge et de la comparaison avec hier (28,6 % ou 29 %) ; affichage quand hier = 0 ; dénominateur du taux quand des ventes sont sans coût | SCN-01, SCN-09 |
| Q-11 | Dépenses | Matrice « Comptable : Tout » contre UC-DEP-04 « auteur le jour même » : un comptable peut-il modifier la dépense du propriétaire, ou la sienne le lendemain ? « Le jour de la saisie » = jour de saisie ou date de la dépense ? | EXP-06, M23 |
| Q-12 | Vente comptant | Paiements inférieurs au total : refus (quel code ?) ou vente comptant partiellement payée ? Le « montant remis » est-il envoyé au serveur ? | SAL-05, ERR-OVR-02 |
| Q-13 | Achats | Matrice « Comptable : Tout » sur les achats contre UC-ACH-04 (annulation : propriétaire seul) et UC-ACH-03 (7 jours) | M11, PUR-10 |
| Q-14 | Prix de base visible par le comptable | Le comptable crée l'article sans prix de vente : voit-il le prix de base et le minimum ? Que répondre s'il envoie un prix (403 ou champ ignoré) ? | CAT-03, M05 |
| Q-15 | Créances anciennes | Matrice « Créer les créances : Vendeur Siens » contre UC-CRE-02 (propriétaire seul) | REC-02, M18 |
| Q-16 | Coût d'un ajustement + | Quel coût unitaire porte un ajustement + ou un écart d'inventaire positif (CMP courant ? aucun ?) Sans achat préalable, la vente qui suit est-elle « sans coût connu » ? | ADJ-05, SCN-10 |
| Q-17 | Inventaire | Quantité théorique prise au lancement ou à la validation quand des ventes ont lieu pendant le comptage | INV-06 |
| Q-18 | Seuil de stock bas | « Passe sous le seuil » : strictement inférieur, ou inférieur ou égal ? Le stock total « tous lieux » inclut-il l'abîmé ? | LOW-01 |
| Q-19 | Ancienneté des créances | Classes « moins de 30 jours » puis « 31 à 60 » : où va une créance de 30 jours exactement ? | REC-05 |
| Q-20 | Clients et vendeur | Le vendeur ne voit que ses clients, mais le téléphone est unique dans la boutique : que voit un vendeur qui crée un client existant chez un autre vendeur (fuite d'existence ou réutilisation) ? Peut-il vendre à crédit à ce client ? | CUS-03, ERR-DUP-04 |
| Q-21 | Portée « Siens » des créances | Créances du vendeur = vendeur de la vente ou vendeur responsable (modifiable par le propriétaire) ? Aucune route de modification du responsable n'existe dans specs § 6.3 | REC-01, M18, M19 |
| Q-22 | Créance en perte | Après une récupération, quel « reste » afficher et quel plafond pour `OVERPAYMENT` ? Une récupération totale fait-elle passer la créance à « Soldée » ? | SCN-08 |
| Q-23 | Journal hors boutique | Le journal est par boutique (`shop_id`) ; où inscrire une connexion, un échec de connexion ou un « Accès refusé » d'un utilisateur rattaché à plusieurs boutiques, ou d'un non-membre (404) ? | AUD-04, SEC-L01 |
| Q-24 | « Versements reçus aujourd'hui » | Les acomptes des ventes à crédit en font-ils partie ? | SCN-09 |
| Q-25 | Impression | RG-T01 exige une entrée de journal à chaque impression et le reçu doit porter « Duplicata » à la réimpression, mais l'impression est faite par le navigateur et aucune route ne la reçoit. Comment compter les impressions ? | RCP-03, RG-T01 |
| Q-26 | Rôle Chauffeur au Lot 1 | Peut-on créer un compte Chauffeur au Lot 1 alors que la fiche chauffeur (module 13) n'existe pas ? Que voit-il ? | UC-SOC-04, SEC-N03 |
| Q-27 | Utilisateur multi-boutiques | Désactiver un compte (RG-D06) : le compte entier ou le rattachement à une boutique ? Un propriétaire de B peut-il désactiver un utilisateur aussi présent dans A ? À la réutilisation d'un téléphone existant (UC-SOC-01/04), le code existant est-il gardé ? | PLT-02, SEC-X06, ERR-DUP-05 |
| Q-28 | Comptage des essais | Le 5ᵉ code faux répond-il 401 ou déjà 423 ? Un code actuel faux lors du changement de code compte-t-il comme un essai ? | SEC-L02, PIN-02 |
| Q-29 | Menus au Lot 1 | Le menu du propriétaire contient « Camions », celui du comptable « Déplacements » (Lot 2) : masqués au Lot 1 ? remplacés par quoi ? | DSB-01, SEC-M |
| Q-30 | Lieux pour le vendeur | Matrice « Gérer les lieux : Vendeur — » mais le vendeur voit le stock par lieu (UC-STK-05) et son lieu de vente : `GET /locations` doit-il lui répondre ? | M03 |
| Q-31 | Codes d'erreur manquants | specs § 6.2 ne donne pas de code pour : compte désactivé, lieu ou article non désactivable car stock > 0, retour supérieur au vendu, dépense hors délai, demande de prix expirée | LOC-02, CAT-12, EXC-02, EXP-06, ERR-PRM-07, SEC-X01 |
| Q-32 | Signalement par le propriétaire | Le propriétaire (« Tout ») peut-il signaler une erreur, ce qui n'a pas de sens métier ? | M15 |
| Q-33 | Normalisation | Châssis, téléphone, marque + modèle : majuscules, espaces, indicatif +237 pris en compte pour l'unicité ? | CAT-02, ERR-DUP-02, ERR-DUP-04 |
| Q-34 | Prix | Prix minimum supérieur au prix de base : refusé ? Prix d'achat ou de vente à 0 : autorisé (cadeau) ? | CAT-10, PUR-04 |
| Q-35 | Prix unitaire d'achat à 0 | Voir Q-34 | PUR-04 |
| Q-36 | Lieu de vente du vendeur | Le vendeur peut-il vendre depuis un autre point de vente que son lieu habituel ? | SAL-03 |
| Q-37 | Idempotence | Même `id` rejoué avec un contenu différent : 200 avec l'ancienne ressource, ou 409 ? | SAL-06 |
| Q-38 | Prix minimum révélé | `PRICE_BELOW_MINIMUM` renvoie `min_price` au vendeur et l'instantané hors ligne contient le minimum : le vendeur a-t-il le droit de connaître ce plancher de négociation ? | ERR-PRM-01, SEC-N01 |
| Q-39 | Historique d'article pour le comptable | UC-STK-06 montre le « document lié (vente) » : le comptable voit-il le numéro de vente, et peut-il l'ouvrir (RG-D03) ? | SEC-N02 |
| Q-40 | Délégation admin | Durée par défaut (Q7 des specs) et route de création de la délégation absente de specs § 6.3 | SEC-I11 |
| Q-41 | Limitation de débit | Seuils de limitation par IP et par numéro non chiffrés | SEC-L09 |
| Q-42 | Révocation | Effet immédiat sur le jeton d'accès en cours (contrôle du `sid` à chaque requête) ou à expiration (≤ 15 min) ? | SEC-R02 |
| Q-43 | `other_locations` | Lieux à 0 inclus ou non ; entrepôts inclus alors qu'on ne peut pas y vendre ? | ERR-STK-01 |
| Q-44 | Demande de prix | Frontière exacte des 30 min ; durée de validité d'une demande **acceptée** ; usage unique ; prix exact ou « au moins » ce prix | ERR-PRM-07, ERR-PRM-08 |
| Q-45 | Plafond de crédit | « Dépasse » strict ? Comment le propriétaire « passe outre » : confirmation explicite ou simple avertissement ? | ERR-CRD-02, ERR-CRD-03 |
| Q-46 | Date de vente | `sold_on` est-il obligatoire dans le corps ou fixé par le serveur (journée de Douala) quand il manque ? Borne « 7 jours » incluse ? | SCN-09, ERR-DAT-01 |
| Q-47 | Rappel dans le passé | Une date de rappel passée est-elle acceptée ? | ERR-DAT-06 |
| Q-48 | Instantané hors ligne | `GET /offline-snapshot` doit-il aussi répondre `403 FEATURE_DISABLED` quand le droit est inactif (la recherche « dès la première lettre » s'appuie sur le catalogue local, specs § 10) ? | ERR-FEA-03, PERF-05 |
| Q-49 | Décompte des 4 gestes | L'appui sur « Nouvelle vente » depuis l'accueil compte-t-il ? Le choix du paiement compte-t-il s'il est présélectionné ? | E2E-01 |
| Q-50 | Message hors réseau du tableau de bord | « Chiffres disponibles avec internet » (UC-TDB-01) ou « Connexion nécessaire » (TR-26) ? | E2E-05 |
| Q-51 | « Un écran en moins de 2 s en 3G » | Incompatible avec une première visite de 2 Mo en 3G (≈ 23 s à 700 kbit/s) : l'exigence vise-t-elle seulement les écrans suivants (service worker actif) ? | PERF-04 |

## 7. Synthèse des cas

| Catégorie | Nombre de cas |
| --- | --- |
| Cas fonctionnels décrits dans la matrice (PLT, AUTH, MEM, LOC, SET, PIN, PWA, ALR, CAT, STK, INV, ADJ, LOW, VAL, PUR, SUP, SAL, RCP, RPT, MOD, EXC, CUS, REC, REM, GUA, EXP, DSB, AUD, MNY, ATT, CTR-STK) | 139 |
| Scénarios chiffrés (SCN-01 à SCN-10) | 10 scénarios, 76 lignes de vérification chiffrées |
| Sécurité : matrice des droits (SEC-M) | 30 lignes × 4 rôles = 120 cellules + 2 colonnes NM/ADM |
| Sécurité : non-fuite (SEC-N) | 6 |
| Sécurité : isolation (SEC-I) | 14 |
| Sécurité : blocage, révocation, désactivation (SEC-L, SEC-R, SEC-X) | 9 + 6 + 6 = 21 |
| Erreurs par code (ERR-*) | 49 |
| Hors-ligne (OFF-*) | 10 |
| E2E | 10 parcours |
| Accessibilité (A11Y) | 7 |
| Performance (PERF) | 6 |
| Questions ouvertes | 51 |
