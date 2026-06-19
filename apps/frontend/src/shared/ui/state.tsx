import { AlertCircle, Inbox, RefreshCw } from "lucide-react";
import { Button } from "./button";
import { Card } from "./card";

export function SkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="h-28 animate-pulse rounded-lg border border-line bg-white/80 shadow-soft" />
      ))}
    </div>
  );
}

export function EmptyState({ title, text }: { title: string; text?: string }) {
  return (
    <Card className="border-dashed bg-[#fbfaf6] text-center">
      <div className="mx-auto mb-3 grid h-11 w-11 place-items-center rounded-md bg-oat text-steel">
        <Inbox className="h-5 w-5" aria-hidden />
      </div>
      <h3 className="text-base font-bold">{title}</h3>
      {text ? <p className="mt-1 text-sm text-muted">{text}</p> : null}
    </Card>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Что-то пошло не так.";
  return (
    <Card className="border-coral/30 bg-[#fff6f2]">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 text-coral" aria-hidden />
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-ink">Не удалось загрузить данные</h3>
          <p className="mt-1 text-sm text-muted">{message}</p>
          {onRetry ? (
            <Button className="mt-3" variant="secondary" onClick={onRetry}>
              <RefreshCw className="h-4 w-4" aria-hidden />
              Повторить
            </Button>
          ) : null}
        </div>
      </div>
    </Card>
  );
}
