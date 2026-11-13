# Plan d'exécution — Lot 2 (Mouvement) — BROUILLON, MIS EN ATTENTE

> **Statut : brouillon, mis en attente** (décision client du 2026-11-13 : le Lot 3 passe avant le Lot 2).
> Ce fichier garde les constats de l'analyse du code faite avant le changement de priorité ; le
> découpage en tâches sera repris (et renuméroté après celles du Lot 3) quand le Lot 2 redémarrera.

## Constats sur l'existant (2026-11-13)

| Sujet | Ce qui existe déjà | Ce qui manque pour le Lot 2 |
| --- | --- | --- |
| Grand livre | `MovementType` contient `transfer_out`, `transfer_in`, `transfer_missing`, `restore` ; `StockLedger.record_entry/record_exit/reverse` | aucune écriture de `stock_level.incoming` (seul `apply` vendable/abîmé) : méthode « en route » à ajouter au grand livre et à la projection |
| Stock abîmé | `GET /stock/damaged`, solde `damaged` de la projection | `POST /stock/damaged/{id}/restore` (« Remettre en vente ») et « Passer en perte » (ajustement −, motif Casse, état Abîmé) |
| Droits | `TRANSFER_*`, `FLEET_*`, `TRIP_*`, `PAYROLL_*` déjà dans `permissions.py` et `role_matrix.py` (comptable : `FLEET_NAMES_READ` en lecture, `TRANSFER_CANCEL` portée « Siens ») | aucune route ne les utilise |
| Alertes | types `transfer_to_receive`, `reception_gap`, `trip_expense_to_validate`, `breakdown`, `truck_silent`, `document_to_renew` déclarés avec leur module | type « déplacement sans voyage » (UC-TRF-01) et « déplacement en route depuis 7 jours » (UC-TRF-03) absents de `AlertType` |
| Hors-ligne | `trip_step.create`, `trip_expense.create` déclarés (`LOT_2_TYPES`, refus `AVAILABLE_IN_LOT_2`) | cas d'utilisation à brancher dans le `runner` |
| Accueils / tableau de bord | blocs `transfers_to_receive`, `transfers_in_transit`, `trucks`, `driver.*` valent `LOT_2` ou `null` | requêtes réelles |
| Menus Motos | entrées `trucks`, `payroll`, `transfers`, `my_trip`, `my_trip_expenses`, `my_trips` dans `domain/profiles/motos.py` | écrans ; retrait de `transfers`/`transport` de `UPCOMING_MODULES` à la fin de chaque module |
| Tâches planifiées | **aucun conteneur `worker`** n'existe (TR-19, `infra/README.md` le liste en reste à faire) ; les expirations (demandes de prix, rappels) sont faites à la lecture | camion sans étape (24 h), déplacement en route (7 j), documents à renouveler (J-30) exigent un planificateur |
| Migrations | tête `0017_upcoming_modules` | tables `transfer`, `transfer_line`, `city`, `truck`, `driver`, `trip`, `trip_step`, `third_party_load`, `trip_expense`, `bonus`, `salary_advance`, `payroll`, `payroll_adjustment`, `payroll_payment` |

## Pistes de découpage (à reprendre)

1. Transferts backend (domaine + grand livre « en route » + routes + abîmé) ; écrans Déplacements, Stock abîmé, bordereau.
2. Transport backend en 3 tranches : camions/chauffeurs/villes ; voyages, étapes, chargements, dépenses de voyage (+ hors-ligne) ; primes, avances, paie, bilan camion, flotte.
3. Worker planifié (nouveau conteneur) pour les alertes temporelles.
4. Écrans Camions, Paie, Mon voyage, Mes dépenses, Mes voyages ; accueils comptable et chauffeur.
5. Recette Lot 2 (tests unitaires et d'intégration seulement) et déploiement.

## Questions pressenties

- Rattachement d'un déplacement à un voyage quand le camion n'a pas de voyage en cours : le comptable ne voit pas les voyages (RG-D04) — rattachement par le propriétaire seulement ?
- Planificateur : nouveau conteneur `worker` ou tâches déclenchées à la lecture (comme les expirations du Lot 1) ?
- Libellé de l'écart de voyage et de son règlement : écriture de dépense automatique ou simple note ?
