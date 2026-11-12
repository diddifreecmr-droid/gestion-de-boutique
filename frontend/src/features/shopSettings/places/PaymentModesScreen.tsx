import { useState } from "react";
import { Plus } from "lucide-react";
import { uuidV7 } from "../../../core/api/uuidv7";
import type { PaymentModePatch, ShopPaymentMode } from "../../../core/gateways/shopAdminContract";
import { useShopAdmin } from "../../../core/gateways/httpShopAdmin";
import { Button, TextField } from "../../../shared/ui";
import { FormMessage } from "../../expenses/FormMessage";
import { useLoad } from "../../expenses/useLoad";
import { ScreenFrame } from "../ScreenFrame";
import type { SettingsScreenProps } from "../settingsNav";
import { useAction } from "../useAction";
import { YesNoChips } from "../YesNoChips";
import { PaymentModeRow } from "./PaymentModeRow";
import { mergeById } from "./mergeById";

/** Modes de paiement (UC-SOC-06, SET-03) : ajouter (« Wave »), renommer, référence, désactiver. */
export function PaymentModesScreen({ shopId, onBack }: SettingsScreenProps) {
  const gateway = useShopAdmin();
  const [round, setRound] = useState(0);
  const loaded = useLoad(`${shopId}:${String(round)}`, () => gateway.paymentModes(shopId));
  const [changed, setChanged] = useState<ShopPaymentMode[]>([]);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | undefined>(undefined);
  const [reference, setReference] = useState(false);
  const action = useAction();

  return (
    <ScreenFrame
      title="Modes de paiement"
      onBack={onBack}
      loaded={loaded}
      onRetry={() => {
        setRound((n) => n + 1);
      }}
    >
      {(initial) => {
        const modes = mergeById(initial, changed);
        const keep = (mode: ShopPaymentMode) => {
          setChanged((current) => [...current.filter((m) => m.id !== mode.id), mode]);
        };
        const patch = (mode: ShopPaymentMode, change: Omit<PaymentModePatch, "version">) =>
          action.run(mode.id, async () => {
            keep(
              await gateway.updatePaymentMode(shopId, mode.id, {
                ...change,
                version: mode.version,
              }),
            );
          });
        const add = async () => {
          if (name.trim() === "") {
            setNameError("Le nom est vide");
            return;
          }
          const order = Math.max(0, ...modes.map((m) => m.display_order)) + 1;
          const done = await action.run("new", async () => {
            keep(
              await gateway.createPaymentMode(shopId, {
                id: uuidV7(),
                name: name.trim(),
                reference_required: reference,
                display_order: order,
              }),
            );
          });
          if (done) {
            setName("");
            setReference(false);
          }
        };
        return (
          <>
            <ul
              aria-label="Modes de paiement"
              className="m-0 list-none divide-y divide-border rounded-lg bg-surface p-0 shadow-card"
            >
              {modes.map((mode) => (
                <PaymentModeRow
                  key={mode.id}
                  mode={mode}
                  busy={action.busy === mode.id}
                  onPatch={(change) => patch(mode, change)}
                />
              ))}
            </ul>
            {action.message !== null && <FormMessage text={action.message} />}
            <section aria-labelledby="new-mode" className="flex flex-col gap-4">
              <h2 id="new-mode" className="m-0 text-title-sm font-semibold text-text">
                Nouveau mode de paiement
              </h2>
              <TextField
                label="Nom du mode"
                value={name}
                maxLength={200}
                error={nameError}
                onChange={(event) => {
                  setName(event.target.value);
                  setNameError(undefined);
                }}
              />
              <YesNoChips
                label="Référence de la transaction obligatoire"
                value={reference}
                onChange={setReference}
              />
              <Button
                variant="secondary"
                icon={Plus}
                fullWidth
                loading={action.busy === "new"}
                onClick={() => void add()}
              >
                Ajouter le mode
              </Button>
            </section>
          </>
        );
      }}
    </ScreenFrame>
  );
}
