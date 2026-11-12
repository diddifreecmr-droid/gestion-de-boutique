import type { AuditEntry } from "../../core/gateways/journalContract";
import { Badge, Disclosure } from "../../shared/ui";
import { changeValue, entryMoment, entrySentence, moduleLabel, type People } from "./journalText";

/**
 * Une entrée du journal (lecture seule) : moment, phrase, module. Une action **sensible**
 * (annulation, prix, vente sous le minimum, ajustement, droits — AUD-02) porte la pastille
 * « Sensible » et un trait rouge à gauche ; motif et changements avant/après sous la phrase.
 */
export function JournalRow({ entry, people }: { entry: AuditEntry; people: People }) {
  const frame = entry.sensitive ? "border-l-4 border-danger" : "";
  return (
    <li className={`flex flex-col gap-2 p-4 ${frame}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-body text-text-muted">{entryMoment(entry)}</span>
        <span className="text-body text-text-muted">· {moduleLabel(entry.module)}</span>
        {entry.sensitive && <Badge status="danger">Sensible</Badge>}
      </div>
      <p className="m-0 break-words text-body text-text">{entrySentence(entry, people)}</p>
      {entry.reason !== null && (
        <p className="m-0 break-words text-body text-text-muted">Motif : {entry.reason}</p>
      )}
      {entry.changes.length > 0 && (
        <Disclosure label="Voir les changements">
          <ul aria-label="Changements" className="m-0 flex list-none flex-col gap-1 p-0">
            {entry.changes.map((change) => (
              <li key={change.field} className="break-words text-body text-text">
                {change.field} : {changeValue(change.before)} → {changeValue(change.after)}
              </li>
            ))}
          </ul>
        </Disclosure>
      )}
    </li>
  );
}
