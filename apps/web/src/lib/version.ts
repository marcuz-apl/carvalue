import fs from "fs";
import path from "path";

/**
 * Dynamically resolves the current repository version from the root VERSION file.
 * Automatically tracks commit version bumps driven by .githooks/pre-commit.
 */
export function getAppVersion(): string {
  const candidatePaths = [
    path.resolve(process.cwd(), "VERSION"),
    path.resolve(process.cwd(), "../../VERSION"),
    path.resolve(process.cwd(), "../VERSION"),
  ];

  for (const p of candidatePaths) {
    try {
      if (fs.existsSync(p)) {
        const raw = fs.readFileSync(p, "utf-8").trim();
        if (raw) {
          return raw.startsWith("v") ? raw : `v${raw}`;
        }
      }
    } catch {
      // Continue to next candidate path
    }
  }

  return "v1.2.7";
}
