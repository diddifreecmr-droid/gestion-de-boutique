import { useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import type { OpenedShop } from "../../core/gateways/platformContract";
import { createHttpPlatform, PlatformContext } from "../../core/gateways/httpPlatform";
import { useServices } from "../../core/services/servicesContext";
import { AccountPage } from "../settings/AccountPage";
import { OpenedShopNotice } from "./OpenedShopNotice";
import { OpenShopForm } from "./OpenShopForm";
import { platformNav, VIEW } from "./platformNav";
import { ShopAdmin } from "./ShopAdmin";
import { ShopList } from "./ShopList";

interface Opened {
  opened: OpenedShop;
  ownerPhone: string;
}

function Screens() {
  const [params, setParams] = useSearchParams();
  const nav = platformNav(setParams);
  // Le code provisoire vit ici, en mémoire seulement : jamais dans l'adresse ni le stockage.
  const [opened, setOpened] = useState<Opened | null>(null);
  if (opened !== null) {
    return (
      <OpenedShopNotice
        opened={opened.opened}
        ownerPhone={opened.ownerPhone}
        onDone={() => {
          setOpened(null);
          nav.list();
        }}
      />
    );
  }
  const id = params.get("id");
  if (params.get("vue") === VIEW.create) {
    return (
      <OpenShopForm
        nav={nav}
        onOpened={(shop, ownerPhone) => {
          setOpened({ opened: shop, ownerPhone });
        }}
      />
    );
  }
  if (id !== null) return <ShopAdmin key={id} shopId={id} nav={nav} />;
  // Accueil de la console : la liste, puis « Mon compte » (une seule fois, ici seulement).
  return (
    <>
      <ShopList nav={nav} />
      <AccountPage title="Mon compte" />
    </>
  );
}

/** Console plateforme (chargée à la demande) : boutiques, ouverture, statut, droits, délégation. */
export default function PlatformConsole() {
  const services = useServices();
  const gateway = useMemo(() => createHttpPlatform(services), [services]);
  return (
    <PlatformContext.Provider value={gateway}>
      <Screens />
    </PlatformContext.Provider>
  );
}
