/**
 * Saisie hors connexion (TR-11, RG-T22 à RG-T25) — service **léger**, présent dès le démarrage
 * mais inerte tant que le droit `offline_capture` n'est actif pour aucune boutique (V1) :
 * aucune base ouverte, Dexie jamais chargé, aucun appel à `/sync` (recette OFF-01, OFF-02).
 *
 * Droit actif : la file (`engine`, chargé à la demande) reçoit les saisies faites sans réseau ;
 * elle part **dans l'ordre** au retour du réseau (`online`) et à l'ouverture (`watch`), puis
 * l'instantané hors ligne est relu (RG-T25). L'état observable donne le compteur « N saisies
 * en attente d'envoi », les refus gardés et les messages d'arrivée.
 */
import { NetworkError } from "../api/errors";
import { createStore, type Store } from "../state/store";
import type { DocPrefix, OfflineSnapshot, OperationType } from "./contract";
import { PREFIX_OF } from "./contract";
import type * as Engine from "./engine";
import { provisionalNumber } from "./provisional";
import type { OfflineRights } from "./rights";
import type { SendBatch } from "./sendQueue";

export interface CaptureState {
  /** Saisies en attente d'envoi, par boutique. */
  pending: Readonly<Record<string, number>>;
  /** Saisies refusées par le serveur (motif gardé), par boutique. */
  rejected: Readonly<Record<string, readonly { number: string; message: string }[]>>;
  /** Dernières arrivées : « Vente V-HL-3F2A-0007 → V-000125 ». */
  arrived: readonly string[];
  /** Dernier envoi en échec hors réseau (ex. droit retiré : `FEATURE_DISABLED`). */
  failure: string | null;
}

export interface CaptureDeps {
  rights: OfflineRights;
  deviceId: () => string;
  /** `POST /shops/{id}/sync`, authentifié. */
  send: SendBatch;
  /** `GET /shops/{id}/offline-snapshot`, authentifié. */
  fetchSnapshot: (shopId: string) => Promise<OfflineSnapshot>;
  /** Chargement de la file : `import("./engine")` (remplacé dans les tests). */
  load?: () => Promise<typeof Engine>;
  now?: () => Date;
}

export interface QueuedEntry {
  shopId: string;
  opId: string;
  type: OperationType;
  capturedAt: Date;
  payload: Record<string, unknown>;
}

export interface OfflineCapture {
  readonly rights: OfflineRights;
  readonly state: Store<CaptureState>;
  /** Identifiant de l'appareil (code des numéros provisoires). */
  deviceId: () => string;
  enabled: (shopId: string) => boolean;
  /** Met la saisie en file et renvoie son numéro provisoire (droit actif seulement). */
  queue: (entry: QueuedEntry) => Promise<string>;
  /** Instantané gardé sur l'appareil (`null` s'il n'a jamais été lu). */
  snapshot: (shopId: string) => Promise<OfflineSnapshot | null>;
  /** Envoie la file puis relit l'instantané ; sans réseau, la file attend (rien n'est perdu). */
  syncNow: (shopId: string) => Promise<void>;
  /** Saisies en attente sur l'appareil, toutes boutiques (0 sans droit, sans rien charger). */
  waiting: () => Promise<number>;
  /** Abandon confirmé deux fois avant la déconnexion (RG-T24) : nombre de saisies perdues. */
  discard: () => Promise<number>;
  /**
   * Boutique ouverte à l'écran : envoie la file maintenant (ouverture) et à chaque retour du
   * réseau (`online`) ; renvoie le débranchement. Droit inactif : ne fait rien.
   */
  watch: (shopId: string, target: Window) => () => void;
}

const EMPTY: CaptureState = { pending: {}, rejected: {}, arrived: [], failure: null };

export function createOfflineCapture(deps: CaptureDeps): OfflineCapture {
  const state = createStore<CaptureState>(EMPTY);
  const load = deps.load ?? (() => import("./engine"));
  const now = deps.now ?? (() => new Date());
  let engine: Promise<{ module: typeof Engine; outbox: Engine.Outbox }> | null = null;
  const open = () =>
    (engine ??= load().then((module) => ({ module, outbox: module.openOutbox() })));
  const patch = (next: Partial<CaptureState>) => {
    state.set({ ...state.get(), ...next });
  };

  const refresh = async (shopId: string) => {
    const { outbox } = await open();
    const [pending, rejected] = await Promise.all([
      outbox.pending(shopId),
      outbox.rejected(shopId),
    ]);
    const current = state.get();
    patch({
      pending: { ...current.pending, [shopId]: pending.length },
      rejected: {
        ...current.rejected,
        [shopId]: rejected.map((op) => ({
          number: op.provisionalNumber,
          message: op.error?.message ?? "Refusée",
        })),
      },
    });
  };

  const requireEnabled = (shopId: string) => {
    if (!deps.rights.isEnabled(shopId)) {
      throw new Error(`Saisie hors connexion non ouverte pour la boutique ${shopId}`);
    }
  };

  const capture: OfflineCapture = {
    rights: deps.rights,
    state,
    deviceId: deps.deviceId,
    enabled: (shopId) => deps.rights.isEnabled(shopId),
    queue: async ({ shopId, opId, type, capturedAt, payload }) => {
      requireEnabled(shopId);
      const { outbox } = await open();
      const deviceId = deps.deviceId();
      const prefix: DocPrefix = PREFIX_OF[type];
      const sequence = await outbox.nextSequence(shopId, deviceId, prefix);
      const number = provisionalNumber(prefix, deviceId, sequence);
      await outbox.enqueue({
        shopId,
        opId,
        type,
        provisionalNumber: number,
        capturedAt: capturedAt.toISOString(),
        payload,
      });
      await refresh(shopId);
      return number;
    },
    snapshot: async (shopId) => {
      requireEnabled(shopId);
      return (await open()).outbox.snapshot(shopId);
    },
    syncNow: async (shopId) => {
      requireEnabled(shopId);
      const { module, outbox } = await open();
      try {
        const report = await module.sendQueue(outbox, deps.send, shopId, deps.deviceId());
        await outbox.saveSnapshot(shopId, await deps.fetchSnapshot(shopId), now());
        patch({ arrived: [...state.get().arrived, ...report.arrived], failure: null });
      } catch (error) {
        // Sans réseau : cas prévu, la file reste intacte et repartira à l'événement `online`.
        if (!(error instanceof NetworkError)) {
          patch({ failure: error instanceof Error ? error.message : String(error) });
          throw error;
        }
      } finally {
        await refresh(shopId);
      }
    },
    waiting: async () =>
      deps.rights.enabledShops().length === 0 ? 0 : (await open()).outbox.waiting(),
    discard: async () => {
      if (deps.rights.enabledShops().length === 0) return 0;
      const lost = await (await open()).outbox.discardAll();
      patch({ pending: {}, rejected: {} });
      return lost;
    },
    watch: (shopId, target) => {
      if (!deps.rights.isEnabled(shopId)) return () => undefined; // V1 : rien n'est chargé
      const sync = () => {
        capture.syncNow(shopId).catch((error: unknown) => {
          // Erreur hors réseau : déjà dans `failure` (montrée par la bannière), et en console.
          console.error("Envoi de la file hors connexion impossible", error);
        });
      };
      target.addEventListener("online", sync);
      sync();
      return () => {
        target.removeEventListener("online", sync);
      };
    },
  };
  return capture;
}
