import { useState } from "react";
import { Repeat, X } from "lucide-react";
import type { ShopSummary } from "../../core/gateways/platformContract";
import { usePlatformGateway } from "../../core/gateways/httpPlatform";
import { Button, ChoiceChips, ConfirmDialog } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "../expenses/useLoad";
import { platformErrorMessage, PROFILES, profileLabel, type ProfileCode } from "./platformNav";

export interface ShopProfileChangeProps {
  shop: ShopSummary;
  /** Bloque le bouton pendant une autre action de la fiche. */
  busy: boolean;
  /** Type changé : la fiche est relue. */
  onChanged: () => void;
}

/**
 * Type de la boutique et « Changer le type de boutique » (QC-1, T38) : permis seulement pour une
 * boutique **sans données** ; sinon le serveur refuse (`PROFILE_CHANGE_BLOCKED`) et l'écran dit
 * ce qui bloque (« 1 article, 1 membre d'un rôle absent du type choisi »).
 */
export function ShopProfileChange({ shop, busy, onChanged }: ShopProfileChangeProps) {
  const gateway = usePlatformGateway();
  const current = profileLabel(shop.profile_code);
  const [choosing, setChoosing] = useState(false);
  const [target, setTarget] = useState<ProfileCode | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const others = PROFILES.filter((profile) => profile.value !== shop.profile_code);

  const change = async (code: ProfileCode) => {
    setConfirming(false);
    setPending(true);
    setMessage(null);
    try {
      await gateway.changeProfile(shop.shop_id, code);
      onChanged();
    } catch (error) {
      try {
        setMessage(platformErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setPending(false);
    }
  };

  const close = () => {
    setChoosing(false);
    setTarget(null);
    setMessage(null);
  };

  return (
    <section aria-label="Type de boutique" className="flex flex-col gap-2">
      <p className="m-0 text-body text-text">Type de boutique : {current}</p>
      {!choosing && (
        <Button
          variant="secondary"
          icon={Repeat}
          fullWidth
          loading={busy}
          onClick={() => {
            setChoosing(true);
          }}
        >
          Changer le type de boutique
        </Button>
      )}
      {choosing && (
        <>
          <ChoiceChips
            label="Nouveau type"
            options={others}
            value={target}
            onChange={(code) => {
              setTarget(code);
              setMessage(null);
            }}
          />
          <p className="m-0 text-body text-text-muted">
            Permis seulement si la boutique n'a encore aucune donnée (article, vente, achat…).
          </p>
          {message !== null && <FormMessage text={message} />}
          <Button
            icon={Repeat}
            fullWidth
            loading={pending || busy}
            onClick={() => {
              if (target === null) setMessage("Choisissez d'abord le nouveau type.");
              else setConfirming(true);
            }}
          >
            Changer le type
          </Button>
          <Button variant="ghost" icon={X} fullWidth onClick={close}>
            Garder « {current} »
          </Button>
        </>
      )}
      {target !== null && (
        <ConfirmDialog
          open={confirming}
          title={`Passer ${shop.name} en ${profileLabel(target)} ?`}
          confirmLabel="Changer le type"
          confirmIcon={Repeat}
          onConfirm={() => void change(target)}
          onCancel={() => {
            setConfirming(false);
          }}
        >
          Les lieux, les rôles proposés et les réglages deviennent ceux du type{" "}
          {profileLabel(target)} ; les lieux inutilisés sont désactivés.
        </ConfirmDialog>
      )}
    </section>
  );
}
