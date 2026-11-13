import { useState } from "react";
import { RefreshCw } from "lucide-react";
import type { ImportBatch } from "../../core/gateways/importsContract";
import { useImports } from "../../core/gateways/httpImports";
import { formatDate } from "../../shared/format";
import {
  Badge,
  Banner,
  Button,
  EmptyState,
  ListCard,
  ListCardRow,
  Skeleton,
} from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { rowsText, stillCancellable, untilText } from "./batchText";
import { modelOf } from "./importModels";

export const HISTORY_LABEL = "Imports passés";
export const NO_BATCH = "Aucun import pour l'instant.";

/** Pastille du lot (design-system § 7.7) : « Importé » ou « Annulé ». */
export function BatchBadge({ batch }: { batch: ImportBatch }) {
  return batch.status === "imported" ? (
    <Badge status="success">Importé</Badge>
  ) : (
    <Badge status="danger">Annulé</Badge>
  );
}

function subtitle(batch: ImportBatch, today: string): string {
  const parts = [formatDate(batch.imported_at), rowsText(batch)];
  if (stillCancellable(batch, today)) parts.push(untilText(batch));
  return parts.join(" · ");
}

export interface BatchListProps {
  shopId: string;
  today: string;
  onOpen: (batch: ImportBatch) => void;
}

/**
 * Liste des lots passés (T45) : numéro, modèle, date, lignes importées et ignorées, pastille,
 * « Annulable jusqu'au JJ/MM » tant que le délai court. Hors ligne : bannière et « Réessayer ».
 */
export function BatchList({ shopId, today, onOpen }: BatchListProps) {
  const gateway = useImports();
  const [attempt, setAttempt] = useState(0);
  const loaded = useLoad(`${shopId}:${String(attempt)}`, () => gateway.list(shopId));
  if (loaded.status === "loading") return <Skeleton lines={3} label="Chargement des imports…" />;
  if (loaded.status === "offline") {
    return (
      <Banner
        title="Connexion nécessaire pour voir les imports passés."
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
  if (loaded.value.length === 0) return <EmptyState message={NO_BATCH} />;
  return (
    <ListCard label={HISTORY_LABEL}>
      {loaded.value.map((batch) => (
        <ListCardRow
          key={batch.id}
          title={`${batch.number} · ${modelOf(batch.kind).label}`}
          subtitle={subtitle(batch, today)}
          badge={<BatchBadge batch={batch} />}
          cancelled={batch.status === "cancelled"}
          onOpen={() => {
            onOpen(batch);
          }}
        />
      ))}
    </ListCard>
  );
}
