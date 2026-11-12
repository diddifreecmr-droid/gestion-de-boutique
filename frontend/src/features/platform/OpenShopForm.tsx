import { useState } from "react";
import { ArrowLeft, Check } from "lucide-react";
import type { OpenedShop, OpenShopInput } from "../../core/gateways/platformContract";
import { usePlatformGateway } from "../../core/gateways/httpPlatform";
import { ActionBar, Button, Disclosure, TextField } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "../expenses/useLoad";
import { platformErrorMessage, PROFILES, type PlatformNav } from "./platformNav";

interface Fields {
  name: string;
  city: string;
  phone: string;
  address: string;
  ownerName: string;
  ownerPhone: string;
}

const EMPTY: Fields = { name: "", city: "", phone: "", address: "", ownerName: "", ownerPhone: "" };

const REQUIRED: readonly { key: keyof Fields; label: string; tel?: boolean }[] = [
  { key: "name", label: "Nom de la boutique" },
  { key: "city", label: "Ville" },
  { key: "phone", label: "Téléphone de la boutique", tel: true },
  { key: "ownerName", label: "Nom du propriétaire" },
  { key: "ownerPhone", label: "Téléphone du propriétaire", tel: true },
];

function body(fields: Fields): OpenShopInput {
  const address = fields.address.trim();
  return {
    profile_code: PROFILES[0].value,
    name: fields.name.trim(),
    city: fields.city.trim(),
    phone: fields.phone.trim(),
    address: address === "" ? null : address,
    owner: { name: fields.ownerName.trim(), phone: fields.ownerPhone.trim() },
  };
}

/**
 * Ouvrir une boutique et créer son propriétaire (UC-SOC-01, PLT-01) : le serveur crée lieux,
 * modes de paiement et réglages du profil, et renvoie **une fois** le code provisoire.
 */
export function OpenShopForm({
  nav,
  onOpened,
}: {
  nav: PlatformNav;
  onOpened: (opened: OpenedShop, ownerPhone: string) => void;
}) {
  const gateway = usePlatformGateway();
  const [fields, setFields] = useState(EMPTY);
  const [checked, setChecked] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const missing = REQUIRED.filter(({ key }) => fields[key].trim() === "");

  const submit = async () => {
    setChecked(true);
    if (pending || missing.length > 0) return;
    setPending(true);
    setMessage(null);
    try {
      onOpened(await gateway.open(body(fields)), fields.ownerPhone.trim());
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

  const set = (key: keyof Fields, value: string) => {
    setFields((current) => ({ ...current, [key]: value }));
  };
  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
        Retour aux boutiques
      </Button>
      <h1 className="m-0 text-title font-bold text-text">Ouvrir une boutique</h1>
      <p className="m-0 text-body text-text-muted">Type de boutique : {PROFILES[0].label}</p>
      {REQUIRED.map(({ key, label, tel }) => (
        <TextField
          key={key}
          label={label}
          required
          maxLength={tel === true ? 32 : 120}
          {...(tel === true ? { type: "tel", inputMode: "tel" as const } : {})}
          value={fields[key]}
          error={checked && fields[key].trim() === "" ? `${label} : obligatoire` : undefined}
          onChange={(event) => {
            set(key, event.target.value);
          }}
        />
      ))}
      <Disclosure>
        <TextField
          label="Adresse"
          maxLength={200}
          value={fields.address}
          onChange={(event) => {
            set("address", event.target.value);
          }}
        />
      </Disclosure>
      {message !== null && <FormMessage text={message} />}
      <div className="sticky bottom-0 z-20 -mx-4">
        <ActionBar fixed={false}>
          <Button size="lg" fullWidth icon={Check} loading={pending} onClick={() => void submit()}>
            Ouvrir la boutique
          </Button>
        </ActionBar>
      </div>
    </>
  );
}
