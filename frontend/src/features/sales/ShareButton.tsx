import { useState } from "react";
import { Share2 } from "lucide-react";
import { ApiError, NetworkError } from "../../core/api/errors";
import { Button } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "../expenses/useLoad";
import type { ShareableReceipt, ShareHost, ShareOutcome } from "./share/sharePdf";

export const SHARE_OFFLINE = "Connexion nécessaire pour préparer le PDF du reçu.";

export interface ShareButtonProps {
  /** Relit le DTO du reçu (le serveur compte l'émission, comme une impression). */
  load: () => Promise<ShareableReceipt>;
  /** Navigateur simulé (tests) ; par défaut, celui de l'appareil. */
  host?: ShareHost;
}

type State =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "done"; outcome: ShareOutcome }
  | { kind: "failed"; text: string };

function outcomeText(outcome: ShareOutcome): string | null {
  if (outcome.kind === "downloaded") {
    return `Partage indisponible sur cet appareil : le PDF « ${outcome.fileName} » a été téléchargé.`;
  }
  return outcome.kind === "shared" ? "Reçu partagé." : null;
}

/**
 * « Partager » (UC-VEN-04) : PDF produit sur l'appareil par un module chargé au premier appui
 * (D9, PERF-03), puis feuille de partage du téléphone, ou téléchargement si elle manque.
 */
export function ShareButton({ load, host }: ShareButtonProps) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const share = async () => {
    setState({ kind: "busy" });
    try {
      const [source, module] = await Promise.all([load(), import("./share/sharePdf")]);
      const outcome = await module.shareReceipt(source, host);
      setState({ kind: "done", outcome });
    } catch (error) {
      if (error instanceof NetworkError) setState({ kind: "failed", text: SHARE_OFFLINE });
      else if (error instanceof ApiError) {
        setState({ kind: "failed", text: `Reçu indisponible : ${error.message} (${error.code}).` });
      } else setFatal(error);
    }
  };

  const message = state.kind === "done" ? outcomeText(state.outcome) : null;
  return (
    <div className="flex flex-col gap-2">
      <Button
        variant="secondary"
        icon={Share2}
        fullWidth
        loading={state.kind === "busy"}
        onClick={() => void share()}
      >
        Partager
      </Button>
      {state.kind === "failed" && <FormMessage text={state.text} />}
      {message !== null && (
        <p role="status" className="m-0 text-body text-text">
          {message}
        </p>
      )}
    </div>
  );
}
