import { ExternalLink, RefreshCw } from "lucide-react";
import { Button } from "../../shared/ui";
import { VERSION_CONFLICT_MESSAGE, type SubmitFailure } from "./catalogErrors";
import { InlineMessage } from "./InlineMessage";

export interface SubmitFailureNoticeProps {
  failure: SubmitFailure;
  /** Ouvre l'article existant (doublon, UC-STK-01 : on le propose au lieu d'en créer un). */
  onOpenExisting: (articleId: string) => void;
  /** Relit l'article (conflit de version, ERR-VER-01). */
  onReload: () => void;
}

/** Refus d'un envoi : doublon avec lien, conflit de version avec rechargement, ou message. */
export function SubmitFailureNotice({
  failure,
  onOpenExisting,
  onReload,
}: SubmitFailureNoticeProps) {
  switch (failure.kind) {
    case "duplicate":
      return (
        <div className="flex flex-col gap-2">
          <InlineMessage text={`Cet article existe déjà : ${failure.existingName}`} />
          <Button
            variant="secondary"
            fullWidth
            icon={ExternalLink}
            onClick={() => {
              onOpenExisting(failure.existingId);
            }}
          >
            {`Ouvrir « ${failure.existingName} »`}
          </Button>
        </div>
      );
    case "conflict":
      return (
        <div className="flex flex-col gap-2">
          <InlineMessage text={VERSION_CONFLICT_MESSAGE} />
          <Button variant="secondary" fullWidth icon={RefreshCw} onClick={onReload}>
            Recharger l'article
          </Button>
        </div>
      );
    case "message":
      return <InlineMessage text={failure.text} />;
  }
}
