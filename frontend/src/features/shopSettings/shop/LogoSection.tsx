import { useId, useState } from "react";
import { ImageUp, Trash2 } from "lucide-react";
import { uuidV7 } from "../../../core/api/uuidv7";
import { useAttachments } from "../../../core/gateways/httpAttachments";
import { useShopAdmin } from "../../../core/gateways/httpShopAdmin";
import { useShopLogo } from "../../../core/profile/shopLogoContext";
import { Button, FilePickerButton, ShopLogo, useToast } from "../../../shared/ui";
import { attachmentErrorMessage } from "../../attachments/attachmentErrors";
import { canvasCodec, prepareLogo, type ImageCodec } from "../../attachments/prepareFile";
import { FormMessage } from "../../expenses/FormMessage";
import { asError } from "../../expenses/useLoad";
import { settingsErrorMessage } from "../settingsErrors";
import type { SectionProps } from "./SettingsSection";

export const LOGO_HINT =
  "Photo JPG ou PNG, réduite automatiquement. Elle s'affiche en haut de l'écran, en filigrane " +
  "et sur le reçu (si « Logo sur le reçu » est à Oui). Sans logo : les initiales de la boutique.";

type Busy = "upload" | "remove" | null;

/**
 * Logo de la boutique (gérant, specs § 15.1) : envoyer une image (réduite à 512 px, pièce
 * jointe `shop`), la désigner dans les réglages, voir l'aperçu, la retirer. La barre du haut et
 * le filigrane changent aussitôt (`useShopLogo().replace`), sans relire le profil.
 */
export function LogoSection(props: SectionProps & { codec?: ImageCodec }) {
  const { shopId, settings, onSaved, codec = canvasCodec } = props;
  const attachments = useAttachments();
  const admin = useShopAdmin();
  const logo = useShopLogo();
  const toast = useToast();
  const titleId = useId();
  const [busy, setBusy] = useState<Busy>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const run = async (key: Busy, explain: (error: unknown) => string, work: () => Promise<void>) => {
    setBusy(key);
    setMessage(null);
    try {
      await work();
    } catch (error) {
      try {
        setMessage(explain(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(null);
    }
  };

  const designate = async (attachmentId: string | null) => {
    const patch = { logo_attachment_id: attachmentId, version: settings.version };
    onSaved(await admin.updateSettings(shopId, patch));
  };

  const upload = (file: File) =>
    run("upload", attachmentErrorMessage, async () => {
      const prepared = await prepareLogo(file, codec);
      const request = {
        id: uuidV7(),
        ownerType: "shop" as const,
        ownerId: null,
        kind: "photo" as const,
      };
      const sent = await attachments.upload(shopId, {
        ...request,
        file: prepared.blob,
        fileName: prepared.fileName,
      });
      try {
        await designate(sent.id);
      } catch (error) {
        setMessage(settingsErrorMessage(error));
        return;
      }
      logo.replace(URL.createObjectURL(prepared.blob));
      toast.show({ tone: "success", message: "Logo de la boutique : enregistré." });
    });

  const remove = () =>
    run("remove", settingsErrorMessage, async () => {
      await designate(null);
      logo.replace(null);
      toast.show({ tone: "success", message: "Logo retiré : les initiales s'affichent." });
    });

  const hasLogo = settings.logo_attachment_id !== null;
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-card"
    >
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Logo de la boutique
      </h2>
      <div className="flex items-center gap-4">
        <ShopLogo
          name={settings.header.name}
          src={hasLogo ? logo.src : null}
          size="md"
          alt={hasLogo ? "Logo de la boutique" : "Logo générique (initiales)"}
        />
        <p className="m-0 text-body text-text-muted">{LOGO_HINT}</p>
      </div>
      {message !== null && <FormMessage text={message} />}
      <FilePickerButton
        label={hasLogo ? "Changer le logo" : "Envoyer le logo"}
        accept="image/jpeg,image/png,image/*"
        icon={ImageUp}
        loading={busy === "upload"}
        onFile={(file) => void upload(file)}
      />
      {hasLogo && (
        <Button
          variant="ghost"
          icon={Trash2}
          loading={busy === "remove"}
          onClick={() => void remove()}
        >
          Retirer le logo
        </Button>
      )}
    </section>
  );
}
