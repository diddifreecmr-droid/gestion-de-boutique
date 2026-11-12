import type { EntitlementState, ShopAccess } from "../../core/gateways/platformContract";
import { formatDate, formatTime } from "../../shared/format";
import { Badge, ChoiceChips } from "../../shared/ui";

type Choice = "plan" | "on" | "off";

const CHOICES = [
  { value: "plan", label: "Selon l'offre" },
  { value: "on", label: "Activé" },
  { value: "off", label: "Désactivé" },
] as const;

const ENTITLEMENT_LABELS: Readonly<Record<string, string>> = {
  offline_capture: "Saisie hors connexion",
};

function choiceOf(state: EntitlementState): Choice {
  if (state.override === null) return "plan";
  return state.override ? "on" : "off";
}

/** Valeur envoyée au serveur : `null` retire la surcharge (l'offre du compte décide). */
function overrideOf(choice: Choice): boolean | null {
  if (choice === "plan") return null;
  return choice === "on";
}

/**
 * Droits d'offre (TR-26) : valeur en vigueur et réglage de l'administrateur ; délégation du
 * propriétaire (24 h), qu'il est **seul** à pouvoir accorder (CDC § 4.1).
 */
export function ShopRights({
  access,
  busy,
  onOverride,
}: {
  access: ShopAccess;
  busy: boolean;
  onOverride: (code: EntitlementState["code"], value: boolean | null) => void;
}) {
  const until = access.admin_access_until;
  return (
    <>
      <h2 className="m-0 text-title-sm font-bold text-text">Droits d'offre</h2>
      {access.entitlements.map((state) => {
        const label = ENTITLEMENT_LABELS[state.code] ?? state.code;
        return (
          <div key={state.code} className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-lead text-text">{label}</span>
              {state.enabled ? (
                <Badge status="success">Actif</Badge>
              ) : (
                <Badge status="offline">Inactif</Badge>
              )}
            </div>
            <ChoiceChips
              label={`Réglage : ${label}`}
              options={CHOICES}
              value={choiceOf(state)}
              onChange={(choice) => {
                if (!busy) onOverride(state.code, overrideOf(choice));
              }}
            />
          </div>
        );
      })}
      <h2 className="m-0 text-title-sm font-bold text-text">Accès à la boutique</h2>
      <p className="m-0 text-body text-text">
        {until === null
          ? "Aucun accès en cours. Seul le propriétaire peut vous ouvrir sa boutique, en consultation et pour 24 h, depuis ses réglages."
          : `Le propriétaire vous a ouvert sa boutique en consultation jusqu'au ${formatDate(until)} à ${formatTime(until)}. Chaque consultation est inscrite dans son journal.`}
      </p>
    </>
  );
}
