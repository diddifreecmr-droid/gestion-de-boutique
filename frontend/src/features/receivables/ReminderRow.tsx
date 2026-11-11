import { useState } from "react";
import { CalendarClock, Check } from "lucide-react";
import type { Reminder, ReminderPatch } from "../../core/gateways/receivablesContract";
import { formatDate } from "../../shared/format";
import { Badge, Button, TextField } from "../../shared/ui";
import { reminderStatus } from "./labels";

export interface ReminderRowProps {
  reminder: Reminder;
  today: string;
  busy: boolean;
  onChange: (patch: ReminderPatch) => Promise<boolean>;
}

/** Un rappel : date, note, statut ; « Marquer fait » ou « Reporter » tant qu'il n'est pas fait. */
export function ReminderRow({ reminder, today, busy, onChange }: ReminderRowProps) {
  const [postponing, setPostponing] = useState(false);
  const [date, setDate] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const { label, badge } = reminderStatus(reminder.status);
  const done = reminder.status === "done";
  const overdue = !done && reminder.remind_on < today;
  const postpone = async () => {
    if (date === "") {
      setError("Choisissez la nouvelle date");
      return;
    }
    if (await onChange({ status: "postponed", remind_on: date })) setPostponing(false);
  };
  return (
    <li className="flex flex-col gap-2 px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 flex-col">
          <span className="text-lead text-text">Le {formatDate(reminder.remind_on)}</span>
          {reminder.note !== null && (
            <span className="text-body break-words text-text-muted">{reminder.note}</span>
          )}
        </div>
        <Badge status={overdue ? "danger" : badge}>{overdue ? "Dépassé" : label}</Badge>
      </div>
      {!done && !postponing && (
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            icon={Check}
            loading={busy}
            onClick={() => void onChange({ status: "done" })}
          >
            Marquer fait
          </Button>
          <Button
            variant="ghost"
            icon={CalendarClock}
            onClick={() => {
              setPostponing(true);
            }}
          >
            Reporter
          </Button>
        </div>
      )}
      {postponing && (
        <>
          <TextField
            label="Nouvelle date du rappel"
            type="date"
            min={today}
            value={date}
            error={error}
            onChange={(event) => {
              setDate(event.target.value);
              setError(undefined);
            }}
          />
          <Button
            variant="secondary"
            icon={CalendarClock}
            loading={busy}
            onClick={() => void postpone()}
          >
            Reporter le rappel
          </Button>
        </>
      )}
    </li>
  );
}
