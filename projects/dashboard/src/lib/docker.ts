import http from "node:http";

const DOCKER_SOCKET = "/var/run/docker.sock";

export interface DockerContainer {
  Id: string;
  Names: string[];
  Image: string;
  State: string;
  Status: string;
  Created: number;
}

function dockerRequest<T>(method: string, path: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const req = http.request(
      { socketPath: DOCKER_SOCKET, path, method, headers: { "Content-Type": "application/json" } },
      (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
            resolve(data ? (JSON.parse(data) as T) : (undefined as T));
          } else {
            reject(new Error(`Docker API ${method} ${path}: ${res.statusCode} ${data}`));
          }
        });
      }
    );
    req.on("error", reject);
    req.setTimeout(15_000, () => {
      req.destroy();
      reject(new Error(`Docker API timeout: ${method} ${path}`));
    });
    req.end();
  });
}

export async function listContainers(): Promise<DockerContainer[]> {
  return dockerRequest<DockerContainer[]>("GET", "/containers/json?all=true");
}

export async function restartContainer(idOrName: string): Promise<void> {
  await dockerRequest<void>("POST", `/containers/${encodeURIComponent(idOrName)}/restart?t=10`);
}

export async function getContainerLogs(idOrName: string, tail = 100): Promise<string> {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        socketPath: DOCKER_SOCKET,
        path: `/containers/${encodeURIComponent(idOrName)}/logs?stdout=true&stderr=true&tail=${tail}&timestamps=true`,
        method: "GET",
      },
      (res) => {
        const chunks: Buffer[] = [];
        res.on("data", (chunk: Buffer) => chunks.push(chunk));
        res.on("end", () => {
          const raw = Buffer.concat(chunks);
          // Docker multiplexed stream: strip 8-byte header from each frame
          const lines: string[] = [];
          let offset = 0;
          while (offset < raw.length) {
            if (offset + 8 > raw.length) break;
            const frameSize = raw.readUInt32BE(offset + 4);
            if (offset + 8 + frameSize > raw.length) break;
            lines.push(raw.subarray(offset + 8, offset + 8 + frameSize).toString("utf8"));
            offset += 8 + frameSize;
          }
          resolve(lines.join(""));
        });
      }
    );
    req.on("error", reject);
    req.setTimeout(10_000, () => {
      req.destroy();
      reject(new Error("Docker logs timeout"));
    });
    req.end();
  });
}

export function isDockerAvailable(): boolean {
  try {
    require("node:fs").accessSync(DOCKER_SOCKET);
    return true;
  } catch {
    return false;
  }
}
