import { useState } from "react";
import { TextField } from "../../../shared/ui";
import { YesNoChips } from "../YesNoChips";
import { SettingsSection, type SectionProps } from "./SettingsSection";
import { parseOptionalInt, parseThreshold } from "./settingsInputs";

/** Texte d'aide de l'accord sous le minimum (décision client du 11/11/2026, specs § 15.1). */
export const APPROVAL_HINT =
  "Non (par défaut) : la vente sous le prix minimum passe avec un avertissement et reste au journal. Oui : le vendeur doit demander votre accord.";

/** Formulaire du seuil : « 2.0 » lu → « 2 » ; « 2.5 » → « 2,5 ». */
const thresholdText = (value: string) => String(Number(value)).replace(".", ",");

/**
 * Prix et stock (UC-SOC-06, CDC § 20.1) : prix minimum, accord du propriétaire sous le
 * minimum (`min_price_requires_approval`, désactivé par défaut), seuil de stock bas, délai
 * d'échange.
 */
export function SalesRulesSection(props: SectionProps) {
  const { settings } = props;
  const [minPrice, setMinPrice] = useState(settings.min_price_enabled);
  const [approval, setApproval] = useState(settings.min_price_requires_approval);
  const [threshold, setThreshold] = useState(thresholdText(settings.low_stock_threshold));
  const [exchange, setExchange] = useState(
    settings.exchange_days === null ? "" : String(settings.exchange_days),
  );
  const [errors, setErrors] = useState<{ threshold?: string; exchange?: string }>({});

  const collect = () => {
    const parsedThreshold = parseThreshold(threshold);
    const parsedExchange = parseOptionalInt(exchange, 0, 365);
    setErrors({
      ...(parsedThreshold.ok ? {} : { threshold: parsedThreshold.error }),
      ...(parsedExchange.ok ? {} : { exchange: parsedExchange.error }),
    });
    if (!parsedThreshold.ok || !parsedExchange.ok) return null;
    const sameThreshold = Number(parsedThreshold.value) === Number(settings.low_stock_threshold);
    return {
      min_price_enabled: minPrice,
      min_price_requires_approval: approval,
      exchange_days: parsedExchange.value,
      ...(sameThreshold ? {} : { low_stock_threshold: parsedThreshold.value }),
    };
  };

  return (
    <SettingsSection {...props} title="Prix et stock" collect={collect}>
      <YesNoChips
        label="Prix minimum activé"
        value={minPrice}
        onChange={(value) => {
          setMinPrice(value);
        }}
      />
      <YesNoChips
        label="Accord du propriétaire sous le prix minimum"
        value={approval}
        onChange={setApproval}
      />
      <p className="m-0 text-body text-text-muted">
        {minPrice ? APPROVAL_HINT : "S'applique seulement quand le prix minimum est activé."}
      </p>
      <TextField
        label="Seuil de stock bas par défaut"
        hint="Alerte quand le stock d'un article descend à ce nombre"
        inputMode="decimal"
        value={threshold}
        error={errors.threshold}
        onChange={(event) => {
          setThreshold(event.target.value);
          setErrors({});
        }}
      />
      <TextField
        label="Délai d'échange (jours, facultatif)"
        inputMode="numeric"
        value={exchange}
        error={errors.exchange}
        onChange={(event) => {
          setExchange(event.target.value);
          setErrors({});
        }}
      />
    </SettingsSection>
  );
}
