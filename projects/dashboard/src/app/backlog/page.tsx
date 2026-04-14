import { BacklogConsole } from "@/features/operator/backlog-console";

export const revalidate = 15;

type BacklogPageProps = {
  searchParams?:
    | Promise<{ status?: string | string[] | undefined }>
    | { status?: string | string[] | undefined };
};

function resolveStatus(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] ?? "ready" : value ?? "ready";
}

export default async function BacklogPage({ searchParams }: BacklogPageProps) {
  const resolvedSearchParams = (await searchParams) ?? {};
  return <BacklogConsole initialStatus={resolveStatus(resolvedSearchParams.status)} />;
}
