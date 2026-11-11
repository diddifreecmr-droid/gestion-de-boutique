/// <reference lib="webworker" />
/**
 * Service worker minimal (specs.md § 4.6, § 7.2) : précache des fichiers du build.
 *
 * Mise à jour au prochain lancement : pas de `skipWaiting()` ni de `clientsClaim()`.
 * Une nouvelle version s'installe en arrière-plan puis attend ; elle prend la main quand
 * tous les onglets de l'application ont été fermés, c'est-à-dire au lancement suivant.
 * L'ossature hors-ligne (Dexie, outbox) viendra à T23.
 */
import { cleanupOutdatedCaches, precacheAndRoute } from "workbox-precaching";

declare const self: ServiceWorkerGlobalScope;

cleanupOutdatedCaches();
precacheAndRoute(self.__WB_MANIFEST);
