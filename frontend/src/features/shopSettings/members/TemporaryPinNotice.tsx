import { Check, KeyRound } from "lucide-react";
import { Button } from "../../../shared/ui";

export interface TemporaryPinNoticeProps {
  name: string;
  /** Code provisoire renvoyé une seule fois par le serveur (jamais mis en cache). */
  pin: string;
  onDone: () => void;
}

/**
 * Code provisoire d'un membre (MEM-01, MEM-04) : affiché **une seule fois**, à donner de vive
 * voix ; le membre devra le changer à sa première connexion.
 */
export function TemporaryPinNotice({ name, pin, onDone }: TemporaryPinNoticeProps) {
  return (
    <section
      aria-labelledby="temporary-pin"
      aria-live="polite"
      className="flex flex-col gap-3 rounded-lg bg-success-soft p-4 shadow-card"
    >
      <h2
        id="temporary-pin"
        className="m-0 flex items-center gap-2 text-title-sm font-semibold text-success-text"
      >
        <KeyRound aria-hidden="true" className="size-6 shrink-0" />
        Code provisoire de {name}
      </h2>
      <p className="m-0 font-mono text-amount font-bold tracking-widest text-text">{pin}</p>
      <p className="m-0 text-body text-text">
        Donnez ce code à {name} : il ne sera plus affiché. Il devra le changer à sa première
        connexion.
      </p>
      <Button variant="secondary" icon={Check} fullWidth onClick={onDone}>
        J'ai noté le code
      </Button>
    </section>
  );
}
