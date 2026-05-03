import { useMemo, useState } from "react";
import { Copy, Send } from "lucide-react";
import { useDatasetContext } from "./context";
import { api, ApiError } from "@/lib/api";
import { API_PUBLIC_URL } from "@/lib/env";
import { cn } from "@/lib/utils";

type EndpointKey = "metadata" | "latest" | "historical" | "csv";
type Lang = "curl" | "python" | "javascript" | "r";

interface EndpointDef {
  key: EndpointKey;
  method: "GET";
  /** Path template, with `:slug` placeholder. */
  pathTemplate: string;
  title: string;
  description: string;
  params: ParamDef[];
}

interface ParamDef {
  name: string;
  /** Placeholder + input type hint. */
  type: "date" | "string" | "number";
  required?: boolean;
  hint?: string;
  defaultValue?: string;
}

const ENDPOINTS: ReadonlyArray<EndpointDef> = [
  {
    key: "metadata",
    method: "GET",
    pathTemplate: "/datasets/:slug",
    title: "Dataset metadata",
    description: "Returns the dataset's identifying metadata and field schema.",
    params: [],
  },
  {
    key: "latest",
    method: "GET",
    pathTemplate: "/datasets/:slug/latest",
    title: "Latest snapshot",
    description: "Every record from the most recent snapshot_date.",
    params: [],
  },
  {
    key: "historical",
    method: "GET",
    pathTemplate: "/datasets/:slug/historical",
    title: "Historical records",
    description: "Paginated history. Filter by date range and (where supported) currency.",
    params: [
      { name: "from", type: "date", hint: "YYYY-MM-DD" },
      { name: "to", type: "date", hint: "YYYY-MM-DD" },
      { name: "currency", type: "string", hint: "USD, EUR, …" },
      { name: "limit", type: "number", defaultValue: "100", hint: "1–1000" },
      { name: "offset", type: "number", defaultValue: "0", hint: "≥0" },
    ],
  },
  {
    key: "csv",
    method: "GET",
    pathTemplate: "/datasets/:slug/csv",
    title: "CSV export",
    description: "Streams a CSV with the same filters as historical (no pagination).",
    params: [
      { name: "from", type: "date", hint: "YYYY-MM-DD" },
      { name: "to", type: "date", hint: "YYYY-MM-DD" },
      { name: "currency", type: "string", hint: "USD, EUR, …" },
    ],
  },
];

interface SendResult {
  status: number;
  durationMs: number;
  bodyText: string;
  ok: boolean;
}

