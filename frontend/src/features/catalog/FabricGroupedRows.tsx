import { ChevronRight } from "lucide-react";
import type { ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { Button } from "../../shared/ui";
import { ArticleRows } from "./ArticleRows";
import type { CatalogRole } from "./catalogRights";
import { groupByFabric } from "./fabricGroups";

export interface FabricGroupedRowsProps {
  role: CatalogRole;
  items: readonly ArticleResponse[];
  onOpen: (articleId: string) => void;
  onOpenFabric: (fabric: string) => void;
}

/**
 * Liste des articles Textile groupée par tissu (design-system § 7.6) : un bloc par tissu (nom,
 * nombre de couleurs, « Voir le tissu »), ses couleurs dessous ; les articles sans tissu à la fin.
 */
export function FabricGroupedRows({ role, items, onOpen, onOpenFabric }: FabricGroupedRowsProps) {
  const groups = groupByFabric(items);
  const loose = groups.filter((group) => group.fabric === null).flatMap((group) => group.items);
  return (
    <>
      {groups.map((group) => {
        const fabric = group.fabric;
        if (fabric === null) return null;
        const count = group.items.length;
        return (
          <section key={fabric} aria-label={`Tissu ${fabric}`} className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="m-0 text-title-sm font-semibold text-text">
                {fabric}{" "}
                <span className="text-body font-normal text-text-muted">
                  · {count > 1 ? `${String(count)} couleurs` : "1 couleur"}
                </span>
              </h2>
              <Button
                variant="ghost"
                icon={ChevronRight}
                onClick={() => {
                  onOpenFabric(fabric);
                }}
              >
                Voir le tissu {fabric}
              </Button>
            </div>
            <ArticleRows
              role={role}
              label={`Couleurs de ${fabric}`}
              items={group.items}
              onOpen={onOpen}
            />
          </section>
        );
      })}
      {loose.length > 0 && (
        <ArticleRows role={role} label="Autres articles" items={loose} onOpen={onOpen} />
      )}
    </>
  );
}
