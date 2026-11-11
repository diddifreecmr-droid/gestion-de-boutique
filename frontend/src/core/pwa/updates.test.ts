import { describe, expect, it, vi } from "vitest";
import { reloadLatestVersion } from "./reload";
import { applyUpdate, SW_URL, UPDATE_CHECK_INTERVAL_MS, watchForUpdates } from "./updates";

function fakeWorker(state: ServiceWorkerState = "installing") {
  const worker = Object.assign(new EventTarget(), { state, postMessage: vi.fn() });
  return worker as unknown as ServiceWorker & { state: ServiceWorkerState };
}

function fakeContainer(options: {
  controller: boolean;
  waiting?: ServiceWorker;
  update?: () => Promise<void>;
}) {
  const registration = Object.assign(new EventTarget(), {
    waiting: options.waiting ?? null,
    installing: null as ServiceWorker | null,
    update: vi.fn(options.update ?? (() => Promise.resolve())),
  });
  const container = Object.assign(new EventTarget(), {
    controller: options.controller ? {} : null,
    register: vi.fn(() => Promise.resolve(registration)),
  });
  return {
    registration,
    container: container as unknown as ServiceWorkerContainer,
    raw: container,
  };
}

describe("nouvelle version (specs § 7.3)", () => {
  it("inscrit /sw.js, vérifie à l'ouverture puis toutes les 30 min", async () => {
    const { container, registration, raw } = fakeContainer({ controller: true });
    const timers: [() => void, number][] = [];
    const stop = await watchForUpdates({
      container,
      onUpdateReady: vi.fn(),
      onCheckFailed: vi.fn(),
      setInterval: (handler, ms) => timers.push([handler, ms]),
    });
    expect(raw.register).toHaveBeenCalledWith(SW_URL, { scope: "/", updateViaCache: "none" });
    expect(registration.update).toHaveBeenCalledTimes(1);
    expect(timers.map(([, ms]) => ms)).toEqual([UPDATE_CHECK_INTERVAL_MS]);
    timers[0]?.[0]();
    expect(registration.update).toHaveBeenCalledTimes(2);
    expect(UPDATE_CHECK_INTERVAL_MS).toBe(1_800_000);
    stop();
  });

  it("propose une version déjà en attente, ou celle qui finit de s'installer", async () => {
    const waiting = fakeWorker("installed");
    const { container, registration } = fakeContainer({ controller: true, waiting });
    const onUpdateReady = vi.fn();
    await watchForUpdates({
      container,
      onUpdateReady,
      onCheckFailed: vi.fn(),
      setInterval: () => 0,
    });
    expect(onUpdateReady).toHaveBeenCalledWith(waiting);
    const installing = fakeWorker();
    registration.installing = installing;
    registration.dispatchEvent(new Event("updatefound"));
    installing.state = "installed";
    installing.dispatchEvent(new Event("statechange"));
    expect(onUpdateReady).toHaveBeenLastCalledWith(installing);
  });

  it("première installation (aucun contrôleur) : rien à proposer", async () => {
    const { container } = fakeContainer({ controller: false, waiting: fakeWorker("installed") });
    const onUpdateReady = vi.fn();
    await watchForUpdates({
      container,
      onUpdateReady,
      onCheckFailed: vi.fn(),
      setInterval: () => 0,
    });
    expect(onUpdateReady).not.toHaveBeenCalled();
  });

  it("une vérification impossible (hors ligne) est signalée", async () => {
    const failure = new TypeError("offline");
    const { container } = fakeContainer({
      controller: true,
      update: () => Promise.reject(failure),
    });
    const onCheckFailed = vi.fn();
    await watchForUpdates({
      container,
      onUpdateReady: vi.fn(),
      onCheckFailed,
      setInterval: () => 0,
    });
    await vi.waitFor(() => {
      expect(onCheckFailed).toHaveBeenCalledWith(failure);
    });
  });

  it("« Mettre à jour » : SKIP_WAITING puis rechargement au changement de contrôleur", () => {
    const postMessage = vi.fn();
    const worker = Object.assign(fakeWorker("installed"), { postMessage });
    const { container, raw } = fakeContainer({ controller: true });
    const reload = vi.fn();
    applyUpdate(worker, container, reload);
    expect(postMessage).toHaveBeenCalledWith({ type: "SKIP_WAITING" });
    expect(reload).not.toHaveBeenCalled();
    raw.dispatchEvent(new Event("controllerchange"));
    raw.dispatchEvent(new Event("controllerchange"));
    expect(reload).toHaveBeenCalledOnce();
  });
});

describe("« Recharger la dernière version »", () => {
  it("vide tous les caches, désinscrit le service worker, puis recharge", async () => {
    const order: string[] = [];
    const caches = {
      keys: () => Promise.resolve(["boutique-app-1", "workbox-precache"]),
      delete: (name: string) => {
        order.push(`delete ${name}`);
        return Promise.resolve(true);
      },
    } as unknown as CacheStorage;
    const registration = {
      unregister: () => {
        order.push("unregister");
        return Promise.resolve(true);
      },
    };
    const serviceWorker = {
      getRegistrations: () => Promise.resolve([registration]),
    } as unknown as ServiceWorkerContainer;
    await reloadLatestVersion({ caches, serviceWorker, reload: () => order.push("reload") });
    expect(order).toEqual([
      "delete boutique-app-1",
      "delete workbox-precache",
      "unregister",
      "reload",
    ]);
  });

  it("sans API de cache (contexte non sécurisé) : recharge quand même", async () => {
    const reload = vi.fn();
    await reloadLatestVersion({ caches: undefined, serviceWorker: undefined, reload });
    expect(reload).toHaveBeenCalledOnce();
  });

  it("une désinscription refusée fait échouer l'opération, sans recharger", async () => {
    const reload = vi.fn();
    const serviceWorker = {
      getRegistrations: () => Promise.resolve([{ unregister: () => Promise.resolve(false) }]),
    } as unknown as ServiceWorkerContainer;
    await expect(reloadLatestVersion({ caches: undefined, serviceWorker, reload })).rejects.toThrow(
      "n'a pas pu être désinscrit",
    );
    expect(reload).not.toHaveBeenCalled();
  });
});
