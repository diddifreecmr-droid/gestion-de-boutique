import { CheckCircle2, KeyRound } from "lucide-react";
import type { OpenedShop } from "../../core/gateways/platformContract";
import { Banner, Button } from "../../shared/ui";

/**
 * Boutique ouverte (PLT-01) : le code provisoire du propriétaire n'est affiché **qu'ici, une
 * fois** — il n'est ni gardé ni relisible (le serveur ne le renvoie plus). Le propriétaire le
 * changera à sa première connexion. Téléphone déjà connu : son compte est rattaché (PLT-02).
 */
export function OpenedShopNotice({
  opened,
  ownerPhone,
  onDone,
}: {
  opened: OpenedShop;
  ownerPhone: string;
  onDone: () => void;
}) {
  const pin = opened.temporary_pin;
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Boutique ouverte</h1>
      <Banner icon={CheckCircle2} title={`« ${opened.shop.name} » est ouverte.`}>
        {opened.owner_created
          ? "Le compte du propriétaire a été créé."
          : "Ce téléphone avait déjà un compte : il est rattaché à la nouvelle boutique avec son code actuel."}
      </Banner>
      {pin !== null && (
        <div className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card">
          <p className="m-0 flex items-center gap-2 text-body text-text-muted">
            <KeyRound aria-hidden="true" className="size-6 shrink-0" />
            Code provisoire du propriétaire ({ownerPhone})
          </p>
          <p className="m-0 font-mono text-kpi font-bold text-text">{pin}</p>
          <p className="m-0 text-body text-text">
            Notez-le et transmettez-le au propriétaire : il ne sera plus affiché. Il devra le
            changer à sa première connexion.
          </p>
        </div>
      )}
      <Button size="lg" fullWidth onClick={onDone}>
        J'ai noté le code, revenir aux boutiques
      </Button>
    </>
  );
}
