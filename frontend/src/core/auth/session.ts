/**
 * Session (specs § 7.2, § 8.1) : jeton d'accès **en mémoire seulement**, rafraîchissement
 * **single-flight** puis rejeu, fin de session propre vers l'écran de connexion.
 */
import { ApiError } from "../api/errors";
import type { AuthApi } from "../api/auth";
import type { ChangePinRequest, TokenResponse } from "../api/types";
import { createStore, type Store } from "../state/store";
import { parseMe } from "./me";
import { singleFlight } from "./singleFlight";
import { endNotice, endsSession, SessionEndedError, type SessionState } from "./sessionState";

/** Le jeton est rafraîchi avant son expiration quand il lui reste moins de 30 s. */
export const REFRESH_MARGIN_MS = 30_000;

export interface Credentials {
  phone: string;
  secret: string;
  /** Code à 6 chiffres (membre) ou mot de passe (administrateur plateforme). */
  kind: "pin" | "password";
}

interface AccessToken {
  value: string;
  expiresAt: number;
}

export class Session {
  readonly state: Store<SessionState> = createStore<SessionState>({ status: "restoring" });
  private token: AccessToken | null = null;
  private restoring: Promise<void> | null = null;
  private readonly refreshOnce = singleFlight(() => this.rotate());

  constructor(
    private readonly api: AuthApi,
    private readonly deviceLabel: string,
    private readonly now: () => number = Date.now,
  ) {}

  /** Au chargement : restaure la session de l'appareil sans rien demander. */
  restore(): Promise<void> {
    this.restoring ??= this.runRestore();
    return this.restoring;
  }

  /** Après un échec de restauration (réseau, serveur) : nouvelle tentative. */
  retryRestore(): Promise<void> {
    this.restoring = null;
    this.state.set({ status: "restoring" });
    return this.restore();
  }

  async login({ phone, secret, kind }: Credentials): Promise<void> {
    const proof = kind === "pin" ? { pin: secret } : { password: secret };
    this.accept(await this.api.login({ phone, device_label: this.deviceLabel, ...proof }));
    await this.loadMe();
  }

  /** Déconnexion volontaire ; un 401 (session déjà close côté serveur) n'empêche pas de sortir. */
  async logout(): Promise<void> {
    try {
      await this.api.logout();
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 401)) throw error;
    }
    this.signOut(null);
  }

  async changePin(body: ChangePinRequest): Promise<void> {
    // Code actuel faux : 422 CURRENT_PIN_INVALID (pas 401), la session reste ouverte.
    await this.authorized((token) => this.api.changePin(token, body));
    await this.loadMe();
  }

  /** Appel authentifié : jeton valide, puis sur 401 un seul refresh partagé et un rejeu. */
  async authorized<T>(call: (token: string) => Promise<T>): Promise<T> {
    const token = await this.validToken();
    try {
      return await call(token);
    } catch (error) {
      this.notePinChange(error);
      const expired = error instanceof ApiError && error.status === 401;
      if (!expired) throw error;
      if (error.code === "SESSION_REVOKED") throw this.end(error);
      const fresh = await this.refreshAfter(token);
      try {
        return await call(fresh);
      } catch (replayError) {
        this.notePinChange(replayError);
        if (endsSession(replayError)) throw this.end(replayError);
        throw replayError;
      }
    }
  }

  private async runRestore(): Promise<void> {
    try {
      await this.refreshOnce();
      await this.loadMe();
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        this.signOut(endNotice(error, true));
      } else if (error instanceof SessionEndedError) {
        return; // l'état « déconnecté » est déjà posé par end()
      } else if (error instanceof Error) {
        // Réseau, serveur, stockage de l'appareil : affiché avec « Réessayer », jamais masqué.
        this.state.set({ status: "failed", error });
      } else {
        throw error;
      }
    }
  }

  private async loadMe(): Promise<void> {
    const me = parseMe(await this.authorized((token) => this.api.me(token)));
    this.state.set({ status: "signedIn", me });
  }

  private async rotate(): Promise<void> {
    this.accept(await this.api.refresh());
  }

  private accept(response: TokenResponse): void {
    const expiresAt = Date.parse(response.expires_at);
    if (response.access_token === "" || Number.isNaN(expiresAt)) {
      throw new Error("Réponse de session invalide : jeton ou expiration illisible");
    }
    this.token = { value: response.access_token, expiresAt };
  }

  private async validToken(): Promise<string> {
    // Session fermée (déconnexion, révocation) : aucun jeton, plus aucun appel authentifié.
    // Pendant une connexion, l'état est encore « déconnecté » mais le jeton vient d'arriver.
    if (this.token === null && this.state.get().status === "signedOut") {
      throw new SessionEndedError();
    }
    const current = this.token;
    if (current !== null && current.expiresAt - this.now() > REFRESH_MARGIN_MS) {
      return current.value;
    }
    return this.refreshAfter(current?.value ?? null);
  }

  /** Refresh partagé ; si un autre appel a déjà tourné le jeton, on réutilise le nouveau. */
  private async refreshAfter(stale: string | null): Promise<string> {
    if (this.token !== null && this.token.value !== stale) return this.token.value;
    try {
      await this.refreshOnce();
    } catch (error) {
      if (endsSession(error)) throw this.end(error);
      throw error;
    }
    if (this.token === null) throw new SessionEndedError();
    return this.token.value;
  }

  /** `PIN_CHANGE_REQUIRED` : l'écran de changement de code s'impose (garde de route). */
  private notePinChange(error: unknown): void {
    const state = this.state.get();
    if (!(error instanceof ApiError) || error.code !== "PIN_CHANGE_REQUIRED") return;
    if (state.status === "signedIn") {
      this.state.set({ status: "signedIn", me: { ...state.me, mustChangePin: true } });
    }
  }

  private end(error: ApiError): SessionEndedError {
    const notice = endNotice(error, this.state.get().status === "restoring");
    this.signOut(notice);
    return new SessionEndedError(notice ?? error.message);
  }

  private signOut(notice: string | null): void {
    this.token = null;
    this.state.set({ status: "signedOut", notice });
  }
}
