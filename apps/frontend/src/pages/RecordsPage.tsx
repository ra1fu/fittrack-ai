import { useQuery } from "@tanstack/react-query";
import { api } from "../shared/api/client";
import { Card } from "../shared/ui/card";
import { PageHeader } from "../shared/ui/page";
import { EmptyState, ErrorState, SkeletonGrid } from "../shared/ui/state";

export function RecordsPage() {
  const records = useQuery({ queryKey: ["personal-records"], queryFn: () => api.personalRecords().then((r) => r.data) });
  return (
    <>
      <PageHeader title="Records" description="Личные рекорды по упражнениям." />
      {records.isLoading ? <SkeletonGrid count={4} /> : null}
      {records.isError ? <ErrorState error={records.error} onRetry={() => records.refetch()} /> : null}
      {records.data?.length === 0 ? <EmptyState title="Рекордов пока нет" /> : null}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {records.data?.map((record) => (
          <Card key={String(record.id)}>
            <p className="text-sm font-semibold text-muted">{String(record.record_type)}</p>
            <p className="mt-2 text-2xl font-bold">{String(record.value)} {String(record.unit)}</p>
            <p className="text-sm text-muted">{String(record.achieved_at)}</p>
          </Card>
        ))}
      </div>
    </>
  );
}
