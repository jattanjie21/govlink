import { useOutletContext } from "react-router-dom";
import type { DatasetDetail, DatasetHealth } from "@/lib/types";

export interface DatasetOutletContext {
  slug: string;
  dataset: DatasetDetail;
  freshness: DatasetHealth | undefined;
}

export function useDatasetContext(): DatasetOutletContext {
  return useOutletContext<DatasetOutletContext>();
}
