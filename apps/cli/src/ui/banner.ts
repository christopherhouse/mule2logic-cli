import chalk from "chalk";

export function showBanner(): void {
  const divider = chalk.gray("─".repeat(58));

  console.log();
  console.log(divider);
  console.log();
  console.log(
    chalk.bold.cyan("  🔄  ") +
      chalk.bold.white("MuleSoft → Logic Apps Standard") +
      chalk.bold.cyan("  Migration Tool"),
  );
  console.log();
  console.log(chalk.gray("  Powered by Azure • AI-Assisted • Production-Ready"));
  console.log();
  console.log(divider);
  console.log();
  console.log(chalk.yellow("  📋  Migration Stages:"));
  console.log(chalk.white("      🔍  Analyzing project / flow"));
  console.log(chalk.white("      🧠  Planning migration"));
  console.log(chalk.white("      ⚙️   Converting flows"));
  console.log(chalk.white("      ✅  Validating output"));
  console.log();
  console.log(
    chalk.dim("  Run ") + chalk.green("mule2logic --help") + chalk.dim(" to get started"),
  );
  console.log();
  console.log(divider);
  console.log();
}
