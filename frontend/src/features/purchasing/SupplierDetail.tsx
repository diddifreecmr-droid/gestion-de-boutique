import { useState } from "react";
import { ArrowLeft, Pencil, RotateCcw, ShoppingBag, XCircle } from "lucide-react";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { formatDate } from "../../shared/format";
import {
  Badge,
  Button,
  ChoiceChips,
  ConfirmDialog,
  EmptyState,
  KpiCard,
  Skeleton,
} from "../../shared/ui";
import { businessDate } from "../expenses/businessDay";
import { FormMessage } from "../expenses/FormMessage";
import { asError, useLoad } from "../expenses/useLoad";
import { defaultFilters, PERIOD_LABELS, toQuery, type Period } from "./listFilters";
import { purchaseErrorMessage } from "./purchaseErrors";
import { PurchaseRow } from "./PurchaseRow";
import type { ScreenProps } from "./purchasingNav";

/** Périodes de la fiche (sans dates libres : la liste des achats les propose). */
const PERIODS = (["month", "week", "today"] as const).map((value) => ({
  value,
  label: PERIOD_LABELS[value],
}));

/** Fiche fournisseur (UC-ACH-02) : total acheté sur la période, ses achats, modifier, désactiver. */
export function SupplierDetail({
  shopId,
  refs,
  nav,
  id,
  onSupplierSaved,
}: ScreenProps & { id: string }) {
  const { gateway, now } = usePurchasingDeps();
  const today = businessDate(now());
  const [period, setPeriod] = useState<Exclude<Period, "custom">>("month");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const query = toQuery({ ...defaultFilters(today), period }, today);
  const sheet = useLoad(`${id}:${period}`, () =>
    gateway.supplierSheet(shopId, id, {
      ...(query.from === undefined ? {} : { from: query.from, to: query.to ?? today }),
    }),
  );
  const supplier = refs.suppliers.find((item) => item.id === id);
  if (supplier === undefined) throw new Error(`Fournisseur inconnu : « ${id} »`);

  const setActive = async (active: boolean) => {
    setConfirming(false);
    setBusy(true);
    setMessage(null);
    try {
      onSupplierSaved(
        await gateway.updateSupplier(shopId, id, { version: supplier.version, active }),
      );
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

  const ready = sheet.status === "ready" ? sheet.value : null;
  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.suppliers}>
        Retour aux fournisseurs
      </Button>
      <div className="flex flex-col items-start gap-2">
        <h1 className="m-0 break-words text-title font-bold text-text">{supplier.name}</h1>
        {!supplier.active && <Badge status="danger">Désactivé</Badge>}
        {[supplier.phone, supplier.city, supplier.country, supplier.note]
          .filter((part): part is string => part !== null && part !== "")
          .map((part) => (
            <p key={part} className="m-0 break-words text-body text-text-muted">
              {part}
            </p>
          ))}
      </div>
      <ChoiceChips label="Période" options={PERIODS} value={period} onChange={setPeriod} />
      {sheet.status === "loading" && <Skeleton lines={3} label="Chargement de la fiche…" />}
      {sheet.status === "offline" && (
        <EmptyState message="Connexion nécessaire pour afficher la fiche." />
      )}
      {ready !== null && (
        <>
          <KpiCard
            label={`Total acheté du ${formatDate(ready.first_day)} au ${formatDate(ready.last_day)}`}
            amount={ready.totals.total}
            detail={ready.totals.count === 1 ? "1 achat" : `${String(ready.totals.count)} achats`}
          />
          {ready.purchases.length === 0 ? (
            <EmptyState
              icon={ShoppingBag}
              message="Aucun achat chez ce fournisseur sur cette période."
            />
          ) : (
            <ul
              aria-label={`Achats chez ${supplier.name}`}
              className="m-0 list-none divide-y divide-border overflow-hidden rounded-lg bg-surface p-0 shadow-card"
            >
              {ready.purchases.map((purchase) => (
                <PurchaseRow key={purchase.id} refs={refs} purchase={purchase} />
              ))}
            </ul>
          )}
        </>
      )}
      {message !== null && <FormMessage text={message} />}
      <Button
        variant="secondary"
        icon={Pencil}
        fullWidth
        onClick={() => {
          nav.editSupplier(id);
        }}
      >
        Modifier le fournisseur
      </Button>
      {supplier.active ? (
        <Button
          variant="danger"
          icon={XCircle}
          fullWidth
          loading={busy}
          onClick={() => {
            setConfirming(true);
          }}
        >
          Désactiver le fournisseur
        </Button>
      ) : (
        <Button
          variant="secondary"
          icon={RotateCcw}
          fullWidth
          loading={busy}
          onClick={() => void setActive(true)}
        >
          Réactiver le fournisseur
        </Button>
      )}
      <ConfirmDialog
        open={confirming}
        title={`Désactiver ${supplier.name} ?`}
        confirmLabel="Désactiver"
        confirmIcon={XCircle}
        onConfirm={() => void setActive(false)}
        onCancel={() => {
          setConfirming(false);
        }}
      >
        Il ne sera plus proposé dans les nouveaux achats ; ses achats restent consultables.
      </ConfirmDialog>
    </>
  );
}
