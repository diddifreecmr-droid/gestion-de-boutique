import type { SaleShortcut } from "../../core/gateways/catalogContract";
import { ChoiceChips, QuantityStepper, SegmentedControl, TextField } from "../../shared/ui";
import { meterStock, withMode, type LineDraft } from "./draft";
import { lineTenths } from "./lineQuantity";
import {
  lengthInput,
  maxPieces,
  metersText,
  piecesTenths,
  piecesText,
  resolveShortcut,
  shortcutLabel,
} from "./textile";

export interface TextileQuantityProps {
  line: LineDraft;
  /** Raccourcis du profil (`GET /profile`, RG-X05), dans l'ordre servi. */
  shortcuts: readonly SaleShortcut[];
  /** Erreur de longueur ou de stock, déjà filtrée par l'écran. */
  error: string | undefined;
  onChange: (line: LineDraft) => void;
}

const MODES = [
  { value: "meter", label: "Au mètre" },
  { value: "piece", label: "À la pièce" },
] as const;

type TextileMode = (typeof MODES)[number]["value"];

function textileMode(line: LineDraft): TextileMode {
  if (line.mode === "meter" || line.mode === "piece") return line.mode;
  throw new Error(`« ${line.article.name} » : ligne à l'unité dans la saisie au mètre`);
}

/** Raccourci qui correspond à la saisie en cours (pastille cochée), sinon aucun. */
function activeShortcut(line: LineDraft, shortcuts: readonly SaleShortcut[]): string | null {
  const tenths = lineTenths(line);
  const found = shortcuts.find((shortcut) => {
    const resolved = resolveShortcut(shortcut, line.article);
    if (resolved.mode === "piece") return line.mode === "piece" && line.quantity === 1;
    return line.mode === "meter" && resolved.tenths === tenths;
  });
  return found?.code ?? null;
}

/**
 * Quantité d'une ligne Textile (design-system § 7.5) : bascule « Au mètre / À la pièce » si
 * l'article se vend à la pièce ; au mètre, raccourcis puis longueur libre au dixième ; à la
 * pièce, nombre de pièces et longueur retirée du stock (au dixième, QC-3).
 */
export function TextileQuantity({ line, shortcuts, error, onChange }: TextileQuantityProps) {
  const mode = textileMode(line);
  const piece = line.article.piece;
  const pick = (code: string) => {
    const shortcut = shortcuts.find((one) => one.code === code);
    if (shortcut === undefined) throw new Error(`Raccourci inconnu : « ${code} »`);
    const resolved = resolveShortcut(shortcut, line.article);
    if (resolved.mode === "piece") onChange({ ...withMode(line, "piece"), quantity: 1 });
    else onChange({ ...withMode(line, "meter"), length: lengthInput(resolved.tenths) });
  };
  return (
    <>
      {piece !== undefined && (
        <SegmentedControl
          label="Vendre au mètre ou à la pièce"
          options={MODES}
          value={mode}
          onChange={(next) => {
            onChange(withMode(line, next));
          }}
        />
      )}
      {mode === "meter" && shortcuts.length > 0 && (
        <ChoiceChips
          compact
          label="Raccourcis"
          options={shortcuts.map((one) => ({
            value: one.code,
            label: shortcutLabel(one, line.article),
          }))}
          value={activeShortcut(line, shortcuts)}
          onChange={pick}
        />
      )}
      {mode === "meter" && (
        <TextField
          label="Longueur"
          inputMode="decimal"
          autoComplete="off"
          suffix="m"
          hint="Au dixième de mètre, par exemple 2,5"
          value={line.length}
          error={error}
          onChange={(event) => {
            onChange({ ...line, length: event.target.value });
          }}
        />
      )}
      {mode === "piece" && piece !== undefined && (
        <>
          <QuantityStepper
            inline
            label="Pièces"
            value={line.quantity}
            max={Math.max(line.quantity, maxPieces(meterStock(line.article), piece.length_m))}
            error={error}
            onChange={(quantity) => {
              onChange({ ...line, quantity });
            }}
          />
          <p className="m-0 text-body text-text-muted">
            {piecesText(line.quantity)} = {metersText(piecesTenths(line.quantity, piece.length_m))}{" "}
            retirés du stock
          </p>
        </>
      )}
    </>
  );
}
