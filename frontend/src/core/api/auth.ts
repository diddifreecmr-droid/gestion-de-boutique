/** Routes d'authentification (specs § 6.3), typées par le contrat généré. */
import type { ApiClient } from "./client";
import type { ChangePinRequest, LoginRequest, MeResponse, TokenResponse } from "./types";

export interface AuthApi {
  login(body: LoginRequest): Promise<TokenResponse>;
  /** Le cookie httpOnly porte le jeton de rafraîchissement : aucun corps. */
  refresh(): Promise<TokenResponse>;
  logout(): Promise<void>;
  changePin(token: string, body: ChangePinRequest): Promise<void>;
  me(token: string): Promise<MeResponse>;
}

export function createAuthApi(client: ApiClient): AuthApi {
  return {
    login: (body) => client.post("/api/v1/auth/login", { body }),
    refresh: () => client.post("/api/v1/auth/refresh"),
    logout: async () => {
      await client.post("/api/v1/auth/logout");
    },
    changePin: async (token, body) => {
      await client.post("/api/v1/auth/change-pin", { token, body });
    },
    me: (token) => client.get("/api/v1/me", { token }),
  };
}
