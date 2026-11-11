import { AlertCircle, CheckCircle2, X } from "lucide-react";
import type { ToastTone } from "./toastContext";

export interface ToastProps {
  tone: ToastTone;
  message: string;
  onClose: () => void;
}

const TONES: Record<ToastTone, string> = {
  success: "bg-success text-on-primary",
  error: "bg-danger text-on-primary",
};

/**
 * Retour après une action (§ 6.5) : success/blanc ou danger/blanc, 48 px au moins,
 * icône + texte, bouton « Fermer » (icône + mot, P5). L'annonce est faite par la région
 * qui le contient (ToastProvider), pas par le toast lui-même.
 */
export function Toast({ tone, message, onClose }: ToastProps) {
  const Icon = tone === "success" ? CheckCircle2 : AlertCircle;
  return (
    <div
      className={`flex min-h-(--control-md) w-full items-center gap-2 rounded-md py-1 pr-1 pl-4 shadow-card ${TONES[tone]}`}
    >
      <Icon aria-hidden="true" className="size-6 shrink-0" />
      <p className="m-0 flex-1 text-body font-semibold">{message}</p>
      <button
        type="button"
        onClick={onClose}
        className={
          "inline-flex min-h-(--control-md) shrink-0 items-center gap-1 rounded-md px-2 " +
          "text-label font-semibold outline-hidden focus-visible:outline-2 focus-visible:outline-solid " +
          "focus-visible:outline-on-primary"
        }
      >
        <X aria-hidden="true" className="size-6 shrink-0" />
        <span>Fermer</span>
      </button>
    </div>
  );
}
