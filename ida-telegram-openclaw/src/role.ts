import { existsSync, readFileSync, writeFileSync, unlinkSync, mkdirSync } from "node:fs";
import { join } from "node:path";

export interface RoleCheckResult {
  role: string;
  isPrimary: boolean;
}

export function checkRole(env: NodeJS.ProcessEnv = process.env): RoleCheckResult {
  const role = (env.IDA_TELEGRAM_ROLE || "").trim().toLowerCase();
  return {
    role,
    isPrimary: role === "primary",
  };
}

export interface LockInfo {
  host: string;
  container_id: string;
  pid: number;
  start_time: string;
}

export interface LockAcquisitionResult {
  acquired: boolean;
  reclaimed?: boolean;
  reason?: string;
  existing?: LockInfo;
}

export function acquireHostLock(
  lockDir: string,
  host: string,
  containerId: string,
  pid: number
): LockAcquisitionResult {
  if (!existsSync(lockDir)) {
    mkdirSync(lockDir, { recursive: true });
  }

  const lockFile = join(lockDir, "poller.lock");

  if (existsSync(lockFile)) {
    try {
      const raw = readFileSync(lockFile, "utf-8");
      const existing: LockInfo = JSON.parse(raw);

      // Check if existing holder is on the same host
      const isSameHost = existing.host === host;

      if (isSameHost) {
        // Test if PID is alive
        let isAlive = false;
        try {
          process.kill(existing.pid, 0);
          isAlive = true;
        } catch {
          isAlive = false;
        }

        if (isAlive) {
          return {
            acquired: false,
            reason: `live holder on the same host (PID ${existing.pid})`,
            existing,
          };
        }
      }

      // If dead PID or different host, reclaim lock with warning
      const lockData: LockInfo = {
        host,
        container_id: containerId,
        pid,
        start_time: new Date().toISOString(),
      };
      writeFileSync(lockFile, JSON.stringify(lockData, null, 2), "utf-8");
      return {
        acquired: true,
        reclaimed: true,
        existing,
      };
    } catch {
      // Corrupt lock file, overwrite
    }
  }

  const lockData: LockInfo = {
    host,
    container_id: containerId,
    pid,
    start_time: new Date().toISOString(),
  };
  writeFileSync(lockFile, JSON.stringify(lockData, null, 2), "utf-8");
  return { acquired: true };
}

export function releaseHostLock(lockDir: string): void {
  const lockFile = join(lockDir, "poller.lock");
  if (existsSync(lockFile)) {
    try {
      unlinkSync(lockFile);
    } catch {
      // Ignore cleanup error
    }
  }
}

export function calculate409Backoff(attempt: number): number {
  // Base 5s (5000ms), doubles each attempt, capped at 5 minutes (300,000ms)
  const delay = 5000 * Math.pow(2, attempt);
  return Math.min(delay, 300000);
}
