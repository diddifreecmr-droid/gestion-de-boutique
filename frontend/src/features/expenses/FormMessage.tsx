import { AlertCircle } from "lucide-react";

/** Message d'erreur d'un écran ou d'un groupe de champs, annoncé poliment (§ 8). */
export function FormMessage({ text }: { text: string }) {
  return (
    <p role="status" className="m-0 flex items-start gap-1 text-body text-danger-text">
      <AlertCircle aria-hidden="true" className="size-6 shrink-0" />
      <span>{text}</span>
    </p>
  );
}
