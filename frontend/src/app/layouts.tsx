import { Outlet } from "react-router";
import { AppBanners } from "./AppBanners";

/** Écrans sans barre du haut (connexion, choix de boutique) : bannières en tête. */
export function BareLayout() {
  return (
    <>
      <AppBanners />
      <Outlet />
    </>
  );
}
