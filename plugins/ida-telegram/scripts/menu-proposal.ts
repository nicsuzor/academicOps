#!/usr/bin/env bun
/**
 * CLI runner for the Telegram Menu Proposal skill.
 * Discovers installed skills and workflows, retrieves usage metrics,
 * presents the proposal matrix, parses operator allocations, and
 * persists/syncs approved commands.
 */

import {
  discoverCandidates,
  formatProposalMatrix,
  parseAllocationReply,
  validateCustomCommand,
  persistBotCommands,
  type CandidateCommand,
  type PersonaAllocation,
} from "../src/telegram/proposal.js";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

async function main() {
  const args = process.argv.slice(2);
  const jsonOutput = args.includes("--json");

  // Read telemetry usage if provided via --telemetry <path>
  let telemetryUsage: Record<string, number> = {};
  const telemetryIdx = args.indexOf("--telemetry");
  if (telemetryIdx !== -1 && args[telemetryIdx + 1]) {
    const telemetryPath = resolve(args[telemetryIdx + 1]);
    if (existsSync(telemetryPath)) {
      try {
        telemetryUsage = JSON.parse(readFileSync(telemetryPath, "utf-8"));
      } catch (e) {
        console.error("Warning: Failed to parse telemetry JSON:", e);
      }
    }
  }

  // Discover all candidates across installed plugin roots and workflows
  const candidates = await discoverCandidates({ telemetryUsage });

  // Custom command addition if provided via --custom-command <json>
  const customCmdIdx = args.indexOf("--custom-command");
  if (customCmdIdx !== -1 && args[customCmdIdx + 1]) {
    try {
      const customSpec = JSON.parse(args[customCmdIdx + 1]);
      const val = validateCustomCommand(customSpec);
      if (!val.valid) {
        console.error(`Error validating custom command: ${val.error}`);
        process.exit(1);
      }
      if (val.commandSpec) {
        const spec = val.commandSpec;
        candidates.push({
          command: spec.command,
          description: spec.description,
          skill: spec.skill,
          type: "custom",
          usageCount: 0,
          currentAllocation: (customSpec.allocation as PersonaAllocation) || "both",
          bareAction: spec.bareAction,
        });
      }
    } catch (e) {
      console.error("Error parsing --custom-command JSON:", e);
      process.exit(1);
    }
  }

  // Parse allocations if provided via --allocations <string|json>
  let allocations: Record<string, PersonaAllocation> = {};
  for (const c of candidates) {
    allocations[c.command] = c.currentAllocation;
  }

  const allocIdx = args.indexOf("--allocations");
  if (allocIdx !== -1 && args[allocIdx + 1]) {
    const rawAlloc = args[allocIdx + 1];
    try {
      if (rawAlloc.trim().startsWith("{")) {
        allocations = parseAllocationReply(JSON.parse(rawAlloc), allocations);
      } else {
        allocations = parseAllocationReply(rawAlloc, allocations);
      }
    } catch {
      allocations = parseAllocationReply(rawAlloc, allocations);
    }

    for (const c of candidates) {
      if (allocations[c.command]) {
        c.currentAllocation = allocations[c.command];
      }
    }
  }

  // Persist if requested via --save <dir>
  const saveIdx = args.indexOf("--save");
  if (saveIdx !== -1 && args[saveIdx + 1]) {
    const saveDir = resolve(args[saveIdx + 1]);
    const primeCmds = candidates
      .filter((c) => c.currentAllocation === "prime" || c.currentAllocation === "both")
      .map((c) => ({ command: c.command, description: c.description }));
    const strategicCmds = candidates
      .filter((c) => c.currentAllocation === "strategic" || c.currentAllocation === "both")
      .map((c) => ({ command: c.command, description: c.description }));

    await persistBotCommands(saveDir, {
      prime: primeCmds,
      strategic: strategicCmds,
    });
    console.log(`Saved dynamic command configuration to ${saveDir}/commands.json`);
  }

  if (jsonOutput) {
    console.log(JSON.stringify(candidates, null, 2));
    return;
  }

  const matrix = formatProposalMatrix(candidates);
  console.log(matrix);
}

if (import.meta.main) {
  main().catch((err) => {
    console.error("Error running menu-proposal:", err);
    process.exit(1);
  });
}
