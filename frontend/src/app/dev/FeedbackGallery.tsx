import { useState } from "react";
import { RefreshCw, ShoppingCart, Wrench, XCircle } from "lucide-react";
import {
  Banner,
  Button,
  ConfirmDialog,
  EmptyState,
  Skeleton,
  Toast,
  useToast,
} from "../../shared/ui";
import { GallerySection, StateLabel } from "./GallerySection";

const noop = () => undefined;

type DialogKind = "simple" | "reason" | null;

export function FeedbackGallery() {
  const toast = useToast();
  const [dialog, setDialog] = useState<DialogKind>(null);
  const close = () => {
    setDialog(null);
  };

  return (
    <>
      <GallerySection title="Toast">
        <Toast tone="success" message="Vente enregistrée — reçu n° V-000124" onClose={noop} />
        <Toast tone="error" message="La vente n'a pas été enregistrée" onClose={noop} />
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => {
              toast.show({ tone: "success", message: "Vente enregistrée — reçu n° V-000124" });
            }}
          >
            Afficher un succès (4 s)
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              toast.show({ tone: "error", message: "Échec de l'envoi : réessayez" });
            }}
          >
            Afficher une erreur
          </Button>
        </div>
      </GallerySection>

      <GallerySection title="Banner">
        <Banner
          title="Connexion nécessaire"
          action={
            <Button variant="secondary" icon={RefreshCw}>
              Réessayer
            </Button>
          }
        >
          Vos saisies ne peuvent pas être envoyées sans réseau.
        </Banner>
        <Banner title="Maintenance ce soir à 22 h 00" icon={Wrench} />
      </GallerySection>

      <GallerySection title="ConfirmDialog">
        <div className="flex flex-wrap gap-2">
          <Button
            variant="danger"
            onClick={() => {
              setDialog("simple");
            }}
          >
            Se déconnecter
          </Button>
          <Button
            variant="danger"
            icon={XCircle}
            onClick={() => {
              setDialog("reason");
            }}
          >
            Annuler la vente
          </Button>
        </div>
        <ConfirmDialog
          open={dialog === "simple"}
          title="Se déconnecter ?"
          confirmLabel="Se déconnecter"
          onConfirm={close}
          onCancel={close}
        >
          Deux saisies sont encore en attente d&apos;envoi.
        </ConfirmDialog>
        <ConfirmDialog
          open={dialog === "reason"}
          title="Annuler la vente V-000124 ?"
          confirmLabel="Annuler la vente"
          confirmIcon={XCircle}
          requireReason
          onConfirm={close}
          onCancel={close}
        >
          La vente reste visible, barrée, avec le motif.
        </ConfirmDialog>
      </GallerySection>

      <GallerySection title="EmptyState">
        <EmptyState
          message="Aucune vente aujourd'hui"
          icon={ShoppingCart}
          action={<Button icon={ShoppingCart}>Nouvelle vente</Button>}
        />
        <StateLabel>Sans action</StateLabel>
        <EmptyState message="Aucune alerte" />
      </GallerySection>

      <GallerySection title="Skeleton">
        <Skeleton />
        <Skeleton lines={1} label="Chargement du stock…" />
      </GallerySection>
    </>
  );
}
