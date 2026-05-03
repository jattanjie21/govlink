/**
 * TanStack Query hooks for every backend endpoint we use.
 *
 * Centralising here means pages don't repeat URLs or query keys, and
 * cache invalidation has one place to live.
 */

import { useQuery } from "@tanstack/react-query";
import { apiGet, apiGetEnvelope, apiGetRaw } from "./api";
import type {
  DatasetDetail,
  DatasetRecord,
  DatasetSummary,
  Envelope,
  HealthResponse,
  HistoricalParams,
} from "./types";

export const queryKeys = {
  datasets: ["datasets"] as const,
  dataset: (slug: string) => ["dataset", slug] as const,
  latest: (slug: string) => ["dataset", slug, "latest"] as const,
  historical: (slug: string, params: HistoricalParams) =>
    ["dataset", slug, "historical", params] as const,
  health: ["admin", "health"] as const,
};

export function useDatasets() {
  return useQuery({
    queryKey: queryKeys.datasets,
    queryFn: () => apiGet<DatasetSummary[]>("/datasets"),
  });
}

export function useDataset(slug: string | undefined) {
  return useQuery({
    queryKey: slug ? queryKeys.dataset(slug) : ["dataset", "_none"],
    queryFn: () => apiGet<DatasetDetail>(`/datasets/${slug}`),
    enabled: Boolean(slug),
  });
}

export function useDatasetLatest(slug: string | undefined) {
  return useQuery({
    queryKey: slug ? queryKeys.latest(slug) : ["dataset", "_none", "latest"],
    queryFn: () =>
      apiGetEnvelope<DatasetRecord[]>(`/datasets/${slug}/latest`),
    enabled: Boolean(slug),
  });
}

export function useDatasetHistorical(
  slug: string | undefined,
  params: HistoricalParams,
) {
  return useQuery<Envelope<DatasetRecord[]>>({
    queryKey: slug
      ? queryKeys.historical(slug, params)
      : ["dataset", "_none", "historical", params],
    queryFn: () =>
      apiGetEnvelope<DatasetRecord[]>(`/datasets/${slug}/historical`, {
        params: cleanParams(params as Record<string, unknown>),
      }),
    enabled: Boolean(slug),
    placeholderData: (prev) => prev, // keep prior page visible while paginating
  });
}

export function useHealth(refetchIntervalMs = 30_000) {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => apiGetRaw<HealthResponse>("/admin/health"),
    refetchInterval: refetchIntervalMs,
  });
}

function cleanParams<T extends Record<string, unknown>>(p: T): Partial<T> {
  const out: Partial<T> = {};
  (Object.keys(p) as Array<keyof T>).forEach((k) => {
    const v = p[k];
    if (v === undefined || v === null || v === "") return;
    out[k] = v;
  });
  return out;
}
