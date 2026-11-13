import { useState } from "react";
import { ArrowLeft, FileText, Pencil, RefreshCw, ShoppingCart } from "lucide-react";
import { useNavigate } from "react-router";
import type { CustomerSale } from "../../core/gateways/customersContract";
import { useCustomersGateway } from "../../core/gateways/httpCustomers";
import { useModules } from "../../core/profile/modulesContext";
import { shopPath } from "../../core/profile/shopProfile";
import { formatDate, formatMoney } from "../../shared/format";
import {
  Badge,
  Button,
  EmptyState,
  KpiCard,
  ListCard,
  ListCardRow,
  Skeleton,
} from "../../shared/ui";
import { useLoad } from "../expenses/useLoad";
import { RECEIVABLES_KEY, VIEW as RECEIVABLE_VIEW } from "../receivables/receivablesNav";
import { SALES_KEY } from "../sales/salesNav";
import { customerLine } from "./customerFields";
import type { CustomerNav } from "./customersNav";

function saleBadge(sale: CustomerSale, credit: boolean) {
  if (sale.status === "cancelled") return <Badge status="danger">Annulée</Badge>;
  if (credit && sale.remaining > 0)
    return <Badge status="credit">{`Reste ${formatMoney(sale.remaining)}`}</Badge>;
  return undefined;
}

/**
 * Fiche client (UC-VEN-11, CUS-01) : coordonnées, total acheté, total dû, historique des ventes ;
 * le relevé des créances s'ouvre dans « Créances ». Montants de vente seulement (aucun coût).
 * Sans le module Créances : ni total dû, ni reste, ni relevé (specs § 15.1).
 */
export function CustomerSheet({
  shopId,
  id,
  nav,
}: {
  shopId: string;
  id: string;
  nav: CustomerNav;
}) {
  const gateway = useCustomersGateway();
  const navigate = useNavigate();
  const credit = useModules().has("receivables");
  const [round, setRound] = useState(0);
  const sheet = useLoad(`${id}|${String(round)}`, () => gateway.sheet(shopId, id));
  const back = (
    <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
      Retour aux clients
    </Button>
  );
  if (sheet.status === "loading") {
    return (
      <>
        {back}
        <Skeleton lines={4} label="Chargement de la fiche…" />
      </>
    );
  }
  if (sheet.status === "offline") {
    return (
      <>
        {back}
        <EmptyState
          message="Connexion nécessaire pour afficher la fiche."
          action={
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={() => {
                setRound((n) => n + 1);
              }}
            >
              Réessayer
            </Button>
          }
        />
      </>
    );
  }
  const { customer, total_bought, total_due, sales } = sheet.value;
  const details = [customerLine(customer), customer.address, customer.note].filter(
    (part): part is string => part !== null && part !== "",
  );
  return (
    <>
      {back}
      <div className="flex flex-col items-start gap-2">
        <h1 className="m-0 break-words text-title font-bold text-text">{customer.name}</h1>
        {customer.kind === "company" && <Badge status="success">Entreprise</Badge>}
        {details.map((part) => (
          <p key={part} className="m-0 break-words text-body text-text-muted">
            {part}
          </p>
        ))}
      </div>
      <KpiCard label="Total acheté" amount={total_bought} />
      {credit && (
        <>
          <KpiCard label="Total dû" amount={total_due} />
          <Button
            variant="secondary"
            icon={FileText}
            fullWidth
            onClick={() =>
              void navigate(
                `${shopPath(shopId, RECEIVABLES_KEY)}?vue=${RECEIVABLE_VIEW.statement}&client=${encodeURIComponent(id)}`,
              )
            }
          >
            Relevé des créances
          </Button>
        </>
      )}
      {sales.length === 0 ? (
        <EmptyState icon={ShoppingCart} message="Aucune vente pour ce client." />
      ) : (
        <ListCard label={`Ventes de ${customer.name}`}>
          {sales.map((sale) => (
            <ListCardRow
              key={sale.id}
              title={sale.number}
              subtitle={formatDate(sale.sold_on)}
              amount={sale.total}
              badge={saleBadge(sale, credit)}
              cancelled={sale.status === "cancelled"}
              onOpen={() =>
                void navigate(`${shopPath(shopId, SALES_KEY)}?id=${encodeURIComponent(sale.id)}`)
              }
            />
          ))}
        </ListCard>
      )}
      <Button
        variant="secondary"
        icon={Pencil}
        fullWidth
        onClick={() => {
          nav.edit(id);
        }}
      >
        Modifier le client
      </Button>
    </>
  );
}
