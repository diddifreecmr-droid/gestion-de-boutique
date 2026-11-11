import { ArrowLeft, CirclePlus, Users } from "lucide-react";
import { Badge, Button, EmptyState, ListCard, ListCardRow } from "../../shared/ui";
import type { ScreenProps } from "./purchasingNav";

/** Ville et pays, ou téléphone : la sous-ligne d'un fournisseur. */
function place(supplier: ScreenProps["refs"]["suppliers"][number]): string | undefined {
  const parts = [supplier.city, supplier.country, supplier.phone].filter(
    (part): part is string => part !== null && part !== "",
  );
  return parts.length === 0 ? undefined : parts.join(" · ");
}

/** Fournisseurs (UC-ACH-02) : actifs d'abord, désactivés ensuite (ils gardent leurs achats). */
export function SupplierList({ refs, nav }: ScreenProps) {
  const ordered = [...refs.suppliers].sort((a, b) => Number(b.active) - Number(a.active));
  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
        Retour aux achats
      </Button>
      <h1 className="m-0 text-title font-bold text-text">Fournisseurs</h1>
      <Button size="lg" fullWidth icon={CirclePlus} onClick={nav.newSupplier}>
        Nouveau fournisseur
      </Button>
      {ordered.length === 0 ? (
        <EmptyState icon={Users} message="Aucun fournisseur pour l'instant." />
      ) : (
        <ListCard label="Liste des fournisseurs">
          {ordered.map((supplier) => (
            <ListCardRow
              key={supplier.id}
              title={supplier.name}
              subtitle={place(supplier)}
              badge={supplier.active ? undefined : <Badge status="danger">Désactivé</Badge>}
              onOpen={() => {
                nav.supplier(supplier.id);
              }}
            />
          ))}
        </ListCard>
      )}
    </>
  );
}
