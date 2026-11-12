import { useState } from "react";
import { Eye } from "lucide-react";
import { useAttachments } from "../../core/gateways/httpAttachments";
import { Button } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "../expenses/useLoad";
import { attachmentErrorMessage } from "./attachmentErrors";

export interface AttachmentViewProps {
  shopId: string;
  attachmentId: string;
  /** Nom de la pièce (« Pièce d'identité du garant »), aussi texte alternatif de l'image. */
  label: string;
  /** Ouverture d'un PDF (nouvel onglet) ; remplacée dans les tests. */
  openWindow?: (url: string) => void;
}

type Shown = { kind: "closed" } | { kind: "image"; url: string } | { kind: "failed"; text: string };

function defaultOpen(url: string): void {
  const opened = window.open(url, "_blank", "noopener");
  if (opened === null) window.location.assign(url); // fenêtre bloquée : même onglet
}

/**
 * « Voir la pièce » : demande un lien court (60 s, droits vérifiés par le serveur) au moment
 * de l'appui, jamais à l'avance. Photo → affichée ici ; PDF → ouvert à part.
 */
export function AttachmentView({ shopId, attachmentId, label, openWindow }: AttachmentViewProps) {
  const gateway = useAttachments();
  const [busy, setBusy] = useState(false);
  const [shown, setShown] = useState<Shown>({ kind: "closed" });
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const open = async () => {
    setBusy(true);
    try {
      const link = await gateway.link(shopId, attachmentId);
      if (link.mime === "application/pdf") {
        (openWindow ?? defaultOpen)(link.url);
        setShown({ kind: "closed" });
      } else {
        setShown({ kind: "image", url: link.url });
      }
    } catch (error) {
      try {
        setShown({ kind: "failed", text: attachmentErrorMessage(error) });
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      {shown.kind === "image" ? (
        <img
          src={shown.url}
          alt={label}
          className="max-h-80 w-full rounded-lg border border-border object-contain"
        />
      ) : (
        <Button variant="ghost" icon={Eye} loading={busy} onClick={() => void open()}>
          {`Voir : ${label}`}
        </Button>
      )}
      {shown.kind === "failed" && <FormMessage text={shown.text} />}
    </div>
  );
}
