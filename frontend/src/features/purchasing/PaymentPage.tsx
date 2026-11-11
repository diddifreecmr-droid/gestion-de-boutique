import { useState } from "react";
import { ArrowLeft, Check } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import type { Purchase } from "../../core/gateways/purchasingContract";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { formatMoney } from "../../shared/format";
import { ActionBar, AmountField, Button, ChoiceChips, TextField, useToast } from "../../shared/ui";
import { businessDate, dateBounds, dateProblem } from "../expenses/businessDay";
import { FormMessage } from "../expenses/FormMessage";
import { LoadingOrOffline } from "../expenses/LoadingOrOffline";
import { asError, useLoad } from "../expenses/useLoad";
import { paymentOf, remainingOf } from "./correctionRule";
import { purchaseErrorMessage } from "./purchaseErrors";
import type { ScreenProps } from "./purchasingNav";

/** « Noter un paiement » (UC-ACH-06) : date, montant, mode, référence — simple repère. */
export function PaymentPage(props: ScreenProps & { id: string }) {
  const { gateway } = usePurchasingDeps();
  const loaded = useLoad(`${props.shopId}:${props.id}`, () => gateway.get(props.shopId, props.id));
  if (loaded.status !== "ready") {
    return <LoadingOrOffline title="Noter un paiement" status={loaded.status} />;
  }
  return <PaymentForm {...props} purchase={loaded.value} />;
}

function PaymentForm({
  shopId,
  refs,
  nav,
  id,
  purchase,
}: ScreenProps & { id: string; purchase: Purchase }) {
  const { gateway, now } = usePurchasingDeps();
  const toast = useToast();
  const today = businessDate(now());
  const modes = refs.modes.filter((mode) => mode.active);
  const [paymentId] = useState(uuidV7);
  const [date, setDate] = useState(today);
  const [amount, setAmount] = useState<number | null>(null);
  const [modeId, setModeId] = useState<string | null>(modes[0]?.id ?? null);
  const [reference, setReference] = useState("");
  const [checked, setChecked] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  if (modes.length === 0) throw new Error("Aucun mode de paiement actif");

  const allowed = paymentOf(purchase);
  const remaining = remainingOf(purchase);
  const mode = modes.find((item) => item.id === modeId);
  const bounds = dateBounds(today, refs.me.role === "owner");
  const errors = {
    date: dateProblem(date, today, refs.me.role === "owner"),
    amount: amount === null || amount <= 0 ? "Le montant est vide" : undefined,
    reference:
      mode?.reference_required === true && reference.trim() === ""
        ? "La référence est obligatoire pour ce mode"
        : undefined,
  };
  const back = () => {
    nav.open(id);
  };

  const submit = async () => {
    setChecked(true);
    const invalid = Object.values(errors).some((e) => e !== undefined);
    if (pending || invalid || modeId === null || amount === null) return;
    setPending(true);
    setMessage(null);
    try {
      const saved = await gateway.pay(shopId, id, {
        id: paymentId,
        amount,
        mode_id: modeId,
        paid_on: date === today ? null : date,
        reference: reference.trim() === "" ? null : reference.trim(),
      });
      toast.show({ tone: "success", message: `Paiement noté — ${saved.number}` });
      back();
    } catch (error) {
      try {
        setMessage(purchaseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setPending(false);
    }
  };

  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={back}>
        Retour à l'achat
      </Button>
      <h1 className="m-0 text-title font-bold text-text">Noter un paiement</h1>
      <p className="m-0 text-lead text-text">
        <span className="font-mono">{purchase.number}</span> — Reste à payer :{" "}
        <strong className="tabular-nums text-credit-text">{formatMoney(remaining)}</strong>
      </p>
      {!allowed.allowed ? (
        <p className="m-0 text-body text-text">{allowed.reason}</p>
      ) : (
        <>
          <AmountField
            label="Montant payé"
            value={amount}
            onChange={setAmount}
            error={checked ? errors.amount : undefined}
          />
          <ChoiceChips
            label="Mode de paiement"
            options={modes.map((m) => ({ value: m.id, label: m.name }))}
            value={modeId}
            onChange={setModeId}
          />
          <TextField
            label="Date du paiement"
            type="date"
            value={date}
            max={bounds.max}
            {...(bounds.min === undefined ? {} : { min: bounds.min })}
            error={checked ? errors.date : undefined}
            onChange={(event) => {
              setDate(event.target.value);
            }}
          />
          <TextField
            label={mode?.reference_required === true ? "Référence" : "Référence (facultatif)"}
            maxLength={64}
            autoComplete="off"
            value={reference}
            error={checked ? errors.reference : undefined}
            onChange={(event) => {
              setReference(event.target.value);
            }}
          />
          {message !== null && <FormMessage text={message} />}
          <div className="sticky bottom-16 z-20 -mx-4">
            <ActionBar fixed={false}>
              <Button
                size="lg"
                fullWidth
                icon={Check}
                loading={pending}
                onClick={() => void submit()}
              >
                Noter le paiement
              </Button>
            </ActionBar>
          </div>
        </>
      )}
    </>
  );
}
