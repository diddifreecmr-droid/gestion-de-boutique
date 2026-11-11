import { useState } from "react";
import { CirclePlus, Pencil } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import type { Supplier } from "../../core/gateways/purchasingContract";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { Button, ListCard, ListCardRow, SearchField } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "../expenses/useLoad";
import { folded } from "./search";
import { purchaseErrorMessage } from "./purchaseErrors";

const SHOWN = 6;

export interface SupplierPickerProps {
  shopId: string;
  suppliers: readonly Supplier[];
  value: { id: string; name: string } | null;
  onChange: (supplier: { id: string; name: string } | null) => void;
  /** Fournisseur créé par la création rapide (ajouté aux référentiels). */
  onCreated: (supplier: Supplier) => void;
}

/**
 * Fournisseur facultatif (UC-ACH-01) : recherche dès la 1re lettre dans les fournisseurs
 * actifs, et création rapide par son seul nom sans quitter la saisie (UC-ACH-02 complète
 * ensuite téléphone, ville… depuis « Fournisseurs »).
 */
export function SupplierPicker({
  shopId,
  suppliers,
  value,
  onChange,
  onCreated,
}: SupplierPickerProps) {
  const { gateway } = usePurchasingDeps();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  if (value !== null) {
    return (
      <div className="flex flex-col gap-2">
        <span className="text-label font-semibold text-text">Fournisseur</span>
        <p className="m-0 break-words text-lead text-text">{value.name}</p>
        <Button
          variant="ghost"
          icon={Pencil}
          onClick={() => {
            onChange(null);
            setText("");
          }}
        >
          Changer de fournisseur
        </Button>
      </div>
    );
  }

  const typed = folded(text.trim());
  const found =
    typed === ""
      ? []
      : suppliers.filter((s) => s.active && folded(s.name).includes(typed)).slice(0, SHOWN);
  const exact = found.some((s) => folded(s.name) === typed);

  const create = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const created = await gateway.createSupplier(shopId, { id: uuidV7(), name: text.trim() });
      onCreated(created);
      onChange({ id: created.id, name: created.name });
    } catch (error) {
      try {
        setMessage(purchaseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <SearchField
        label="Fournisseur (facultatif)"
        hint="Tapez le nom du fournisseur"
        value={text}
        onChange={(next) => {
          setText(next);
          setMessage(null);
        }}
      />
      {found.length > 0 && (
        <ListCard label="Fournisseurs proposés">
          {found.map((supplier) => (
            <ListCardRow
              key={supplier.id}
              title={supplier.name}
              subtitle={supplier.city ?? undefined}
              onOpen={() => {
                onChange({ id: supplier.id, name: supplier.name });
              }}
            />
          ))}
        </ListCard>
      )}
      {typed !== "" && !exact && (
        <Button variant="secondary" icon={CirclePlus} loading={busy} onClick={() => void create()}>
          {`Nouveau fournisseur « ${text.trim()} »`}
        </Button>
      )}
      {message !== null && <FormMessage text={message} />}
    </div>
  );
}
