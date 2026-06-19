import { ReactNode } from "react";

export function SectionTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? <p className="text-xs font-black uppercase text-action">{eyebrow}</p> : null}
        <h2 className="text-lg font-black text-ink">{title}</h2>
        {description ? <p className="mt-1 text-sm font-medium text-muted">{description}</p> : null}
      </div>
      {action ? <div className="flex shrink-0 gap-2">{action}</div> : null}
    </div>
  );
}
