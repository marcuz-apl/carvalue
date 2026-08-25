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
          // Extract only the semantic version part (m.n.p), removing build suffix (-yymmddc)
          const baseVersion = raw.split("-")[0].trim();
          return baseVersion.startsWith("v") ? baseVersion : `v${baseVersion}`;
        }
      }
    } catch {
      // Continue to next candidate path
    }
  }

  return "v1.2.8";
}
