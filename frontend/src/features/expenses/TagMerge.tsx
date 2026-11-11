import { useState } from "react";
import { Merge } from "lucide-react";
import type { Tag } from "../../core/gateways/expensesContract";
import { useExpensesDeps } from "../../core/gateways/httpExpenses";
import { Button, ConfirmDialog } from "../../shared/ui";
import { expenseErrorMessage } from "./expenseErrors";
import { FormMessage } from "./FormMessage";
import { TagFilter } from "./TagFilter";
import { asError } from "./useLoad";

const MISSING = "Choisissez les deux tags à fusionner";
const SAME = "Choisissez deux tags différents";

/** Fusion de deux tags (UC-DEP-02, propriétaire), toujours confirmée. */
export function TagMerge({ shopId }: { shopId: string }) {
  const { gateway } = useExpensesDeps();
  const [source, setSource] = useState<Tag | null>(null);
  const [target, setTarget] = useState<Tag | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const unavailable =
    source === null || target === null ? MISSING : source.id === target.id ? SAME : undefined;

  const merge = async (from: Tag, into: Tag) => {
    setConfirming(false);
    setBusy(true);
    setMessage(null);
    try {
      const result = await gateway.mergeTags(shopId, from.id, into.id);
      const count = result.retagged_expenses;
      setDone(
        `« ${from.name} » fusionné dans « ${result.target.name} » : ${String(count)} dépense${count > 1 ? "s" : ""} mise${count > 1 ? "s" : ""} à jour.`,
      );
      setSource(null);
      setTarget(null);
    } catch (error) {
      try {
        setMessage(expenseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="expense-tag-merge" className="flex flex-col gap-4">
      <h2 id="expense-tag-merge" className="m-0 text-title-sm font-semibold text-text">
        Fusionner deux tags
      </h2>
      <TagFilter shopId={shopId} label="Tag à fusionner" value={source} onChange={setSource} />
      <TagFilter shopId={shopId} label="Fusionner dans" value={target} onChange={setTarget} />
      <p role="status" className="m-0 text-body text-success-text">
        {done}
      </p>
      {message !== null && <FormMessage text={message} />}
      <Button
        variant="secondary"
        icon={Merge}
        fullWidth
        loading={busy}
        onClick={() => {
          setDone(null);
          setConfirming(true);
        }}
        {...(unavailable === undefined ? {} : { disabledReason: unavailable })}
      >
        Fusionner
      </Button>
      {source !== null && target !== null && (
        <ConfirmDialog
          open={confirming}
          title={`Fusionner « ${source.name} » dans « ${target.name} » ?`}
          confirmLabel="Fusionner"
          confirmIcon={Merge}
          onConfirm={() => void merge(source, target)}
          onCancel={() => {
            setConfirming(false);
          }}
        >
          {`Les dépenses marquées « ${source.name} » passeront sous « ${target.name} ». Cette fusion ne se défait pas.`}
        </ConfirmDialog>
      )}
    </section>
  );
}
