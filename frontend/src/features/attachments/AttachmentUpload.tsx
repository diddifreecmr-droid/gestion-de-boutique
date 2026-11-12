import { useState } from "react";
import { CheckCircle2, IdCard, RotateCcw } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import type {
  Attachment,
  AttachmentKind,
  OwnerType,
} from "../../core/gateways/attachmentsContract";
import { useAttachments } from "../../core/gateways/httpAttachments";
import { Button, FilePickerButton } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "../expenses/useLoad";
import { attachmentErrorMessage } from "./attachmentErrors";
import { canvasCodec, prepareFile, type ImageCodec, type PreparedFile } from "./prepareFile";

export interface AttachmentUploadProps {
  shopId: string;
  ownerType: OwnerType;
  ownerId: string | null;
  kind: AttachmentKind;
  /** Libellé du bouton (« Photo de la pièce d'identité »…). */
  label: string;
  /** Après l'envoi : rattacher la pièce à l'élément (client, garant, créance). */
  onUploaded: (attachment: Attachment) => Promise<void> | void;
  codec?: ImageCodec;
}

type Step = { kind: "idle" } | { kind: "busy" } | { kind: "done" } | { kind: "failed"; text: string };

/**
 * Prendre ou choisir une photo (ou un PDF), la réduire, l'envoyer (RG-T26, UC-CRE-07). En cas
 * d'échec (réseau, stockage), le fichier préparé et l'identifiant sont **gardés** : « Réessayer »
 * renvoie la même pièce (rejeu idempotent côté serveur).
 */
export function AttachmentUpload(props: AttachmentUploadProps) {
  const { shopId, ownerType, ownerId, kind, label, onUploaded, codec = canvasCodec } = props;
  const gateway = useAttachments();
  const [step, setStep] = useState<Step>({ kind: "idle" });
  const [pending, setPending] = useState<PreparedFile | null>(null);
  const [clientId, setClientId] = useState(uuidV7);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const fail = (error: unknown) => {
    try {
      setStep({ kind: "failed", text: attachmentErrorMessage(error) });
    } catch (unexpected) {
      setFatal(unexpected);
    }
  };

  const send = async (prepared: PreparedFile) => {
    setStep({ kind: "busy" });
    try {
      const request = { id: clientId, ownerType, ownerId, kind, file: prepared.blob };
      const attachment = await gateway.upload(shopId, { ...request, fileName: prepared.fileName });
      await onUploaded(attachment);
      setPending(null);
      setClientId(uuidV7());
      setStep({ kind: "done" });
    } catch (error) {
      fail(error);
    }
  };

  const chosen = async (file: File) => {
    try {
      const prepared = await prepareFile(file, codec);
      setPending(prepared);
      await send(prepared);
    } catch (error) {
      fail(error);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <FilePickerButton
        label={label}
        accept="image/*,application/pdf"
        icon={IdCard}
        loading={step.kind === "busy"}
        onFile={(file) => void chosen(file)}
      />
      {step.kind === "failed" && <FormMessage text={step.text} />}
      {step.kind === "failed" && pending !== null && (
        <Button variant="ghost" icon={RotateCcw} onClick={() => void send(pending)}>
          Réessayer l'envoi
        </Button>
      )}
      {step.kind === "done" && (
        <p role="status" className="m-0 flex items-center gap-1 text-body text-success-text">
          <CheckCircle2 aria-hidden="true" className="size-6 shrink-0" />
          Pièce enregistrée.
        </p>
      )}
    </div>
  );
}
