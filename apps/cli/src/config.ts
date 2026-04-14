/**
 * CLI configuration module.
 * Loads config from environment variables with sensible defaults.
 */

/** CLI configuration options. */
export interface CliConfig {
  /** Backend API base URL. */
  backendUrl: string;
  /** Enable verbose output. */
  verbose: boolean;
  /** API token for backend authentication. */
  apiToken?: string;
}

const DEFAULT_BACKEND_URL = "http://localhost:8000";

/**
 * Build CLI configuration from environment variables and optional overrides.
 * @param overrides - Partial config overrides (e.g., from CLI flags)
 */
export function getConfig(overrides: Partial<CliConfig> = {}): CliConfig {
  return {
    backendUrl: overrides.backendUrl ?? process.env.M2LA_BACKEND_URL ?? DEFAULT_BACKEND_URL,
    verbose: overrides.verbose ?? process.env.M2LA_VERBOSE === "true",
    apiToken: overrides.apiToken ?? process.env.M2LA_API_TOKEN ?? undefined,
  };
}
