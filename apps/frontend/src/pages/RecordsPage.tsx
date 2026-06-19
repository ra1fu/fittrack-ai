import { useQuery } from "@tanstack/react-query";
import { Medal, Trophy } from "lucide-react";
import { api } from "../shared/api/client";
import { Badge } from "../shared/ui/badge";
import { Card } from "../shared/ui/card";
import { PageHeader } from "../shared/ui/page";
import { EmptyState, ErrorState, SkeletonGrid } from "../shared/ui/state";

export function RecordsPage() {
  const records = useQuery({ queryKey: ["personal-records"], queryFn: () => api.personalRecords().then((r) => r.data) });
  return (
    <>
      <PageHeader title="Records" description="Личные рекорды по упражнениям." />
      <Card className="mb-4 bg-ink text-white">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-black uppercase text-[#9fd5ba]">Personal bests</p>
            <h2 className="text-2xl font-black">Рекорды</h2>
            <p className="mt-1 text-sm font-medium text-white/65">Следите за лучшими подходами и прогрессом силы.</p>
          </div>
          <Trophy className="h-8 w-8 text-[#9fd5ba]" aria-hidden />
        </div>
      </Card>
      {records.isLoading ? <SkeletonGrid count={4} /> : null}
      {records.isError ? <ErrorState error={records.error} onRetry={() => records.refetch()} /> : null}
      {records.data?.length === 0 ? <EmptyState title="Рекордов пока нет" /> : null}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {records.data?.map((record) => (
          <Card key={String(record.id)} className="transition hover:-translate-y-0.5 hover:shadow-lift">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-md bg-[#f2e5ce] text-amber">
                <Medal className="h-5 w-5" aria-hidden />
              </div>
              <Badge tone={record.is_current ? "success" : "neutral"}>
                {record.is_current ? "current" : "history"}
              </Badge>
            </div>
            <p className="text-sm font-bold text-muted">{String(record.record_type)}</p>
            <p className="mt-2 text-3xl font-black">{String(record.value)} {String(record.unit)}</p>
            <p className="text-sm font-medium text-muted">{String(record.achieved_at)}</p>
          </Card>
        ))}
      </div>
    </>
  );
}
