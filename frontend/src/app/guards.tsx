import { Navigate, Outlet, useLocation } from "react-router";
import { useSessionState } from "../core/services/servicesContext";
import { CHANGE_PIN_PATH } from "../features/auth/ChangePinPage";
import { LOGIN_PATH } from "../features/auth/LoginPage";
import { RestoreFailedScreen, RestoringScreen } from "./StartupScreens";

interface FromState {
  from?: string;
}

/**
 * Garde des écrans connectés : non connecté → connexion (l'adresse demandée est gardée) ;
 * code provisoire → changement de code obligatoire.
 */
export function RequireSession() {
  const state = useSessionState();
  const location = useLocation();
  if (state.status === "restoring") return <RestoringScreen />;
  if (state.status === "failed") return <RestoreFailedScreen error={state.error} />;
  if (state.status === "signedOut") {
    const from: FromState = { from: location.pathname };
    return <Navigate to={LOGIN_PATH} replace state={from} />;
  }
  if (state.me.mustChangePin && location.pathname !== CHANGE_PIN_PATH) {
    return <Navigate to={CHANGE_PIN_PATH} replace />;
  }
  return <Outlet />;
}

/** Écrans de connexion : une fois connecté, retour à l'adresse demandée (ou l'accueil). */
export function PublicOnly() {
  const state = useSessionState();
  const location = useLocation();
  if (state.status === "restoring") return <RestoringScreen />;
  if (state.status === "signedIn") {
    const from = (location.state as FromState | null)?.from;
    return <Navigate to={from ?? "/"} replace />;
  }
  return <Outlet />;
}
