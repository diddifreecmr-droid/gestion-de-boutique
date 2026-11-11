import { lazy, Suspense } from "react";
import { Skeleton } from "../../shared/ui";
import type { ReceiptViewProps } from "./receipt/ReceiptView";

/** Vue d'impression et ses styles, chargés au premier « Imprimer » seulement. */
const ReceiptView = lazy(() => import("./receipt/ReceiptView"));

export function ReceiptPrint(props: ReceiptViewProps) {
  return (
    <Suspense fallback={<Skeleton lines={6} label="Ouverture du reçu…" />}>
      <ReceiptView {...props} />
    </Suspense>
  );
}
