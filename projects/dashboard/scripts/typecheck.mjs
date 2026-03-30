import { rmSync } from "node:fs";

for (const target of [
  ".next/types",
  ".next/dev/types",
  "tsconfig.tsbuildinfo",
  ".next/cache/.tsbuildinfo",
]) {
  rmSync(target, { recursive: true, force: true });
}
