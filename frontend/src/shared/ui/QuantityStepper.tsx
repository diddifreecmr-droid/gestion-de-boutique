import type { LucideIcon } from "lucide-react";
import { Minus, Plus } from "lucide-react";
import { formatQuantity } from "../format";
import { Field } from "./Field";
import { FOCUS_OUTLINE, PRESS_TRANSITION } from "./controlClasses";

export interface QuantityStepperProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  /** Borne basse (1 par défaut : une ligne de vente a au moins un article). */
  min?: number;
  /** Borne haute explicite. */
  max?: number;
  /** Stock disponible : affiché dessous (« Stock disponible : 4 ») et sert aussi de borne. */
  available?: number;
  hint?: string | undefined;
  error?: string | undefined;
  id?: string | undefined;
}

function assertInteger(name: string, value: number): void {
  if (!Number.isSafeInteger(value)) {
    throw new Error(`QuantityStepper : ${name} doit être un entier, reçu ${String(value)}`);
  }
}

interface StepButtonProps {
  icon: LucideIcon;
  label: string;
  blocked: boolean;
  onStep: () => void;
}

/**
 * Bouton − ou + (48 px). Exception à P5 voulue par § 6.2 : le signe est universel et le
 * bouton garde un libellé accessible. Bloqué = `aria-disabled` (il garde le focus clavier).
 */
function StepButton({ icon: Icon, label, blocked, onStep }: StepButtonProps) {
  const state = blocked
    ? "cursor-not-allowed opacity-50"
    : "hover:bg-primary-soft active:bg-primary-soft";
  return (
    <button
      type="button"
      aria-label={label}
      aria-disabled={blocked || undefined}
      onClick={blocked ? undefined : onStep}
      className={
        "inline-flex size-(--control-md) shrink-0 items-center justify-center rounded-md " +
        `border border-border-strong bg-surface text-primary ${PRESS_TRANSITION} ` +
        `${FOCUS_OUTLINE} ${state}`
      }
    >
      <Icon aria-hidden="true" className="size-6" />
    </button>
  );
}

/** Quantité entière avec boutons − et + de 48 px de chaque côté (§ 6.2). */
export function QuantityStepper({
  label,
  value,
  onChange,
  min = 1,
  max,
  available,
  hint,
  error,
  id,
}: QuantityStepperProps) {
  assertInteger("value", value);
  assertInteger("min", min);
  const bounds = [max, available].filter((bound) => bound !== undefined);
  bounds.forEach((bound) => {
    assertInteger("max / available", bound);
  });
  const upper = bounds.length === 0 ? Number.MAX_SAFE_INTEGER : Math.min(...bounds);
  if (min > upper) {
    throw new Error(
      `QuantityStepper : bornes impossibles (min ${String(min)} > max ${String(upper)})`,
    );
  }
  if (value < min || value > upper) {
    throw new Error(
      `QuantityStepper : valeur ${String(value)} hors des bornes [${String(min)}, ${String(upper)}]`,
    );
  }

  const footer =
    available === undefined ? undefined : (
      <p className="m-0 text-body text-text-muted">
        Stock disponible : {formatQuantity(available)}
      </p>
    );

  return (
    <Field label={label} hint={hint} error={error} id={id} footer={footer}>
      {(control) => (
        <div className="flex items-center gap-4">
          <StepButton
            icon={Minus}
            label={`${label} : moins un`}
            blocked={value <= min}
            onStep={() => {
              onChange(value - 1);
            }}
          />
          <output
            id={control.id}
            aria-describedby={control["aria-describedby"]}
            aria-live="polite"
            className="min-w-12 text-center text-lead font-bold tabular-nums"
          >
            {formatQuantity(value)}
          </output>
          <StepButton
            icon={Plus}
            label={`${label} : plus un`}
            blocked={value >= upper}
            onStep={() => {
              onChange(value + 1);
            }}
          />
        </div>
      )}
    </Field>
  );
}
