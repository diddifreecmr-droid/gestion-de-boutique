import { useId, useState } from "react";
import { BellPlus } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import type { Receivable } from "../../core/gateways/receivablesContract";
import { Button, TextField } from "../../shared/ui";
import { businessDate } from "../expenses/businessDay";
import { FormMessage } from "../expenses/FormMessage";
import { ReminderRow } from "./ReminderRow";
import { useAction } from "./useAction";

export interface RemindersSectionProps {
  shopId: string;
  receivable: Receivable;
  onChanged: (receivable: Receivable) => void;
}

/**
 * Rappels (UC-CRE-06) : date et note ; le jour venu, le vendeur responsable et le
 * propriétaire reçoivent une alerte interne — aucun message n'est envoyé au client (H19).
 */
export function RemindersSection({ shopId, receivable, onChanged }: RemindersSectionProps) {
  const { gateway, now } = useReceivablesDeps();
  const titleId = useId();
  const today = businessDate(now());
  const [date, setDate] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const [clientId, setClientId] = useState(uuidV7);
  const action = useAction();

  const schedule = async () => {
    if (date === "") {
      setError("Choisissez la date du rappel");
      return;
    }
    const body = { id: clientId, remind_on: date, note: note.trim() === "" ? null : note.trim() };
    const ok = await action.run(async () => {
      onChanged(await gateway.addReminder(shopId, receivable.id, body));
    });
    if (ok) {
      setDate("");
      setNote("");
      setClientId(uuidV7());
    }
  };

  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-2">
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Rappels
      </h2>
      {receivable.reminders.length === 0 ? (
        <p className="m-0 text-body text-text-muted">Aucun rappel programmé.</p>
      ) : (
        <ul className="m-0 list-none divide-y divide-border rounded-lg bg-surface p-0 shadow-card">
          {receivable.reminders.map((reminder) => (
            <ReminderRow
              key={reminder.id}
              reminder={reminder}
              today={today}
              busy={action.busy}
              onChange={(patch) =>
                action.run(async () => {
                  onChanged(await gateway.changeReminder(shopId, reminder.id, patch));
                })
              }
            />
          ))}
        </ul>
      )}
      <TextField
        label="Date du rappel"
        type="date"
        min={today}
        value={date}
        error={error}
        onChange={(event) => {
          setDate(event.target.value);
          setError(undefined);
        }}
      />
      <TextField
        label="Note (facultatif)"
        hint="Ex. « Il a promis 200 000 fin du mois »"
        maxLength={500}
        value={note}
        onChange={(event) => {
          setNote(event.target.value);
        }}
      />
      {action.message !== null && <FormMessage text={action.message} />}
      <Button
        variant="secondary"
        icon={BellPlus}
        loading={action.busy}
        onClick={() => void schedule()}
      >
        Programmer le rappel
      </Button>
    </section>
  );
}
