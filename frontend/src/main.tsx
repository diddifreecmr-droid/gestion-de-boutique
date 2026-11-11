import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
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
