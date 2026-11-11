import { useState } from "react";
import { RefreshCw } from "lucide-react";
import type { Role } from "../../core/auth/me";
import { useGateways } from "../../core/gateways/gateways";
import type { SaleResult } from "../../core/gateways/salesContract";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import { NewSaleForm } from "./NewSaleForm";
import { SALE_ROLES } from "./saleRoles";
import { SaleConfirmation } from "./SaleConfirmation";
import { useLookup } from "./useLookup";

export interface NewSalePageProps {
  shopId: string;
  role: Role;
}

/** Écran « Nouvelle vente » : préparation (lieu, modes), formulaire, puis confirmation. */
export function NewSalePage({ shopId, role }: NewSalePageProps) {
  if (!SALE_ROLES.includes(role)) {
    throw new Error(`Le rôle « ${role} » n'enregistre pas de vente (garde de route manquante)`);
  }
  const { catalog, simulated } = useGateways();
  const [attempt, setAttempt] = useState(0);
  const [recorded, setRecorded] = useState<SaleResult | null>(null);
  const [round, setRound] = useState(0);
  const setup = useLookup(`${shopId}:${String(attempt)}`, () => catalog.saleSetup(shopId));

  const notice = simulated && (
    <p className="m-0 text-body text-text-muted">
      Démonstration : les ventes sont simulées sur cet appareil, rien n'est envoyé au serveur.
    </p>
  );

  if (recorded !== null) {
    return (
      <SaleConfirmation
        sale={recorded}
        onNewSale={() => {
          setRecorded(null);
          setRound((n) => n + 1);
        }}
      />
    );
  }
  if (setup.status !== "ready") {
    return (
      <>
        <h1 className="m-0 text-title font-bold text-text">Nouvelle vente</h1>
        {setup.status === "loading" ? (
          <Skeleton lines={4} label="Préparation de la vente…" />
        ) : (
          <EmptyState
            message="Connexion nécessaire pour ouvrir une vente."
            action={
              <Button
                variant="secondary"
                icon={RefreshCw}
                onClick={() => {
                  setAttempt((n) => n + 1);
                }}
              >
                Réessayer
              </Button>
            }
          />
        )}
      </>
    );
  }
  return (
    <NewSaleForm
      key={round}
      shopId={shopId}
      role={role}
      setup={setup.value}
      onRecorded={setRecorded}
      notice={notice}
    />
  );
}