export default function Api() {
  const { slug, dataset } = useDatasetContext();
  const supportsCurrency = useMemo(
    () => dataset.fields.some((f) => f.name === "currency_code"),
    [dataset.fields],
  );

  const [activeKey, setActiveKey] = useState<EndpointKey>("historical");
  const [paramValues, setParamValues] = useState<Record<string, string>>({});
  const [response, setResponse] = useState<SendResult | null>(null);
  const [sending, setSending] = useState(false);
  const [lang, setLang] = useState<Lang>("curl");

  const endpoint = ENDPOINTS.find((e) => e.key === activeKey)!;
  const visibleParams = endpoint.params.filter(
    (p) => p.name !== "currency" || supportsCurrency,
  );
  const path = endpoint.pathTemplate.replace(":slug", slug);
  const queryString = buildQueryString(visibleParams, paramValues);
  const fullPath = path + (queryString ? `?${queryString}` : "");
  const fullUrl = `${API_PUBLIC_URL}${fullPath}`;

  function setParam(name: string, value: string) {
    setParamValues((prev) => ({ ...prev, [name]: value }));
  }

  async function send() {
    setSending(true);
    setResponse(null);
    const started = performance.now();
    try {
      // CSV is text, JSON otherwise. Use raw axios so we can capture
      // status/timing even on non-2xx without going through ApiError.
      const res = await api.get(fullPath, { responseType: "text" });
      setResponse({
        status: res.status,
        durationMs: Math.round(performance.now() - started),
        bodyText: prettyJsonIfPossible(res.data),
        ok: true,
      });
    } catch (err) {
      const status =
        err instanceof ApiError ? err.status : 0;
      setResponse({
        status,
        durationMs: Math.round(performance.now() - started),
        bodyText:
          err instanceof ApiError
            ? JSON.stringify(
                {
                  error: {
                    code: err.code,
                    message: err.message,
                    details: err.details ?? null,
                  },
                },
                null,
                2,
              )
            : String(err),
        ok: false,
      });
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-10">
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        {/* Endpoints sidebar */}
        <aside>
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
            Endpoints
          </p>
          <ul className="space-y-1">
            {ENDPOINTS.map((e) => (
              <li key={e.key}>
                <button
                  type="button"
                  onClick={() => {
                    setActiveKey(e.key);
                    setResponse(null);
                  }}
                  className={cn(
                    "flex w-full items-center gap-2 rounded border border-rule px-2.5 py-2 text-left text-xs transition-colors duration-2 ease",
                    e.key === activeKey
                      ? "border-rule-2 bg-accent-tint text-ink"
                      : "bg-surface text-ink-2 hover:border-rule-2 hover:text-ink",
                  )}
                >
                  <span className="rounded bg-accent-tint px-1.5 py-0.5 font-mono text-[10px] font-semibold text-accent">
                    GET
                  </span>
                  <span className="truncate font-mono text-[11px]">
                    {e.pathTemplate.replace(":slug", slug)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* Main */}
        <div className="space-y-6 min-w-0">
          {/* Endpoint head */}
          <header className="rounded-lg border border-rule bg-surface p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-display text-lg font-normal leading-tight tracking-tight">
                  {endpoint.title}
                </h2>
                <p className="mt-1 text-sm text-ink-2">{endpoint.description}</p>
              </div>
              <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2 rounded border border-rule bg-canvas px-3 py-1.5 font-mono text-xs">
                <span className="shrink-0 rounded bg-accent-tint px-1.5 py-0.5 text-[10px] font-semibold text-accent">
                  GET
                </span>
                <span className="min-w-0 break-all text-ink">{fullUrl}</span>
              </div>
            </div>
          </header>

          {/* Param builder */}
          <div className="rounded-lg border border-rule bg-surface">
            <header className="flex items-center justify-between border-b border-rule px-5 py-3 text-xs">
              <span className="font-semibold uppercase tracking-[0.12em] text-ink-3">
                Parameters
              </span>
              <span className="text-ink-3">
                {visibleParams.length} {visibleParams.length === 1 ? "param" : "params"}
              </span>
            </header>
            <div className="divide-y divide-rule">
              {visibleParams.length === 0 && (
                <p className="px-5 py-6 text-sm text-ink-3">
                  No parameters for this endpoint.
                </p>
              )}
              {visibleParams.map((p) => (
                <div
                  key={p.name}
                  className="grid grid-cols-1 gap-2 px-5 py-3 sm:grid-cols-[160px_1fr]"
                >
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-ink">{p.name}</span>
                    {!p.required && (
                      <span className="rounded-[2px] border border-rule bg-surface-2 px-1 py-0.5 text-[10px] font-sans text-ink-3">
                        opt
                      </span>
                    )}
                  </div>
                  <input
                    type={p.type === "date" ? "date" : p.type === "number" ? "number" : "text"}
                    value={paramValues[p.name] ?? ""}
                    placeholder={p.hint ?? ""}
                    onChange={(e) => setParam(p.name, e.target.value)}
                    className="w-full rounded border border-rule bg-canvas px-2.5 py-1.5 font-mono text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                  />
                </div>
              ))}
            </div>
            <div className="flex items-center justify-between border-t border-rule px-5 py-3">
              <span className="text-xs text-ink-3">
                {sending ? "Sending…" : response ? `Last response · ${response.durationMs} ms` : "Click Send to fire the request."}
              </span>
              <button
                type="button"
                onClick={send}
                disabled={sending}
                className="inline-flex items-center gap-2 rounded bg-accent px-3 py-1.5 text-xs font-medium text-white transition-colors duration-2 ease hover:bg-accent-hover disabled:opacity-60"
              >
                <Send className="h-3 w-3" />
                Send request
              </button>
            </div>
          </div>

          {/* Response */}
          {response && (
            <div className="rounded-lg border border-rule bg-surface">
              <header className="flex items-center justify-between border-b border-rule px-5 py-3 text-xs">
                <span className="flex items-center gap-2 font-semibold uppercase tracking-[0.12em] text-ink-3">
                  Response
                  <span
                    className={cn(
                      "rounded-[2px] px-1.5 py-0.5 font-sans text-[10px]",
                      response.ok
                        ? "bg-success/15 text-success"
                        : "bg-danger/15 text-danger",
                    )}
                  >
                    {response.status} {statusLabel(response.status)}
                  </span>
                </span>
                <span className="text-ink-3 num">{response.durationMs} ms · {byteSize(response.bodyText)}</span>
              </header>
              <pre className="max-h-[480px] overflow-auto bg-[var(--code-bg)] p-5 font-mono text-xs leading-relaxed text-[var(--code-fg)]">
                {response.bodyText}
              </pre>
            </div>
          )}

          {/* Snippets */}
          <div className="rounded-lg border border-rule bg-surface">
            <header className="flex items-center justify-between border-b border-rule px-5 py-3">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-3">
                Code
              </span>
              <div className="flex gap-1">
                {(["curl", "python", "javascript", "r"] as Lang[]).map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => setLang(l)}
                    className={cn(
                      "rounded px-2.5 py-1 text-xs font-mono transition-colors duration-2 ease",
                      l === lang
                        ? "bg-accent-tint text-accent"
                        : "text-ink-3 hover:text-ink",
                    )}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </header>
            <div className="relative">
              <button
                type="button"
                onClick={() => copy(buildSnippet(lang, fullUrl))}
                className="absolute right-3 top-3 inline-flex items-center gap-1 rounded border border-[var(--code-fg)]/20 bg-[var(--code-bg)]/80 px-2 py-1 text-[10px] text-[var(--code-fg)]/80 hover:text-[var(--code-fg)]"
                aria-label="Copy snippet"
              >
                <Copy className="h-3 w-3" />
                Copy
              </button>
              <pre className="overflow-x-auto bg-[var(--code-bg)] p-5 pr-20 font-mono text-xs leading-relaxed text-[var(--code-fg)]">
                {buildSnippet(lang, fullUrl)}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function buildQueryString(params: ParamDef[], values: Record<string, string>): string {
  const usp = new URLSearchParams();
  for (const p of params) {
    const v = (values[p.name] ?? p.defaultValue ?? "").trim();
    if (v) usp.set(p.name, v);
  }
  return usp.toString();
}

function buildSnippet(lang: Lang, url: string): string {
  switch (lang) {
    case "curl":
      return `curl '${url}'`;
    case "python":
      return `import httpx\n\nres = httpx.get("${url}")\nres.raise_for_status()\ndata = res.json()`;
    case "javascript":
      return `const res = await fetch("${url}");\nif (!res.ok) throw new Error(res.statusText);\nconst data = await res.json();`;
    case "r":
      return `library(httr)\nlibrary(jsonlite)\n\nres <- GET("${url}")\nstop_for_status(res)\ndata <- fromJSON(content(res, "text"))`;
  }
}

function prettyJsonIfPossible(text: string): string {
  if (typeof text !== "string") return JSON.stringify(text, null, 2);
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return text;
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

function statusLabel(s: number): string {
  if (s === 0) return "Error";
  if (s >= 200 && s < 300) return "OK";
  if (s === 404) return "Not Found";
  if (s === 422) return "Unprocessable";
  if (s === 429) return "Rate Limited";
  if (s >= 500) return "Server Error";
  return "";
}

function byteSize(text: string): string {
  const bytes = new Blob([text]).size;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    /* clipboard may be denied; silently ignore */
  }
}
