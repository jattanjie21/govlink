/**
 * Public-facing API URL — used in displayed snippets, "Open Swagger"
 * links, and error copy.
 *
 * NOT used for actual axios calls — those go through the relative
 * `/api` prefix and the Vite proxy (or production reverse proxy).
 *
 * Set `VITE_API_PUBLIC_URL` to override (e.g. https://api.govlink.gm
 * in production). Falls back to localhost so dev "just works".
 */
export const API_PUBLIC_URL =
  import.meta.env.VITE_API_PUBLIC_URL ?? "http://localhost:8000";
