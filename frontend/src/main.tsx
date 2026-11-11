import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { startUpdateWatcher } from "./core/pwa/appUpdate";
import "./app/index.css";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("Élément #root introuvable dans index.html : l'application ne peut pas démarrer");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Service worker et surveillance des nouvelles versions : production seulement (specs § 7.3).
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  startUpdateWatcher(navigator.serviceWorker).catch((error: unknown) => {
    console.error("Inscription du service worker impossible", error);
  });
}
