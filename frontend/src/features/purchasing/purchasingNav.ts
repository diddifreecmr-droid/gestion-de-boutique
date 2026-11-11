/**
 * Écrans de la section « Achats » : la vue est dans l'adresse (`?vue=…&id=…`), si bien que le
 * bouton retour du téléphone revient à l'écran précédent. Sans paramètre : la liste.
 *
 * | Écran | Adresse |
 * | --- | --- |
 * | Liste des achats | `/s/{id}/achats` |
 * | Nouvel achat | `?vue=nouvel` |
 * | Fiche / correction / paiement | `?vue=fiche&id=` · `?vue=corriger&id=` · `?vue=paiement&id=` |
 * | Fournisseurs | `?vue=fournisseurs`, fiche `?vue=fournisseur&id=`, |
 * | | création `?vue=fournisseur-nouveau`, modification `?vue=fournisseur-modifier&id=` |
 */
import type { Role } from "../../core/auth/me";
import type { Supplier } from "../../core/gateways/purchasingContract";
import type { References } from "./references";

/** Segment d'URL (entrée « Achats » du comptable et « Plus → Achats » du propriétaire). */
export const PURCHASES_KEY = "achats";

/** Rôles qui voient les achats (matrice `PURCHASE_READ` : propriétaire et comptable). */
export const PURCHASE_ROLES: readonly Role[] = ["owner", "accountant"];

export type PurchaseRole = "owner" | "accountant";

/** Rôle admis à la section ; tout autre rôle est une erreur de garde (fail-fast). */
export function purchaseRole(role: Role): PurchaseRole {
  if (role === "owner" || role === "accountant") return role;
  throw new Error(`Le rôle « ${role} » n'a pas accès aux achats (garde de route manquante)`);
}

export const VIEW = {
  create: "nouvel",
  detail: "fiche",
  edit: "corriger",
  payment: "paiement",
  suppliers: "fournisseurs",
  supplier: "fournisseur",
  newSupplier: "fournisseur-nouveau",
  editSupplier: "fournisseur-modifier",
} as const;

export interface PurchaseNav {
  list: () => void;
  create: () => void;
  open: (id: string) => void;
  edit: (id: string) => void;
  payment: (id: string) => void;
  suppliers: () => void;
  supplier: (id: string) => void;
  newSupplier: () => void;
  editSupplier: (id: string) => void;
}

/** Ce que reçoit chaque écran de la section. */
export interface ScreenProps {
  shopId: string;
  refs: References;
  nav: PurchaseNav;
  /** Fournisseur créé ou modifié : ajouté aux référentiels sans tout relire. */
  onSupplierSaved: (supplier: Supplier) => void;
}

/** Navigation par paramètres de recherche (`setParams` de react-router). */
export function purchaseNav(setParams: (params: Record<string, string>) => void): PurchaseNav {
  const go = (vue: string, id?: string) => {
    setParams(id === undefined ? { vue } : { vue, id });
  };
  return {
    list: () => {
      setParams({});
    },
    create: () => {
      go(VIEW.create);
    },
    open: (id) => {
      go(VIEW.detail, id);
    },
    edit: (id) => {
      go(VIEW.edit, id);
    },
    payment: (id) => {
      go(VIEW.payment, id);
    },
    suppliers: () => {
      go(VIEW.suppliers);
    },
    supplier: (id) => {
      go(VIEW.supplier, id);
    },
    newSupplier: () => {
      go(VIEW.newSupplier);
    },
    editSupplier: (id) => {
      go(VIEW.editSupplier, id);
    },
  };
}
