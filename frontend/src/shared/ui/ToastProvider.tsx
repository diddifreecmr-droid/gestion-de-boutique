import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Toast } from "./Toast";
import { TOAST_SUCCESS_MS, ToastContext, type ToastApi, type ToastMessage } from "./toastContext";
import { requireText } from "./controlClasses";

interface ActiveToast extends ToastMessage {
  id: number;
}

/**
 * Fournit `useToast()` et affiche les toasts en haut de l'écran (§ 6.5). Deux régions
 * vivantes toujours présentes : `status` (polie) pour les succès, `alert` pour les erreurs.
 * Un succès disparaît après 4 s ; une erreur reste jusqu'à ce qu'on la ferme.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ActiveToast[]>([]);
  const nextId = useRef(1);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    const timer = timers.current.get(id);
    if (timer !== undefined) clearTimeout(timer);
    timers.current.delete(id);
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback(
    (toast: ToastMessage) => {
      requireText("Toast", "message", toast.message);
      const id = nextId.current++;
      setToasts((current) => [...current, { ...toast, id }]);
      if (toast.tone === "success") {
        timers.current.set(
          id,
          setTimeout(() => {
            dismiss(id);
          }, TOAST_SUCCESS_MS),
        );
      }
      return id;
    },
    [dismiss],
  );

  useEffect(() => {
    const pending = timers.current;
    return () => {
      pending.forEach((timer) => {
        clearTimeout(timer);
      });
      pending.clear();
    };
  }, []);

  const api = useMemo<ToastApi>(() => ({ show, dismiss }), [show, dismiss]);
  const region = (tone: ToastMessage["tone"]) =>
    toasts
      .filter((toast) => toast.tone === tone)
      .map((toast) => (
        <Toast
          key={toast.id}
          tone={toast.tone}
          message={toast.message}
          onClose={() => {
            dismiss(toast.id);
          }}
        />
      ));

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-0 z-50 flex justify-center p-4">
        <div className="pointer-events-auto flex w-full max-w-150 flex-col gap-2">
          <div role="alert" className="flex flex-col gap-2">
            {region("error")}
          </div>
          <div role="status" className="flex flex-col gap-2">
            {region("success")}
          </div>
        </div>
      </div>
    </ToastContext.Provider>
  );
}
