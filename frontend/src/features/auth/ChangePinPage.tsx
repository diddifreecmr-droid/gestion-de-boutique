import { LogOut } from "lucide-react";
import { useNavigate } from "react-router";
import { useSession, useSignedIn } from "../../core/services/servicesContext";
import { Button, useToast } from "../../shared/ui";
import { AuthScreen } from "./AuthScreen";
import { ChangePinForm } from "./ChangePinForm";
import { useSubmit } from "./useSubmit";

export const CHANGE_PIN_PATH = "/changer-code";

/**
 * UC-SOC-07 — Changer son code secret. Imposé à la première connexion (code provisoire,
 * `must_change_pin` ou `PIN_CHANGE_REQUIRED`) : la garde de route y ramène.
 */
export function ChangePinPage() {
  const me = useSignedIn();
  const session = useSession();
  const toast = useToast();
  const navigate = useNavigate();
  const kind = me.isPlatformAdmin ? "password" : "pin";
  const logout = useSubmit((error) => {
    toast.show({ tone: "error", message: `Déconnexion impossible : ${String(error)}` });
  });
  const word = kind === "pin" ? "code" : "mot de passe";
  return (
    <AuthScreen
      title={kind === "pin" ? "Changer mon code" : "Changer mon mot de passe"}
      intro={
        me.mustChangePin
          ? `Première connexion : choisissez votre propre ${word} pour continuer.`
          : `Saisissez votre ${word} actuel, puis deux fois le nouveau.`
      }
    >
      <ChangePinForm
        kind={kind}
        onDone={() => {
          toast.show({
            tone: "success",
            message: kind === "pin" ? "Code changé" : "Mot de passe changé",
          });
          void navigate("/");
        }}
      />
      {me.mustChangePin && (
        <Button
          variant="ghost"
          fullWidth
          icon={LogOut}
          loading={logout.pending}
          onClick={() => void logout.run(() => session.logout())}
        >
          Se déconnecter
        </Button>
      )}
    </AuthScreen>
  );
}
