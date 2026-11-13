---
title: "Gestion de boutiques — Micro-Design System"
status: approved
created: 2026-11-11
specs: specs.md
author: "@architect"
---

# Micro-Design System

> Ce document fixe l'identité visuelle et les composants atomiques. Le `@frontend` doit
> l'appliquer **strictement** : aucune couleur, taille ou espacement écrit en dur dans le code.
> Seuls les tokens ci-dessous sont autorisés, et une règle de lint le vérifie (§ 9).
> Source des contraintes : CDC § 1.3 (principes d'interface) et § 21 (lisibilité, poids), `specs.md` D18.

## 1. Principes

| # | Principe | Conséquence visuelle |
| --- | --- | --- |
| P1 | **Un écran = une tâche** | Un seul bouton principal par écran, placé en bas, en pleine largeur sur téléphone |
| P2 | **Gros boutons, gros chiffres** | Zone de toucher ≥ 48 px (56 px pour l'action principale) ; texte ≥ 16 px ; montants clés en 28 à 40 px |
| P3 | **Lisible en plein soleil** | Thème clair, contrastes AAA (≥ 7:1) pour le texte principal, aucun gris pâle sur du blanc |
| P4 | **Le minimum visible** | Les champs facultatifs sont repliés sous « Plus de détails » ; pas de décoration, d'image de fond ni d'animation |
| P5 | **Une icône a toujours un mot** | Pas de bouton fait d'une icône seule, sauf la cloche et le retour, qui gardent un libellé accessible |
| P6 | **Léger** | Polices du système (0 Ko téléchargé), icônes importées une par une, CSS issu des tokens seulement |
| P7 | **Le statut se lit sans la couleur** | Chaque statut a un mot et une icône en plus de sa couleur (daltonisme, écrans bas de gamme) |

**Thème** : clair uniquement en V1, pour la lisibilité en extérieur et la simplicité. Les tokens sont des variables CSS, donc un thème sombre pourra s'ajouter plus tard sans toucher aux composants.

## 2. Couleurs

### 2.1 Palette

Tous les contrastes ont été **calculés** selon la formule WCAG 2.1 :

| Token | Valeur | Rôle | Contraste vérifié |
| --- | --- | --- | --- |
| `--color-bg` | `#F6F7F9` | Fond de l'application | — |
| `--color-surface` | `#FFFFFF` | Cartes, champs, feuilles | — |
| `--color-text` | `#1A2230` | Texte principal, montants | 15,96 sur surface · 14,89 sur fond |
| `--color-text-muted` | `#4A5568` | Libellés secondaires, aides | 7,53 sur surface · 7,02 sur fond |
| `--color-border` | `#D5DAE1` | Séparateurs décoratifs | décoratif seulement |
| `--color-border-strong` | `#8A94A6` | Contour des champs et des contrôles | 3,06 (≥ 3, WCAG 1.4.11) |
| `--color-primary` | `#0B5D7A` | Action principale, liens, focus | blanc dessus : 7,34 |
| `--color-primary-hover` | `#084A62` | Appui sur une action principale | blanc dessus : 9,69 |
| `--color-primary-soft` | `#E3F1F6` | Sélection, fond d'un choix actif | texte primaire dessus : 6,35 |
| `--color-on-primary` | `#FFFFFF` | Texte sur la couleur primaire | — |
| `--color-success` | `#1E7A3C` | Confirmation (« Vente enregistrée ») | blanc dessus : 5,38 |
| `--color-success-text` / `-soft` | `#17602F` / `#E4F4E9` | Pastille « Soldée », « Reçu » | 6,70 |
| `--color-warning-text` / `-soft` | `#8A3B00` / `#FFF1DB` | Pastille « Stock bas », « À valider », « En route > 7 j » | 6,97 |
| `--color-warning-dot` | `#F59E0B` | Point orange de stock bas (CDC UC-STK-05) | texte foncé dessus : 7,43 |
| `--color-danger` | `#B42318` | Action destructrice (annuler, passer en perte) | blanc dessus : 6,57 |
| `--color-danger-text` / `-soft` | `#9A1C13` / `#FDE8E6` | Erreur, stock à zéro, « Annulée » | 7,01 |
| `--color-credit` | `#5B3FA6` | Marque « Crédit » (vente à crédit, créance) | blanc dessus : 7,76 |
| `--color-credit-text` / `-soft` | `#4C3391` / `#EFEAFB` | Pastille « Crédit », « Reste à payer » | 8,14 |

### 2.2 Usage

- **Le bleu pétrole (`primary`)** est réservé à l'action et à la navigation. On ne s'en sert pas pour décorer.
- **Le violet (`credit`)** désigne l'argent **qui reste dû**. Il ne sert à rien d'autre, ce qui le rend reconnaissable d'un coup d'œil : vente à crédit, reste à payer, créances.
- **Rouge et orange** suivent le CDC : point rouge pour un stock à zéro, point orange pour un stock sous le seuil, pastille orange pour un déplacement en retard ou un camion sans nouvelle.
- **Vert** = action réussie ou dossier réglé. Il ne sert jamais à embellir un montant.
- **Montants** : toujours en `--color-text`. Une marge négative passe en `--color-danger-text` **et** porte le signe « − ».

## 3. Typographie

### 3.1 Familles

```css
--font-sans: system-ui, Roboto, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
--font-mono: ui-monospace, "Roboto Mono", Consolas, monospace; /* numéros de document, châssis */
```

Aucune police n'est téléchargée : Roboto est native sur Android et Segoe UI sur Windows, ce qui fait **0 Ko** de poids ajouté. Les chiffres utilisent `font-variant-numeric: tabular-nums` pour rester alignés en colonne.

### 3.2 Échelle

Le CDC impose au moins 16 px partout à l'écran ; il n'y a donc **aucune taille inférieure à 16 px**.

| Token | Taille / interligne | Graisse | Usage |
| --- | --- | --- | --- |
| `--text-body` | 16 / 24 px | 400 | Texte courant, champs, listes |
| `--text-label` | 16 / 24 px | 600 | Libellés de champ, boutons |
| `--text-lead` | 18 / 28 px | 400 | Ligne principale d'un élément de liste |
| `--text-title-sm` | 20 / 28 px | 600 | Titre de carte, de section |
| `--text-title` | 24 / 32 px | 700 | Titre d'écran |
| `--text-amount` | 28 / 36 px | 700 | Total d'une vente, reste à payer |
| `--text-kpi` | 40 / 48 px | 700 | Chiffres du jour du propriétaire |

Sur un écran de 360 px, un montant `--text-kpi` comme « 12 500 000 FCFA » doit tenir sur une ligne : la partie « FCFA » est alors affichée en `--text-title-sm`, à la suite du nombre.

### 3.3 Formats (rappel CDC § 21)

| Donnée | Format | Exemple |
| --- | --- | --- |
| Montant | espace insécable fine entre milliers + `FCFA` | `1 250 000 FCFA` |
| Date | `JJ/MM/AAAA` | `10/11/2026` |
| Heure | `HH h MM` | `14 h 32` |
| Quantité textile | virgule décimale | `2,5 m` |
| Numéro de document | `--font-mono`, inchangé | `V-000124` |

Ces formats sont produits par `shared/format/` uniquement, jamais réécrits dans un écran.

## 4. Espacement, grille, formes

### 4.1 Grille de base 8 px

| Token | Valeur | Usage type |
| --- | --- | --- |
| `--space-1` | 4 px | demi-pas : écart entre une icône et son mot |
| `--space-2` | 8 px | écart serré à l'intérieur d'un composant |
| `--space-3` | 12 px | padding vertical d'une pastille ou d'une ligne compacte |
| `--space-4` | 16 px | **marge d'écran**, padding des cartes, écart entre champs |
| `--space-5` | 24 px | écart entre sections |
| `--space-6` | 32 px | séparation de grands blocs |
| `--space-7` | 48 px | dégagement en bas pour la barre d'action |

### 4.2 Mise en page

| Breakpoint | Largeur | Disposition |
| --- | --- | --- |
| Téléphone (base) | 360 à 599 px | 1 colonne, marges de 16 px, navigation en barre du bas, action principale fixée en bas |
| Tablette | ≥ 600 px | 1 colonne centrée, contenu de 600 px au plus |
| Ordinateur | ≥ 1024 px | navigation latérale (240 px) + contenu de 960 px au plus ; formulaires à 600 px au plus ; les tableaux (stock, journal) utilisent toute la largeur |

### 4.3 Formes et profondeur

| Token | Valeur | Usage |
| --- | --- | --- |
| `--radius-sm` | 6 px | pastilles |
| `--radius-md` | 10 px | boutons, champs |
| `--radius-lg` | 14 px | cartes, feuilles du bas |
| `--radius-full` | 9999 px | compteur de la cloche, points de statut |
| `--shadow-card` | `0 1px 2px rgb(26 34 48 / 0.08)` | cartes (une seule ombre, discrète) |
| `--shadow-sheet` | `0 -4px 16px rgb(26 34 48 / 0.12)` | barre d'action fixe, feuille du bas |
| `--focus-ring` | `0 0 0 3px var(--color-surface), 0 0 0 5px var(--color-primary)` | focus clavier, toujours visible |

### 4.4 Tailles de contrôle

| Token | Valeur | Usage |
| --- | --- | --- |
| `--control-md` | 48 px | hauteur minimale de tout ce qui se touche (CDC) |
| `--control-lg` | 56 px | action principale d'un écran, choix du mode de paiement |
| `--icon-md` | 24 px | icônes standard |
| `--icon-lg` | 32 px | icônes des grosses tuiles d'accueil |

### 4.5 Mouvement

`--duration-fast: 120ms`, `--easing: ease-out`. Ces valeurs servent seulement aux changements d'état (couleur au toucher, ouverture de « Plus de détails »). Aucune animation d'entrée, de chiffre ni de décor. Avec `prefers-reduced-motion: reduce`, la durée passe à 0.

## 5. Icônes

- **Lucide** (`lucide-react`), chaque icône importée une par une, ce qui garde un faible poids. Trait de 2 px, taille `--icon-md`.
- Une icône est toujours accompagnée d'un mot (P5). Couleur : `currentColor`.
- Jeu de référence : `ShoppingCart` vente · `Wallet` versement · `Package` stock · `Truck` camion · `ArrowLeftRight` déplacement · `Receipt` dépense · `ShoppingBag` achat · `Users` clients · `Bell` alertes · `WifiOff` hors connexion · `Printer` imprimer · `Share2` partager · `History` journal · `Settings` réglages.

## 6. Composants atomiques

Chaque composant vit dans `frontend/src/shared/ui/` (un fichier par composant, 200 lignes au plus) et ne consomme que des tokens.

### 6.1 Button

| Variante | Fond / texte | Bordure | Usage |
| --- | --- | --- | --- |
| `primary` | `primary` / `on-primary` | — | **une seule par écran** : Valider, Nouvelle vente |
| `secondary` | `surface` / `primary` | `border-strong` 1 px | Imprimer, Partager, Ajouter une ligne |
| `ghost` | transparent / `primary` | — | Plus de détails, Annuler la saisie |
| `danger` | `danger` / blanc | — | Annuler une vente, Passer en perte (toujours suivi d'une confirmation) |

- Tailles : `md` = 48 px, `lg` = 56 px (action principale). Padding horizontal `--space-4`, libellé en `--text-label`, icône à gauche et `--space-2` d'écart.
- Sur téléphone, l'action principale est en pleine largeur dans une **barre fixée en bas** (`surface` + `--shadow-sheet`, padding `--space-4`, avec la marge de sécurité basse de l'écran).
- États : appui → `primary-hover` ; désactivé → opacité 0,5 et une raison affichée sous le bouton (jamais un bouton grisé sans explication) ; chargement → libellé remplacé par « Envoi… », double appui bloqué.
- Variante métier : le bouton Valider devient « Demander l'accord du propriétaire » (UC-VEN-03), en `secondary`.

### 6.2 Field (Input, Amount, Select)

- **Libellé toujours au-dessus** (`--text-label`) ; jamais un placeholder qui sert de libellé.
- Champ : hauteur 48 px, fond `surface`, bordure 1 px `border-strong`, `--radius-md`, padding `--space-3` × `--space-4`.
- Focus : bordure 2 px `primary` + `--focus-ring`. Erreur : bordure 2 px `danger`, message en `danger-text` sous le champ, avec l'icône `AlertCircle` et un texte clair (« Le prix est vide »).
- **AmountField** : `inputmode="numeric"`, suffixe fixe « FCFA » en `text-muted`, séparateur de milliers inséré pendant la frappe, valeur en `--text-lead` gras.
- **QuantityStepper** : boutons − et + de 48 px de chaque côté de la valeur ; « Stock disponible : 4 » affiché dessous en `text-muted`.
- **ChoiceChips** (mode de paiement, type de dépense, taille) : boutons de 56 px de haut, 2 par ligne sur téléphone. Le choix actif est en `primary-soft` avec une bordure 2 px `primary` et une icône `Check`. Le dernier mode utilisé est présélectionné.
- **Switch** (interrupteur marche / arrêt, ex. modules d'une boutique dans la console) : toute la ligne est la cible, 56 px de haut, fond `surface`, bordure 1 px `border`, `--radius-md` ; libellé `--text-lead` gras à gauche, phrase d'aide facultative dessous en `text-muted` (dépendance, effet), puis le mot « Activé » / « Désactivé » et la piste (48 × 28 px, `--radius-full`) : `primary` activé, `border-strong` désactivé, pastille `surface`. Motif ARIA `switch` (`aria-checked`). Un réglage qui ne se change pas n'a pas d'interrupteur grisé : il est montré avec une pastille `success` « Toujours actif ».
- **Disclosure « Plus de détails »** : bouton `ghost` en pleine largeur avec un chevron ; une fois ouvert, les champs facultatifs apparaissent dans le même flux, sans fenêtre modale.
- **SearchField** : icône loupe, effaçable, résultats dès la première lettre ; les articles les plus vendus sont proposés quand le champ est vide.
- **FilePickerButton** (photo, pièce jointe) : un `Button` `secondary` (icône `IdCard` ou `Camera`) qui ouvre le sélecteur du téléphone (appareil photo, galerie, fichiers) ; le champ natif reste masqué mais porte le même nom accessible. Pendant l'envoi : état `loading` du bouton ; en cas d'échec : message `danger-text` et bouton `ghost` « Réessayer l'envoi » (le fichier est gardé) ; succès : « Pièce enregistrée. » en `success-text` avec `CheckCircle2`. Une pièce s'ouvre par un bouton `ghost` « Voir : … » (icône `Eye`) ; une photo s'affiche dans le flux, coins `--radius-lg`, bordure `border`.

### 6.3 Card

| Variante | Contenu | Style |
| --- | --- | --- |
| `KpiCard` | libellé (`text-muted`), montant (`--text-kpi`), comparaison avec hier (flèche + %, en mots : « +12 % par rapport à hier ») | `surface`, `--radius-lg`, padding `--space-4`, `--shadow-card` ; toute la carte s'ouvre d'un appui (UC-TDB-04) |
| `ListCard` | une ligne d'élément : titre `--text-lead`, sous-ligne `text-muted`, montant à droite, pastille de statut | hauteur ≥ 64 px, séparateur `border` entre les lignes |
| `ActionTile` | grosse tuile d'accueil par rôle : icône `--icon-lg` + mot | 2 par ligne, hauteur 96 px, `surface`, bordure `border` |
| `SummaryCard` | « Total : 800 000 — Versé : 200 000 — Reste à payer : 600 000 » | lignes alignées à droite, le reste à payer en `credit-text` + `--text-amount` |

### 6.4 Badge (pastille de statut)

Hauteur 28 px, `--radius-sm`, padding `--space-1` × `--space-2`, `--text-label`. Toujours **mot + icône**, la couleur ne suffit jamais seule (P7).

| Statut | Couleurs | Icône |
| --- | --- | --- |
| Crédit, En cours (créance) | `credit-soft` / `credit-text` | `Clock` |
| Soldée, Reçu, Validée, Livré | `success-soft` / `success-text` | `CheckCircle2` |
| Stock bas, À valider, En route (retard), Reçu en partie | `warning-soft` / `warning-text` | `AlertTriangle` |
| Annulée, Rejetée, En perte, Rupture | `danger-soft` / `danger-text` | `XCircle` |
| Hors connexion (provisoire) | `bg` / `text-muted`, bordure `border-strong` | `WifiOff` |

Un élément annulé (RG-T03) garde sa ligne : le texte passe en `text-muted` et barré, sauf la pastille « Annulée » et la mention « Annulé le … par … — motif : … ».

### 6.5 Messages

| Composant | Rôle | Style |
| --- | --- | --- |
| `Toast` | Retour après une action : « Vente enregistrée — reçu n° V-000124 » | en haut, `success`/blanc ou `danger`/blanc, 48 px minimum, reste 4 s ; les erreurs restent jusqu'à ce qu'on les ferme |
| `Banner` | État durable : « Connexion nécessaire », maintenance annoncée | pleine largeur sous la barre du haut, `warning-soft` / `warning-text`, icône `WifiOff` |
| `ConfirmDialog` | Annulation, passage en perte, déconnexion avec saisies en attente (double confirmation) | feuille du bas sur téléphone ; motif obligatoire dans un champ ; bouton `danger` à droite, « Retour » en `secondary` |
| `EmptyState` | Liste vide | une phrase + l'action utile (« Aucune vente aujourd'hui » + « Nouvelle vente ») |
| `Skeleton` | Chargement | blocs `border`, sans scintillement animé |

### 6.6 Navigation

- **Barre du haut** (56 px) : nom de la boutique, qui s'ouvre en liste quand il y en a plusieurs (UC-SOC-03) ; cloche avec compteur (pastille `danger`, `--radius-full`) ; flèche de retour sur les écrans de détail.
- **Accès « Mon compte »** (décision du 11/11/2026) : bouton icône `CircleUser` + mot « Compte » dans la barre du haut, à droite de la cloche, **pour tous les rôles**. Il ouvre « Mon compte » : version de l'application, « Recharger la dernière version », changer mon code, se déconnecter. Un bouton équivalent reste sur la page d'accueil. Il ne compte pas dans les 5 entrées de la barre du bas.
- **Barre du bas** (téléphone) : au plus 5 entrées (CDC § 17.4), icône + mot, 64 px de haut. Entrée active en `primary` avec un trait de 3 px au-dessus. Les droits manquants ne s'affichent pas du tout.
- **Navigation latérale** (ordinateur ≥ 1024 px) : mêmes entrées, plus le contenu de « Plus » déplié.

## 7. Écrans de référence

### 7.1 Nouvelle vente (téléphone, 360 px)

```
┌──────────────────────────────────┐
│ ←  Nouvelle vente        🔔 2    │  barre du haut 56 px
├──────────────────────────────────┤
│ Article                          │
│ ┌──────────────────────────────┐ │
│ │ 🔍 Haojue HJ125-8            │ │  48 px
│ └──────────────────────────────┘ │
│ Stock disponible à Garoua : 4    │  text-muted
│                                  │
│ Quantité        [ − ]  1  [ + ]  │
│                                  │
│ Prix                             │
│ ┌──────────────────────────────┐ │
│ │ 780 000                 FCFA │ │  AmountField
│ └──────────────────────────────┘ │
│                                  │
│ Paiement                         │
│ ┌─────────────┐ ┌─────────────┐  │
│ │✓ Espèces    │ │ Orange Money│  │  ChoiceChips 56 px
│ └─────────────┘ └─────────────┘  │
│ ┌─────────────┐ ┌─────────────┐  │
│ │ MTN MoMo    │ │ À crédit    │  │
│ └─────────────┘ └─────────────┘  │
│                                  │
│      ⌄ Plus de détails           │  ghost : couleur, châssis, client
├──────────────────────────────────┤
│ Total               780 000 FCFA │
│ ┌──────────────────────────────┐ │
│ │       ✓ Valider la vente     │ │  primary lg 56 px, barre fixe
│ └──────────────────────────────┘ │
└──────────────────────────────────┘
```

Les 4 gestes du CDC sont : choisir l'article, ajuster le prix, choisir le paiement, valider.

### 7.2 Accueil du propriétaire

```
┌──────────────────────────────────┐
│ Motos Garoua ▾           🔔 3    │
├──────────────────────────────────┤
│ Aujourd'hui ▾                    │
│ ┌──────────────────────────────┐ │
│ │ Ventes du jour               │ │
│ │ 2 340 000 FCFA               │ │  --text-kpi
│ │ 3 ventes · ↑ 12 % / hier     │ │
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ Argent encaissé du jour      │ │
│ │ 1 100 000 FCFA               │ │
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ Marge du jour                │ │
│ │ 610 000 FCFA                 │ │
│ │ Voir aussi au CMP ›          │ │
│ └──────────────────────────────┘ │
│ Créances · Stock · Camions …     │  ListCards
├──────────────────────────────────┤
│ Accueil Ventes Stock Camions Plus│  barre du bas 64 px
└──────────────────────────────────┘
```

## 8. Accessibilité (critères bloquants)

- Contraste : ≥ 7:1 pour le texte principal et ≥ 4,5:1 pour tout autre texte (vérifié au § 2.1) ; ≥ 3:1 pour les contours de contrôle.
- Taille de toucher : ≥ 48 × 48 px, avec au moins 8 px entre deux cibles.
- Le focus clavier est toujours visible (`--focus-ring`), car le propriétaire travaille aussi sur ordinateur.
- Chaque champ a un `<label>` relié ; les erreurs sont annoncées (`aria-live="polite"`).
- Zoom à 200 % sans perte de contenu ; aucune taille fixée en `px` sur le texte de base (utiliser `rem`, base 16 px).
- `axe-core` dans les tests E2E : aucune violation de niveau « serious » ou « critical ».

## 9. Implémentation (contrat pour `@frontend`)

### 9.1 Fichier de tokens — `frontend/src/shared/ui/tokens.css` (Tailwind v4)

```css
@import "tailwindcss";

@theme {
  --color-*: initial;               /* retire la palette Tailwind par défaut */
  --text-*: initial;                /* retire text-xs, text-sm… : 16 px minimum (§ 3.2) */
  --color-bg: #F6F7F9;
  --color-surface: #FFFFFF;
  --color-text: #1A2230;
  --color-text-muted: #4A5568;
  --color-border: #D5DAE1;
  --color-border-strong: #8A94A6;
  --color-primary: #0B5D7A;
  --color-primary-hover: #084A62;
  --color-primary-soft: #E3F1F6;
  --color-on-primary: #FFFFFF;
  --color-success: #1E7A3C;
  --color-success-text: #17602F;
  --color-success-soft: #E4F4E9;
  --color-warning-text: #8A3B00;
  --color-warning-soft: #FFF1DB;
  --color-warning-dot: #F59E0B;
  --color-danger: #B42318;
  --color-danger-text: #9A1C13;
  --color-danger-soft: #FDE8E6;
  --color-credit: #5B3FA6;
  --color-credit-text: #4C3391;
  --color-credit-soft: #EFEAFB;

  --font-sans: system-ui, Roboto, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, "Roboto Mono", Consolas, monospace;

  --text-body: 1rem;        --text-body--line-height: 1.5rem;
  --text-label: 1rem;       --text-label--line-height: 1.5rem;
  --text-lead: 1.125rem;    --text-lead--line-height: 1.75rem;
  --text-title-sm: 1.25rem; --text-title-sm--line-height: 1.75rem;
  --text-title: 1.5rem;     --text-title--line-height: 2rem;
  --text-amount: 1.75rem;   --text-amount--line-height: 2.25rem;
  --text-kpi: 2.5rem;       --text-kpi--line-height: 3rem;

  --spacing: 4px;           /* p-1 = 4 px, p-2 = 8 px, p-4 = 16 px, p-6 = 24 px… */

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;

  --shadow-card: 0 1px 2px rgb(26 34 48 / 0.08);
  --shadow-sheet: 0 -4px 16px rgb(26 34 48 / 0.12);
}

:root {
  --control-md: 3rem;
  --control-lg: 3.5rem;
  --duration-fast: 120ms;
}
@media (prefers-reduced-motion: reduce) {
  :root { --duration-fast: 0ms; }
}
```

**Équivalence espacements** : comme `--spacing` vaut 4 px, les classes Tailwind correspondent aux tokens de la grille : `space-1` → `1`, `space-2` → `2`, `space-3` → `3`, `space-4` → `4`, `space-5` → `6`, `space-6` → `8`, `space-7` → `12`. Les autres multiples ne sont pas utilisés.

### 9.2 Règles vérifiées en CI

1. **Pas de valeur en dur** : ESLint interdit les classes Tailwind à valeur arbitraire (`bg-[#…]`, `p-[13px]`, `text-[15px]`), ainsi que les `style={{ color… }}`. Les couleurs par défaut de Tailwind sont retirées (`--color-*: initial`), si bien qu'une classe comme `bg-blue-500` ne produit rien.
2. **Taille de texte** : aucune classe `text-xs` ni `text-sm` (retirées par `--text-*: initial`) ; le minimum est `text-body`.
3. **Composants** : les écrans assemblent des composants de `shared/ui/` ; un `<button>` ou un `<input>` brut dans `features/` est refusé par le lint.
4. **Poids** : `size-limit` fait échouer la CI au-delà de 3 Mo pour la première ouverture (objectif < 2 Mo).
5. **Vitrine** : une page `/_ui` (développement uniquement, exclue du build de production) affiche chaque composant et chacun de ses états ; elle sert de référence visuelle pour la QA.

## 10. Impression des reçus

L'impression suit sa propre petite échelle, indépendante de l'écran. Elle est pilotée par le profil d'impression de la boutique (`specs.md` § 9.1).

| Élément | 58 mm (`thermal-58`) | 80 mm (`thermal-80`) | A5 / A4 |
| --- | --- | --- | --- |
| Largeur imprimable | 48 mm | 72 mm | page standard, marges de 12 mm |
| Texte courant | 10 pt | 11 pt | 11 pt |
| Nom de la boutique | 13 pt, gras | 15 pt, gras | 18 pt, gras |
| Total | 14 pt, gras | 16 pt, gras | 16 pt, gras |
| Couleur | noir pur, aucun gris (les thermiques impriment mal le gris) | idem | noir |
| Logo | facultatif, monochrome, largeur ≤ 60 % | idem | ≤ 40 mm |

Séparateurs en tirets ; mentions « Vente à crédit », « Duplicata », « Annulé » en capitales et encadrées. Le reçu n'affiche jamais un coût ni une marge (UC-VEN-04).
