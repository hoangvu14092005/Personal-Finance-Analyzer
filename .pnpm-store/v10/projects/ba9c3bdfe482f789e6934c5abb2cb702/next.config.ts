import type { NextConfig } from "next";
import fs from "node:fs";
import path from "node:path";

const rootEnvPath = path.resolve(process.cwd(), "../..", ".env");

if (fs.existsSync(rootEnvPath)) {
  const rootEnv = fs.readFileSync(rootEnvPath, "utf8");

  for (const line of rootEnv.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const separatorIndex = trimmed.indexOf("=");
    if (separatorIndex === -1) continue;

    const key = trimmed.slice(0, separatorIndex).trim();
    const value = trimmed.slice(separatorIndex + 1).trim();
    process.env[key] ??= value;
  }
}

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
