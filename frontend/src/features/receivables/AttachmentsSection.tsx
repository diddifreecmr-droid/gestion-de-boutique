import { useId, useState } from "react";
import type { AttachmentKind } from "../../core/gateways/attachmentsContract";
import { useAttachments } from "../../core/gateways/httpAttachments";
import type { Receivable } from "../../core/gateways/receivablesContract";
import { ChoiceChips } from "../../shared/ui";
import { AttachmentUpload } from "../attachments/AttachmentUpload";
import { AttachmentView } from "../attachments/AttachmentView";

export interface AttachmentsSectionProps {
  shopId: string;
  receivable: Receivable;
  onChanged: (receivable: Receivable) => void;
}

const KINDS: { value: AttachmentKind; label: string }[] = [
  { value: "id_document", label: "Pièce d'identité" },
  { value: "contract", label: "Contrat" },
  { value: "debt_acknowledgement", label: "Reconnaissance de dette" },
];

/**
 * Pièces jointes de la créance (UC-CRE-07, UC-VEN-02 étape 3) : CNI du client, contrat signé,
 * reconnaissance de dette. Chaque pièce s'ouvre par un lien court demandé à l'appui.
 */
export function AttachmentsSection({ shopId, receivable, onChanged }: AttachmentsSectionProps) {
  const gateway = useAttachments();
  const titleId = useId();
  const [kind, setKind] = useState<AttachmentKind>("id_document");
  const ids = receivable.attachment_ids;
  const label = KINDS.find((option) => option.value === kind)?.label ?? "Pièce";
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-2">
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Pièces jointes
      </h2>
      {ids.length === 0 ? (
        <p className="m-0 text-body text-text-muted">Aucune pièce jointe.</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {ids.map((attachmentId, index) => (
            <li key={attachmentId}>
              <AttachmentView
                shopId={shopId}
                attachmentId={attachmentId}
                label={`pièce jointe n° ${String(index + 1)}`}
              />
            </li>
          ))}
        </ul>
      )}
      <ChoiceChips
        label="Type de pièce"
        options={KINDS}
        value={kind}
        onChange={(value) => {
          setKind(value);
        }}
      />
      <AttachmentUpload
        key={`${kind}-${String(ids.length)}`}
        shopId={shopId}
        ownerType="receivable"
        ownerId={receivable.id}
        kind={kind}
        label={`Ajouter : ${label}`}
        onUploaded={async (attachment) => {
          onChanged(await gateway.linkToReceivable(shopId, receivable.id, attachment.id));
        }}
      />
    </section>
  );
}
