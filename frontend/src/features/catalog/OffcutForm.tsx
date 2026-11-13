import { useState } from "react";
import { Check, RefreshCw, Scissors, X } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import { useStockGateway } from "../../core/gateways/httpStock";
import {
  Button,
  ChoiceChips,
  ConfirmDialog,
  EmptyState,
  Skeleton,
  TextField,
  useToast,
} from "../../shared/ui";
import { AttachmentUpload } from "../attachments/AttachmentUpload";
import { metersText } from "../sales/textile";
import { ErrorText } from "../stock/Notice";
import { failureText } from "../stock/stockErrors";
import { useStockSubmit } from "../stock/useStockSubmit";
import { loadFailureMessage } from "./catalogErrors";
import { InlineMessage } from "./InlineMessage";
import { checkOffcut, offcutPlaces, type OffcutDraft, type OffcutPlace } from "./offcutRules";
import { useLoad } from "./useLoad";

export interface OffcutFormProps {
  shopId: string;
  article: { id: string; name: string };
  onDone: () => void;
}

/** « Déclarer une chute » : stock du lieu lu d'abord (`GET /stock`), puis la saisie. */
export function OffcutForm({ shopId, article, onDone }: OffcutFormProps) {
  const gateway = useStockGateway();
  const [attempt, setAttempt] = useState(0);
  const [load] = useLoad(`${String(attempt)}|${article.id}`, () =>
    gateway.matrix(shopId, { text: article.name, locationId: null, sort: "name" }),
  );
  if (load.status === "loading") return <Skeleton lines={3} label="Lecture du stock…" />;
  if (load.status === "failed") return <InlineMessage text={loadFailureMessage(load.error)} />;
  if (load.status === "offline") {
    return (
      <EmptyState
        message="Connexion nécessaire pour déclarer une chute."
        action={
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={() => {
              setAttempt((n) => n + 1);
            }}
          >
            Réessayer
          </Button>
        }
      />
    );
  }
  const places = offcutPlaces(load.value, article.id);
  if (places.length === 0) {
    return (
      <EmptyState
        message="Aucun stock pour cet article : pas de chute à déclarer."
        action={
          <Button variant="secondary" icon={X} onClick={onDone}>
            Fermer
          </Button>
        }
      />
    );
  }
  return <OffcutEntry shopId={shopId} article={article} places={places} onDone={onDone} />;
}

function OffcutEntry({
  shopId,
  article,
  places,
  onDone,
}: OffcutFormProps & { places: readonly OffcutPlace[] }) {
  const gateway = useStockGateway();
  const toast = useToast();
  const [id] = useState(() => uuidV7()); // même identifiant à chaque renvoi (idempotence)
  const [placeId, setPlaceId] = useState(places[0]?.id ?? "");
  const [draft, setDraft] = useState<OffcutDraft>({ length: "", note: "", photoId: null });
  const [shown, setShown] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const place = places.find((one) => one.id === placeId);
  if (place === undefined) throw new Error(`Chute : lieu « ${placeId} » inconnu`);
  const submit = useStockSubmit(place.name);
  const check = checkOffcut(draft, place, article.id, id);
  const typed = draft.length.trim() !== "";

  const send = () => {
    setConfirming(false);
    const body = check.body;
    if (body === null || check.tenths === null) throw new Error("Chute : envoi sans contrôle");
    const length = metersText(check.tenths);
    void submit.run(
      () => gateway.adjust(shopId, body),
      () => {
        toast.show({ tone: "success", message: `Chute de ${length} enregistrée` });
        onDone();
      },
    );
  };
  return (
    <section aria-label="Déclarer une chute" className="flex flex-col gap-4">
      <h2 className="m-0 text-title-sm font-semibold text-text">Déclarer une chute</h2>
      <p className="m-0 text-body text-text-muted">
        La chute sort du stock (motif « Chute »), comme un ajustement : elle est notée au journal.
      </p>
      {places.length > 1 && (
        <ChoiceChips
          label="Lieu"
          options={places.map((one) => ({ value: one.id, label: one.name }))}
          value={placeId}
          onChange={setPlaceId}
        />
      )}
      <p className="m-0 text-body text-text-muted">
        Stock vendable à {place.name} : {metersText(place.tenths)}
      </p>
      <TextField
        label="Longueur de la chute"
        inputMode="decimal"
        autoComplete="off"
        suffix="m"
        hint="Au dixième de mètre, par exemple 0,4"
        value={draft.length}
        error={shown || typed ? check.error : undefined}
        onChange={(event) => {
          setDraft({ ...draft, length: event.target.value });
        }}
      />
      <TextField
        label="Note (facultative)"
        maxLength={500}
        value={draft.note}
        onChange={(event) => {
          setDraft({ ...draft, note: event.target.value });
        }}
      />
      <AttachmentUpload
        shopId={shopId}
        ownerType="stock_adjustment"
        ownerId={null}
        kind="photo"
        label="Photo de la chute (facultative)"
        onUploaded={(attachment) => {
          setDraft((current) => ({ ...current, photoId: attachment.id }));
        }}
      />
      {submit.failure !== null && <ErrorText text={failureText(submit.failure)} />}
      <Button
        size="lg"
        fullWidth
        icon={Scissors}
        loading={submit.pending}
        onClick={() => {
          setShown(true);
          if (check.body !== null) setConfirming(true);
        }}
      >
        Enregistrer la chute
      </Button>
      <Button variant="ghost" fullWidth icon={X} onClick={onDone}>
        Annuler
      </Button>
      <ConfirmDialog
        open={confirming}
        title={`Déclarer une chute de ${check.tenths === null ? "" : metersText(check.tenths)} ?`}
        confirmLabel="Déclarer la chute"
        confirmIcon={Check}
        onConfirm={send}
        onCancel={() => {
          setConfirming(false);
        }}
      >
        {`${article.name} : cette longueur sort du stock de ${place.name}.`}
      </ConfirmDialog>
    </section>
  );
}
