import { useState } from "react";
import { CheckCheck, RefreshCw, Save, Trash2 } from "lucide-react";
import { useStockGateway } from "../../core/gateways/httpStock";
import type { Inventory } from "../../core/gateways/stockContract";
import { Button, ConfirmDialog, useToast } from "../../shared/ui";
import { CountList } from "./CountList";
import { initialDrafts, pendingCounts, uncounted, type Drafts } from "./inventoryDrafts";
import { ErrorText, WarningText } from "./Notice";
import { ReasonsStep } from "./ReasonsStep";
import { failureText } from "./stockErrors";
import { useStockSubmit } from "./useStockSubmit";

export interface InventoryCountingProps {
  shopId: string;
  inventory: Inventory;
  /** Nouvelle version renvoyée par le serveur (comptage enregistré, inventaire validé). */
  onSaved: (inventory: Inventory) => void;
  onReload: () => void;
  onAbandoned: () => void;
}

const REASONS_MISSING = "Donnez un motif pour chaque écart, ou un motif global.";

/** Comptage (UC-STK-07, étapes 1 à 4) : saisir, enregistrer pour reprendre, valider, abandonner. */
export function InventoryCounting(props: InventoryCountingProps) {
  const { shopId, inventory, onSaved, onReload, onAbandoned } = props;
  const gateway = useStockGateway();
  const toast = useToast();
  const submit = useStockSubmit();
  const [drafts, setDrafts] = useState<Drafts>(() => initialDrafts(inventory));
  const [errors, setErrors] = useState<Readonly<Record<string, string>>>({});
  const [gaps, setGaps] = useState<readonly string[] | null>(null);
  const [reasons, setReasons] = useState<Readonly<Record<string, string>>>({});
  const [globalReason, setGlobalReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const failure = submit.failure;
  if (failure?.kind === "reasons" && gaps !== failure.articleIds) setGaps(failure.articleIds);
  const left = uncounted(inventory, drafts);

  /** Envoie les lignes changées ; renvoie l'inventaire à jour (ou `null` si une saisie est fausse). */
  const counts = () => {
    const pending = pendingCounts(inventory, drafts);
    setErrors(pending.errors);
    if (Object.keys(pending.errors).length > 0) return null;
    return async (): Promise<Inventory> => {
      if (pending.entries.length === 0) return inventory;
      const saved = await gateway.saveCounts(shopId, inventory.id, {
        version: inventory.version,
        counts: pending.entries,
      });
      onSaved(saved);
      return saved;
    };
  };

  const save = () => {
    const send = counts();
    if (send === null) return;
    void submit.run(send, () => {
      toast.show({
        tone: "success",
        message: "Comptage enregistré — vous pouvez reprendre plus tard",
      });
    });
  };

  const validate = () => {
    const send = counts();
    if (send === null) return;
    const own = (gaps ?? [])
      .map((articleId) => ({ article_id: articleId, reason: (reasons[articleId] ?? "").trim() }))
      .filter((entry) => entry.reason !== "");
    const global = globalReason.trim();
    if (gaps !== null && global === "" && own.length < gaps.length) {
      setReasonError(REASONS_MISSING);
      return;
    }
    setReasonError(null);
    void submit.run(
      async () => {
        const current = await send();
        return gateway.validateInventory(shopId, inventory.id, {
          version: current.version,
          reasons: own,
          global_reason: global === "" ? null : global,
        });
      },
      (validated) => {
        toast.show({ tone: "success", message: `Inventaire ${validated.number} validé` });
        onSaved(validated);
      },
    );
  };

  const abandon = () => {
    setConfirming(false);
    void submit.run(
      () => gateway.abandonInventory(shopId, inventory.id, inventory.version),
      () => {
        toast.show({ tone: "success", message: `Inventaire ${inventory.number} abandonné` });
        onAbandoned();
      },
    );
  };

  return (
    <>
      {inventory.sales_message !== null && <WarningText text={inventory.sales_message} />}
      <p className="m-0 text-body text-text-muted">
        {`${String(inventory.lines.length - left)} sur ${String(inventory.lines.length)} articles comptés`}
      </p>
      <CountList
        inventory={inventory}
        drafts={drafts}
        errors={errors}
        onChange={(articleId, text) => {
          setDrafts((current) => ({ ...current, [articleId]: text }));
        }}
      />
      {gaps !== null && (
        <ReasonsStep
          inventory={inventory}
          articleIds={gaps}
          reasons={reasons}
          globalReason={globalReason}
          onReason={(articleId, text) => {
            setReasons((current) => ({ ...current, [articleId]: text }));
          }}
          onGlobalReason={setGlobalReason}
          error={reasonError}
        />
      )}
      {failure !== null && failure.kind !== "reasons" && <ErrorText text={failureText(failure)} />}
      {failure?.kind === "conflict" && (
        <Button variant="secondary" fullWidth icon={RefreshCw} onClick={onReload}>
          Recharger l'inventaire
        </Button>
      )}
      <Button variant="secondary" fullWidth icon={Save} loading={submit.pending} onClick={save}>
        Enregistrer le comptage
      </Button>
      <Button
        size="lg"
        fullWidth
        icon={CheckCheck}
        loading={submit.pending}
        onClick={validate}
        {...(left > 0 ? { disabledReason: `Il reste ${String(left)} article(s) à compter.` } : {})}
      >
        {gaps === null ? "Valider l'inventaire" : "Valider avec ces motifs"}
      </Button>
      <Button
        variant="danger"
        fullWidth
        icon={Trash2}
        onClick={() => {
          setConfirming(true);
        }}
      >
        Abandonner l'inventaire
      </Button>
      <ConfirmDialog
        open={confirming}
        title={`Abandonner l'inventaire ${inventory.number} ?`}
        confirmLabel="Abandonner"
        confirmIcon={Trash2}
        onConfirm={abandon}
        onCancel={() => {
          setConfirming(false);
        }}
      >
        Les quantités comptées seront perdues. Le stock ne change pas.
      </ConfirmDialog>
    </>
  );
}
