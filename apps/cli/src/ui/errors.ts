/**
 * Structured CLI error types and global error handler.
 */
import chalk from "chalk";

/** Structured CLI error with code, message, and optional suggestion. */
export class CliError extends Error {
  /** Machine-readable error code. */
  readonly code: string;
  /** Optional suggestion for the user to fix the issue. */
  readonly suggestion?: string;

  constructor(code: string, message: string, suggestion?: string) {
    super(message);
    this.name = "CliError";
    this.code = code;
    this.suggestion = suggestion;
  }
}

/**
 * Global error handler for the CLI.
 * Formats errors with chalk styling and exits with appropriate code.
 */
export function handleError(error: unknown): never {
  if (error instanceof CliError) {
    console.error();
    console.error(chalk.red(`  ❌  Error [${error.code}]: ${error.message}`));
    if (error.suggestion) {
      console.error(chalk.yellow(`  💡  Hint: ${error.suggestion}`));
    }
    console.error();
    process.exit(1);
  }

  if (error instanceof Error) {
    console.error();
    console.error(chalk.red(`  ❌  Unexpected error: ${error.message}`));
    console.error();
    process.exit(1);
  }

  console.error();
  console.error(chalk.red("  ❌  An unknown error occurred"));
  console.error();
  process.exit(1);
}
