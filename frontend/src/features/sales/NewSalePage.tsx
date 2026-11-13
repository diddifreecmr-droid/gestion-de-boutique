import { useState } from "react";
import { RefreshCw, Store } from "lucide-react";
import type { Role } from "../../core/auth/me";
import type { SaleLocation, SaleSetup } from "../../core/gateways/catalogContract";
import { useGateways } from "../../core/gateways/gateways";
import type { SaleResult } from "../../core/gateways/salesContract";
import { Button, ChoiceChips, EmptyState, Skeleton } from "../../shared/ui";
import { lineFieldsOf } from "./lineFields";
import { NewSaleForm } from "./NewSaleForm";
import { articleSearchHint } from "./profileLabels";
import { ReceiptPrint } from "./ReceiptPrint";
import { locationChoice } from "./saleLocation";
import { SALE_ROLES } from "./saleRoles";
import { SaleConfirmation } from "./SaleConfirmation";
import { useLookup } from "./useLookup";

export interface NewSalePageProps {
  shopId: string;
  role: Role;
}

const Title = () => <h1 className="m-0 text-title font-bold text-text">Nouvelle vente</h1>;

/** Écran « Nouvelle vente » : préparation (lieu, modes), formulaire, confirmation, reçu. */
export function NewSalePage({ shopId, role }: NewSalePageProps) {
  if (!SALE_ROLES.includes(role)) {
    throw new Error(`Le rôle « ${role} » n'enregistre pas de vente (garde de route manquante)`);
  }
  const { catalog } = useGateways();
  const [attempt, setAttempt] = useState(0);
  const setup = useLookup(`${shopId}:${String(attempt)}`, () => catalog.saleSetup(shopId));

  if (setup.status !== "ready") {
    return (
      <>
        <Title />
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
  return <SaleFlow shopId={shopId} role={role} setup={setup.value} />;
}

function SaleFlow({ shopId, role, setup }: NewSalePageProps & { setup: SaleSetup }) {
  const { simulated } = useGateways();
  const choice = locationChoice(setup, role);
  const [chosen, setChosen] = useState<SaleLocation | null>(null);
  const [recorded, setRecorded] = useState<SaleResult | null>(null);
  const [printing, setPrinting] = useState(false);
  const [round, setRound] = useState(0);

  if (choice.status === "none") {
    return (
      <>
        <Title />
        <EmptyState icon={Store} message={choice.message} />
      </>
    );
  }
  if (recorded !== null && printing) {
    return (
      <ReceiptPrint
        shopId={shopId}
        saleId={recorded.id}
        onDone={() => {
          setPrinting(false);
        }}
      />
    );
  }
  if (recorded !== null) {
    return (
      <SaleConfirmation
        shopId={shopId}
        sale={recorded}
        onPrint={() => {
          setPrinting(true);
        }}
        onNewSale={() => {
          setRecorded(null);
          setRound((n) => n + 1);
        }}
      />
    );
  }
  const location = chosen ?? choice.initial;
  const notice = (
    <>
      {simulated && (
        <p className="m-0 text-body text-text-muted">
          Démonstration : les ventes sont simulées sur cet appareil, rien n'est envoyé au serveur.
        </p>
      )}
      {choice.choices.length > 1 && (
        <ChoiceChips
          label="Lieu de vente"
          options={choice.choices.map((place) => ({ value: place.id, label: place.name }))}
          value={location.id}
          onChange={(id) => {
            setChosen(choice.choices.find((place) => place.id === id) ?? null);
          }}
        />
      )}
    </>
  );
  return (
    <NewSaleForm
      key={`${location.id}:${String(round)}`}
      shopId={shopId}
      role={role}
      location={location}
      modes={setup.payment_modes}
      requiresApproval={setup.min_price_requires_approval}
      onRecorded={setRecorded}
      notice={notice}
      searchHint={articleSearchHint(setup.article_fields)}
      fields={lineFieldsOf(setup.sale_fields)}
      shortcuts={setup.sale_shortcuts}
    />
  );
}
