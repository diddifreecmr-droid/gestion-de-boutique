import { LogOut } from "lucide-react";
import { Link } from "react-router";
import { useSessionState } from "../../core/services/servicesContext";
import { Banner } from "../../shared/ui";
import { AuthScreen } from "./AuthScreen";
import { LoginForm } from "./LoginForm";

export const LOGIN_PATH = "/connexion";
export const ADMIN_LOGIN_PATH = "/connexion/admin";

/** Motif de la dernière fin de session (révocation, compte désactivé, expiration). */
function SessionNotice() {
  const state = useSessionState();
  if (state.status !== "signedOut" || state.notice === null) return null;
  return <Banner title={state.notice} icon={LogOut} />;
}

/** UC-SOC-02 — Se connecter : numéro de téléphone + code secret à 6 chiffres. */
export function LoginPage() {
  return (
    <AuthScreen title="Connexion" intro="Entrez votre numéro de téléphone et votre code secret.">
      <SessionNotice />
      <LoginForm kind="pin" />
      <Link className="text-label font-semibold text-primary underline" to={ADMIN_LOGIN_PATH}>
        Connexion administrateur plateforme
      </Link>
    </AuthScreen>
  );
}

/** Administrateur plateforme : téléphone + mot de passe (10 caractères au moins). */
export function AdminLoginPage() {
  return (
    <AuthScreen
      title="Connexion administrateur"
      intro="Réservé à l'équipe qui fournit l'application : téléphone et mot de passe."
    >
      <SessionNotice />
      <LoginForm kind="password" />
      <Link className="text-label font-semibold text-primary underline" to={LOGIN_PATH}>
        Retour à la connexion des boutiques
      </Link>
    </AuthScreen>
  );
}
