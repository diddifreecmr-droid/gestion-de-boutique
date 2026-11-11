import { useState, type ReactNode } from "react";
import { Check } from "lucide-react";
import { formatMoney } from "../../shared/format";
import {
  ActionBar,
  AmountField,
  Button,
  ChoiceChips,
  Disclosure,
  TextField,
} from "../../shared/ui";
import { type Draft, draftProblems, requiresDescription } from "./draft";
import { ExpenseExtras } from "./ExpenseExtras";
import { expenseErrorMessage } from "./expenseErrors";
import { FormMessage } from "./FormMessage";
import type { References } from "./references";
import { asError } from "./useLoad";

export const FIX_FIELDS = "La dépense n'est pas enregistrée : corrigez les champs signalés.";

export interface ExpenseFormProps {
  shopId: string;
  refs: References;
  title: string;
  initial: Draft;
  today: string;
  submitLabel: string;
  /** Envoi ; une erreur levée est traduite en message, la saisie est conservée. */
  onSubmit: (draft: Draft) => Promise<void>;
  /** Ligne sous le titre (ex. « D-000012 du 10/11/2026 »). */
  intro?: ReactNode;
  /** Catégorie actuelle, gardée dans la liste même désactivée (correction). */
  keepCategoryId?: string;
}

/**
 * Formulaire de dépense en 3 gestes (UC-DEP-01) : montant, catégorie, valider. Le reste est
 * replié sous « Plus de détails » ; la description remonte au-dessus quand la catégorie
 * l'exige (« Autre »).
 */
export function ExpenseForm(props: ExpenseFormProps) {
  const { shopId, refs, title, initial, today, submitLabel, onSubmit, intro } = props;
  const [draft, setDraft] = useState(initial);
  const [showErrors, setShowErrors] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const update = (patch: Partial<Draft>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };
  const problems = draftProblems(draft, refs, today);
  const blocking = Object.keys(problems).length > 0;
  const descriptionAbove = requiresDescription(refs, draft.categoryId);
  const hiddenProblem = showErrors && problems.date !== undefined;
  const extrasFilled =
    initial.tags.length > 0 || initial.beneficiary !== "" || initial.locationId !== null;
  const categories = refs.categories.filter(
    (category) => category.active || category.id === props.keepCategoryId,
  );
  if (categories.length === 0) throw new Error("Aucune catégorie de dépense active");

  const submit = async () => {
    if (submitting) return;
    setShowErrors(true);
    if (blocking) {
      setMessage(FIX_FIELDS);
      return;
    }
    setMessage(null);
    setSubmitting(true);
    try {
      await onSubmit(draft);
    } catch (error) {
      try {
        setMessage(expenseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      {intro}
      <AmountField
        label="Montant"
        value={draft.amount}
        onChange={(amount) => {
          update({ amount });
        }}
        error={showErrors ? problems.amount : undefined}
      />
      <ChoiceChips
        label="Catégorie"
        options={categories.map((category) => ({ value: category.id, label: category.name }))}
        value={draft.categoryId}
        onChange={(categoryId) => {
          update({ categoryId });
        }}
      />
      {showErrors && problems.category !== undefined && <FormMessage text={problems.category} />}
      {descriptionAbove && (
        <TextField
          label="Description"
          hint="Obligatoire pour cette catégorie"
          required
          value={draft.description}
          maxLength={500}
          error={showErrors ? problems.description : undefined}
          onChange={(event) => {
            update({ description: event.target.value });
          }}
        />
      )}
      <Disclosure
        key={hiddenProblem ? "open" : "closed"}
        defaultOpen={hiddenProblem || extrasFilled}
      >
        <ExpenseExtras
          shopId={shopId}
          refs={refs}
          draft={draft}
          problems={problems}
          showErrors={showErrors}
          today={today}
          update={update}
          descriptionAbove={descriptionAbove}
        />
      </Disclosure>
      {message !== null && <FormMessage text={message} />}
      <div className="sticky bottom-16 z-20 -mx-4">
        <ActionBar
          fixed={false}
          summary={draft.amount === null ? undefined : `Montant ${formatMoney(draft.amount)}`}
        >
          <Button
            size="lg"
            fullWidth
            icon={Check}
            loading={submitting}
            onClick={() => void submit()}
          >
            {submitLabel}
          </Button>
        </ActionBar>
      </div>
    </>
  );
}
