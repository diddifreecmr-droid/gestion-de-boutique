import { useState } from "react";
import { Banknote, Clock, Smartphone } from "lucide-react";
import {
  AmountField,
  ChoiceChips,
  Disclosure,
  QuantityStepper,
  SearchField,
  Switch,
  TextField,
  type ChoiceOption,
} from "../../shared/ui";
import { GallerySection, StateLabel } from "./GallerySection";

type Payment = "cash" | "orange" | "mtn" | "credit";

const PAYMENTS: ChoiceOption<Payment>[] = [
  { value: "cash", label: "Espèces", icon: Banknote },
  { value: "orange", label: "Orange Money", icon: Smartphone },
  { value: "mtn", label: "MTN MoMo", icon: Smartphone },
  { value: "credit", label: "À crédit", icon: Clock },
];

export function FieldGallery() {
  const [name, setName] = useState("");
  const [price, setPrice] = useState<number | null>(780000);
  const [emptyPrice, setEmptyPrice] = useState<number | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [lastUnit, setLastUnit] = useState(4);
  const [payment, setPayment] = useState<Payment | null>("cash");
  const [noChoice, setNoChoice] = useState<Payment | null>(null);
  const [credit, setCredit] = useState(true);
  const [transport, setTransport] = useState(false);
  const [search, setSearch] = useState("Haojue");
  const [emptySearch, setEmptySearch] = useState("");

  return (
    <>
      <GallerySection title="TextField">
        <TextField
          label="Nom du client"
          hint="Facultatif"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
        />
        <TextField label="Numéro de châssis" defaultValue="LBPKE1300" />
        <TextField label="Téléphone" error="Le numéro est vide" defaultValue="" />
      </GallerySection>

      <GallerySection title="AmountField">
        <AmountField label="Prix" value={price} onChange={setPrice} />
        <AmountField
          label="Prix (vide, en erreur)"
          value={emptyPrice}
          onChange={setEmptyPrice}
          error="Le prix est vide"
        />
      </GallerySection>

      <GallerySection title="QuantityStepper">
        <QuantityStepper label="Quantité" value={quantity} onChange={setQuantity} available={4} />
        <StateLabel>Borne haute atteinte</StateLabel>
        <QuantityStepper
          label="Quantité (tout le stock)"
          value={lastUnit}
          onChange={setLastUnit}
          available={4}
        />
        <QuantityStepper
          label="Quantité (en erreur)"
          value={1}
          onChange={() => undefined}
          error="Stock insuffisant à Garoua"
        />
      </GallerySection>

      <GallerySection title="ChoiceChips">
        <ChoiceChips label="Paiement" options={PAYMENTS} value={payment} onChange={setPayment} />
        <ChoiceChips
          label="Paiement (aucun choix)"
          options={PAYMENTS}
          value={noChoice}
          onChange={setNoChoice}
        />
      </GallerySection>

      <GallerySection title="Switch">
        <Switch label="Créances" checked={credit} onChange={setCredit} />
        <Switch
          label="Transport"
          hint="Nécessite Transferts de stock."
          checked={transport}
          onChange={setTransport}
        />
      </GallerySection>

      <GallerySection title="Disclosure">
        <Disclosure>
          <TextField label="Couleur" />
          <TextField label="Châssis" />
        </Disclosure>
        <Disclosure label="Plus de détails (ouvert)" defaultOpen>
          <TextField label="Client" />
        </Disclosure>
      </GallerySection>

      <GallerySection title="SearchField">
        <SearchField label="Article" value={search} onChange={setSearch} />
        <SearchField
          label="Article (vide)"
          placeholder="Nom ou modèle"
          value={emptySearch}
          onChange={setEmptySearch}
        />
      </GallerySection>
    </>
  );
}
