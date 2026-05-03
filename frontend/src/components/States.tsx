import type { ReactNode } from "react";
import { ApiError } from "@/lib/api";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-rule bg-surface/40 px-6 py-16 text-center">
      <p className="font-display text-md">{title}</p>
      {description && (
        <p className="mx-auto mt-2 max-w-md text-sm text-ink-3">{description}</p>
      )}
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}

export function ErrorState({
  error,
  context,
}: {
  error: unknown;
  context?: string;
}) {
  if (error instanceof ApiError && error.isRateLimited) {
    return (
      <div className="rounded-lg border border-rule bg-surface px-6 py-10 text-center">
        <p className="font-display text-md">You're going fast.</p>
        <p className="mt-2 text-sm text-ink-3">
          The backend rate-limits {context ?? "this endpoint"} at 60 requests
          per minute. Wait a moment and refresh.
        </p>
      </div>
    );
  }

  if (error instanceof ApiError && error.isNotFound) {
    return (
      <div className="rounded-lg border border-rule bg-surface px-6 py-10 text-center">
        <p className="font-display text-md">Not found</p>
        <p className="mt-2 text-sm text-ink-3">{error.message}</p>
      </div>
    );
  }

  const msg =
    error instanceof ApiError
      ? `${error.code}: ${error.message}`
      : error instanceof Error
        ? error.message
        : String(error);

  return (
    <div className="rounded-lg border border-rule bg-surface px-6 py-10 text-center">
      <p className="font-display text-md text-danger">Something went wrong</p>
      <p className="mt-2 text-sm text-ink-3">{msg}</p>
      <p className="mt-1 text-xs text-ink-3">
        Check that the backend is reachable.
      </p>
    </div>
  );
}

export function LoadingCardGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-44 animate-pulse rounded-lg border border-rule bg-surface"
        />
      ))}
    </div>
  );
}
