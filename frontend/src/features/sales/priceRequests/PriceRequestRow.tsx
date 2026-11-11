import { useId, useState } from "react";
import { Check, X } from "lucide-react";
import type { PriceDecision, PriceRequest } from "../../../core/gateways/salesContract";
import { formatMoney } from "../../../shared/format";
import { Button } from "../../../shared/ui";
import { remainingText } from "./priceRequestText";

export interface PriceRequestRowProps {
  request: PriceRequest;
  sellerName: string;
  now: number;
  busy: boolean;
  onDecide: (decision: PriceDecision) => void;
}

const VERB: Record<PriceDecision, string> = { accept: "Accepter", refuse: "Refuser" };

/**
 * Une demande en attente (UC-VEN-03, étape 2) : article, prix demandé, prix minimum, vendeur,
 * temps restant ; « Accepter » / « Refuser » d'un appui, puis une confirmation légère.
 */
export function PriceRequestRow({
  request,
  sellerName,
  now,
  busy,
  onDecide,
}: PriceRequestRowProps) {
  const titleId = useId();
  const [asking, setAsking] = useState<PriceDecision | null>(null);
  const gap = request.min_price - request.requested_price;
  return (
    <li aria-labelledby={titleId} className="flex flex-col gap-2 px-4 py-3">
      <h2 id={titleId} className="m-0 break-words text-lead font-semibold text-text">
        {request.article_name}
      </h2>
      <dl className="m-0 grid grid-cols-2 gap-x-4 text-body text-text">
        <dt className="text-text-muted">Prix demandé</dt>
        <dd className="m-0 text-right font-semibold tabular-nums">
          {formatMoney(request.requested_price)}
        </dd>
        <dt className="text-text-muted">Prix minimum</dt>
        <dd className="m-0 text-right tabular-nums">{formatMoney(request.min_price)}</dd>
        <dt className="text-text-muted">Écart</dt>
        <dd className="m-0 text-right tabular-nums">{formatMoney(gap)}</dd>
        <dt className="text-text-muted">Vendeur</dt>
        <dd className="m-0 break-words text-right">{sellerName}</dd>
        <dt className="text-text-muted">Expire dans</dt>
        <dd className="m-0 text-right">{remainingText(request, now)}</dd>
      </dl>
      {asking === null ? (
        <div className="grid grid-cols-2 gap-4">
          <Button
            variant="secondary"
            icon={Check}
            fullWidth
            onClick={() => {
              setAsking("accept");
            }}
          >
            Accepter
          </Button>
          <Button
            variant="secondary"
            icon={X}
            fullWidth
            onClick={() => {
              setAsking("refuse");
            }}
          >
            Refuser
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <p className="m-0 text-body text-text">
            {asking === "accept"
              ? `Accepter ${formatMoney(request.requested_price)} pour ${request.article_name} ?`
              : `Refuser ${formatMoney(request.requested_price)} pour ${request.article_name} ?`}
          </p>
          <div className="grid grid-cols-2 gap-4">
            <Button
              variant={asking === "accept" ? "secondary" : "danger"}
              icon={asking === "accept" ? Check : X}
              fullWidth
              loading={busy}
              onClick={() => {
                onDecide(asking);
              }}
            >
              {`Oui, ${VERB[asking].toLowerCase()}`}
            </Button>
            <Button
              variant="ghost"
              fullWidth
              onClick={() => {
                setAsking(null);
              }}
            >
              Retour
            </Button>
          </div>
        </div>
      )}
    </li>
  );
}
