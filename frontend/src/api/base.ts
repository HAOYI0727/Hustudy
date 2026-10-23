// Vite replaces these inputs at build time; no credentials or runtime switching.
export function resolveApiBase(configured: string | undefined, production: boolean): string {
  const explicit = configured?.trim().replace(/\/+$/, "");
  return explicit || (production ? "/api/v1" : "http://127.0.0.1:8000/api/v1");
}
