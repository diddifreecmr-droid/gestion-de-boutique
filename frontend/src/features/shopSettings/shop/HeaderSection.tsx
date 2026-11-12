import { useState } from "react";
import { TextField } from "../../../shared/ui";
import { SettingsSection, type SectionProps } from "./SettingsSection";
import { optionalText } from "./settingsInputs";

/**
 * En-tête du reçu (UC-SOC-06) : ville, téléphone, adresse, NIU, RCCM. Le nom de la boutique
 * se change depuis la console de la plateforme ; il est rappelé ici.
 */
export function HeaderSection(props: SectionProps) {
  const { header } = props.settings;
  const [city, setCity] = useState(header.city);
  const [phone, setPhone] = useState(header.phone);
  const [address, setAddress] = useState(header.address ?? "");
  const [niu, setNiu] = useState(header.niu ?? "");
  const [rccm, setRccm] = useState(header.rccm ?? "");
  const [errors, setErrors] = useState<{ city?: string; phone?: string }>({});

  const collect = () => {
    const found = {
      ...(city.trim() === "" ? { city: "La ville est vide" } : {}),
      ...(phone.trim() === "" ? { phone: "Le téléphone est vide" } : {}),
    };
    setErrors(found);
    if (Object.keys(found).length > 0) return null;
    return {
      city: city.trim(),
      phone: phone.trim(),
      address: optionalText(address),
      niu: optionalText(niu),
      rccm: optionalText(rccm),
    };
  };

  return (
    <SettingsSection {...props} title="En-tête du reçu" collect={collect}>
      <p className="m-0 text-lead font-semibold text-text">{header.name}</p>
      <TextField
        label="Ville"
        value={city}
        maxLength={200}
        error={errors.city}
        onChange={(event) => {
          setCity(event.target.value);
          setErrors({});
        }}
      />
      <TextField
        label="Téléphone de la boutique"
        type="tel"
        inputMode="tel"
        value={phone}
        maxLength={32}
        error={errors.phone}
        onChange={(event) => {
          setPhone(event.target.value);
          setErrors({});
        }}
      />
      <TextField
        label="Adresse (facultatif)"
        value={address}
        maxLength={1000}
        onChange={(event) => {
          setAddress(event.target.value);
        }}
      />
      <TextField
        label="NIU (facultatif)"
        value={niu}
        maxLength={100}
        onChange={(event) => {
          setNiu(event.target.value);
        }}
      />
      <TextField
        label="RCCM (facultatif)"
        value={rccm}
        maxLength={100}
        onChange={(event) => {
          setRccm(event.target.value);
        }}
      />
    </SettingsSection>
  );
}
