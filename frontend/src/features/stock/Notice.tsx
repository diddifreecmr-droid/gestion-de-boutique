import { AlertCircle, AlertTriangle, ArrowLeft, RefreshCw } from "lucide-react";
import { Badge, Button, EmptyState, Skeleton } from "../../shared/ui";
import { loadFailureMessage } from "./stockErrors";
import type { Load } from "./useLoad";
import type { StockStatus } from "./stockView";

/** Erreur d'un écran ou d'un formulaire, annoncée poliment (design-system.md § 8). */
export function ErrorText({ text }: { text: string }) {
  return (
    <p role="status" className="m-0 flex items-start gap-1 text-body text-danger-text">
      <AlertCircle aria-hidden="true" className="size-6 shrink-0" />
      <span>{text}</span>
    </p>
  );
}

/** Mise en garde dans le flux (ventes pendant le comptage) : mot + icône, warning (§ 2.2). */
export function WarningText({ text }: { text: string }) {
  return (
    <p
      role="status"
      className="m-0 flex items-start gap-2 rounded-md bg-warning-soft p-3 text-body text-warning-text"
    >
      <AlertTriangle aria-hidden="true" className="size-6 shrink-0" />
      <span>{text}</span>
    </p>
  );
}

export function ScreenTitle({ children }: { children: string }) {
  return <h1 className="m-0 text-title font-bold text-text">{children}</h1>;
}

export function BackButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <Button variant="ghost" icon={ArrowLeft} onClick={onClick}>
      {label}
    </Button>
  );
}

/** Pastille de stock (UC-STK-05) : orange sous le seuil, rouge à zéro ; rien si le stock va. */
export function StockBadge({ status }: { status: StockStatus }) {
  if (status === "low") return <Badge status="warning">Stock bas</Badge>;
  if (status === "out") return <Badge status="danger">Rupture</Badge>;
  return null;
}

/** Lecture pas encore prête : chargement, « Connexion nécessaire » + Réessayer, ou refus. */
export function LoadPending({
  load,
  label,
  onRetry,
}: {
  load: Exclude<Load<unknown>, { status: "ready" }>;
  label: string;
  onRetry: () => void;
}) {
  switch (load.status) {
    case "loading":
      return <Skeleton lines={4} label={label} />;
    case "offline":
      return (
        <EmptyState
          message="Connexion nécessaire pour afficher cet écran."
          action={
            <Button variant="secondary" icon={RefreshCw} onClick={onRetry}>
              Réessayer
            </Button>
          }
        />
      );
    case "failed":
      return <ErrorText text={loadFailureMessage(load.error)} />;
  }
}
