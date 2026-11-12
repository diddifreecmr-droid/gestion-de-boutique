import { useState } from "react";
import type { ReceiptFormat } from "../../../core/gateways/shopAdminContract";
import { ChoiceChips, TextField } from "../../../shared/ui";
import { YesNoChips } from "../YesNoChips";
import { SettingsSection, type SectionProps } from "./SettingsSection";
import { optionalText } from "./settingsInputs";

const FORMATS: readonly { value: ReceiptFormat; label: string }[] = [
  { value: "58mm", label: "Ticket 58 mm" },
  { value: "80mm", label: "Ticket 80 mm" },
  { value: "a5", label: "Feuille A5" },
  { value: "a4", label: "Feuille A4" },
];

const COPIES = [
  { value: "1", label: "1 exemplaire" },
  { value: "2", label: "2 exemplaires" },
  { value: "3", label: "3 exemplaires" },
] as const;

type Copies = (typeof COPIES)[number]["value"];

function copiesOf(value: number): Copies {
  const found = COPIES.find((choice) => choice.value === String(value));
  if (found === undefined)
    throw new Error(`Nombre d'exemplaires hors bornes (1 à 3) : ${String(value)}`);
  return found.value;
}

function formatOf(value: string): ReceiptFormat {
  const found = FORMATS.find((choice) => choice.value === value);
  if (found === undefined) throw new Error(`Format de reçu inconnu : « ${value} »`);
  return found.value;
}

export const FOOTER_MAX = 200;

/**
 * Reçu (specs § 9.1, CDC § 20.1) : format (la mise en page suit le profil d'impression du
 * format), nombre d'exemplaires, logo, message de pied de page.
 */
export function ReceiptSection(props: SectionProps) {
  const { settings } = props;
  const [format, setFormat] = useState(formatOf(settings.receipt_format));
  const [copies, setCopies] = useState(copiesOf(settings.copies));
  const [logo, setLogo] = useState(settings.show_logo);
  const [footer, setFooter] = useState(settings.footer_message ?? "");

  const collect = () => ({
    receipt_format: format,
    copies: Number(copies),
    show_logo: logo,
    footer_message: optionalText(footer),
  });

  return (
    <SettingsSection {...props} title="Reçu" collect={collect}>
      <ChoiceChips label="Format du reçu" options={FORMATS} value={format} onChange={setFormat} />
      <p className="m-0 text-body text-text-muted">
        Imprimante : {settings.print_profile} · papier {String(settings.paper_width_mm)} mm, zone
        imprimée {String(settings.printable_width_mm)} mm
      </p>
      <ChoiceChips
        label="Exemplaires imprimés"
        options={COPIES}
        value={copies}
        onChange={setCopies}
      />
      <YesNoChips label="Logo sur le reçu" value={logo} onChange={setLogo} />
      <TextField
        label="Message en bas du reçu (facultatif)"
        hint={`${String(FOOTER_MAX)} caractères au plus`}
        value={footer}
        maxLength={FOOTER_MAX}
        onChange={(event) => {
          setFooter(event.target.value);
        }}
      />
    </SettingsSection>
  );
}
