import type {
  AccountantHome,
  DriverHome,
  Home,
  SellerHome,
} from "../../core/gateways/reportingContract";
import type { Loaded } from "../expenses/useLoad";
import { useFigures, useReporting } from "./reportingContext";

interface Blocks {
  seller: SellerHome;
  accountant: AccountantHome;
  driver: DriverHome;
}

export type HomeRole = keyof Blocks;

/** Bloc du rôle ; un rôle différent ou un bloc absent est une erreur de contrat (fail-fast). */
export function homeBlock<R extends HomeRole>(home: Home, role: R): Blocks[R] {
  if (home.role !== role) throw new Error(`Accueil « ${home.role} » reçu pour « ${role} »`);
  const block: unknown = home[role];
  if (block === null || block === undefined) throw new Error(`Accueil « ${role} » sans son bloc`);
  return block as Blocks[R];
}

/** `GET /home` (UC-TDB-05) : le bloc de son rôle, jamais affiché hors connexion (RG-T25). */
export function useHome<R extends HomeRole>(
  shopId: string,
  role: R,
): { loaded: Loaded<Blocks[R]>; retry: () => void } {
  const { gateway } = useReporting();
  return useFigures(`home:${shopId}:${role}`, async () =>
    homeBlock(await gateway.home(shopId), role),
  );
}
