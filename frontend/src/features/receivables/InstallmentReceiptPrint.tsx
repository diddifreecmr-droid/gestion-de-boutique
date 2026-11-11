import { lazy, Suspense } from "react";
import { Skeleton } from "../../shared/ui";
import type { InstallmentReceiptViewProps } from "./receipt/InstallmentReceiptView";

/** Vue d'impression et ses styles, chargés au premier « Imprimer le reçu » seulement. */
const InstallmentReceiptView = lazy(() => import("./receipt/InstallmentReceiptView"));

export function InstallmentReceiptPrint(props: InstallmentReceiptViewProps) {
  return (
    <Suspense fallback={<Skeleton lines={6} label="Ouverture du reçu…" />}>
      <InstallmentReceiptView {...props} />
    </Suspense>
  );
}
