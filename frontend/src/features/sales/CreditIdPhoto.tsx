import { useId } from "react";
import { useAttachments } from "../../core/gateways/httpAttachments";
import { AttachmentUpload } from "../attachments/AttachmentUpload";

export interface CreditIdPhotoProps {
  shopId: string;
  customerId: string;
}

/**
 * Vente à crédit (UC-VEN-02 étape 3, CDC § 20.4 « Client ») : photo de la pièce d'identité du
 * client, prise juste après la validation. Elle est rattachée à la **fiche du client**
 * (`id_doc_photo_id`), visible du propriétaire et du vendeur responsable seulement.
 */
export function CreditIdPhoto({ shopId, customerId }: CreditIdPhotoProps) {
  const gateway = useAttachments();
  const titleId = useId();
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-2">
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Pièce d'identité du client
      </h2>
      <p className="m-0 text-body text-text-muted">
        Facultatif. Photo réduite avant l'envoi ; visible du propriétaire et du vendeur responsable.
      </p>
      <AttachmentUpload
        shopId={shopId}
        ownerType="customer"
        ownerId={customerId}
        kind="id_document"
        label="Photo de la pièce d'identité"
        onUploaded={(attachment) => gateway.linkToCustomer(shopId, customerId, attachment.id)}
      />
    </section>
  );
}
