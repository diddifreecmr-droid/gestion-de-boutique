import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import type { Supplier, SupplierPatch } from "../../core/gateways/purchasingContract";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { Button, useToast } from "../../shared/ui";
import type { ScreenProps } from "./purchasingNav";
import { SupplierForm, type SupplierFields } from "./SupplierForm";

const optional = (text: string) => (text.trim() === "" ? null : text.trim());

function fieldsOf(supplier: Supplier): SupplierFields {
  return {
    name: supplier.name,
    phone: supplier.phone ?? "",
    city: supplier.city ?? "",
    country: supplier.country ?? "",
    note: supplier.note ?? "",
  };
}

/** Nouveau fournisseur (UC-ACH-02) ; `id` client tiré une fois (renvoi sans doublon). */
export function SupplierNew({ shopId, nav, onSupplierSaved }: ScreenProps) {
  const { gateway } = usePurchasingDeps();
  const toast = useToast();
  const [id] = useState(uuidV7);
  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.suppliers}>
        Retour aux fournisseurs
      </Button>
      <SupplierForm
        title="Nouveau fournisseur"
        initial={{ name: "", phone: "", city: "", country: "", note: "" }}
        submitLabel="Créer le fournisseur"
        onSubmit={(fields) =>
          gateway.createSupplier(shopId, {
            id,
            name: fields.name.trim(),
            phone: optional(fields.phone),
            city: optional(fields.city),
            country: optional(fields.country),
            note: optional(fields.note),
          })
        }
        onSaved={(supplier) => {
          onSupplierSaved(supplier);
          toast.show({ tone: "success", message: `Fournisseur créé : ${supplier.name}` });
          nav.supplier(supplier.id);
        }}
      />
    </>
  );
}

/** Modification (UC-ACH-02) : `PATCH` des seuls champs changés avec la `version` lue. */
export function SupplierEdit({
  shopId,
  refs,
  nav,
  id,
  onSupplierSaved,
}: ScreenProps & { id: string }) {
  const { gateway } = usePurchasingDeps();
  const toast = useToast();
  const supplier = refs.suppliers.find((item) => item.id === id);
  if (supplier === undefined) throw new Error(`Fournisseur inconnu : « ${id} »`);
  const before = fieldsOf(supplier);
  return (
    <>
      <Button
        variant="ghost"
        icon={ArrowLeft}
        onClick={() => {
          nav.supplier(id);
        }}
      >
        Retour au fournisseur
      </Button>
      <SupplierForm
        title="Modifier le fournisseur"
        initial={before}
        submitLabel="Enregistrer"
        onSubmit={(fields) => {
          const patch: SupplierPatch = { version: supplier.version };
          if (fields.name.trim() !== before.name) patch.name = fields.name.trim();
          for (const key of ["phone", "city", "country", "note"] as const) {
            if (fields[key] !== before[key]) patch[key] = optional(fields[key]);
          }
          return gateway.updateSupplier(shopId, id, patch);
        }}
        onSaved={(saved) => {
          onSupplierSaved(saved);
          toast.show({ tone: "success", message: `Fournisseur modifié : ${saved.name}` });
          nav.supplier(id);
        }}
      />
    </>
  );
}
