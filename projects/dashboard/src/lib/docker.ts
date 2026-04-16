import http from "node:http";
import {
  getFoundryDockerProxyUrl,
  getVaultDockerProxyUrl,
  getWorkshopDockerProxyUrl,
} from "@/lib/runtime-hosts";

export interface DockerHost {
  name: string;
  socketPath?: string;
  host?: string;
  port?: number;
  allowRestart: boolean;
}

export interface DockerContainer {
  Id: string;
  Names: string[];
  Image: string;
  State: string;
  Status: string;
  Created: number;
}

export interface DockerContainerWithNode extends DockerContainer {
  node: string;
}

const DOCKER_HOSTS: DockerHost[] = [
  ...(getWorkshopDockerProxyUrl()
    ? [
        {
          name: "workshop",
          host: getWorkshopDockerProxyUrl()!,
          allowRestart: true,
        },
      ]
    : []),
  {
    name: "foundry",
    host: getFoundryDockerProxyUrl(),
    allowRestart: false,
  },
  {
    name: "vault",
    host: getVaultDockerProxyUrl(),
    allowRestart: true,
  },
];

function dockerRequest<T>(method: string, path: string, host: DockerHost): Promise<T> {
  return new Promise((resolve, reject) => {
    const timeout = host.socketPath ? 15_000 : 5_000;
    let options: http.RequestOptions;

    if (host.socketPath) {
      options = { socketPath: host.socketPath, path, method, headers: { "Content-Type": "application/json" } };
    } else if (host.host) {
      const url = new URL(path, host.host);
      options = {
        hostname: url.hostname,
        port: url.port,
        path: url.pathname + url.search,
        method,
        headers: { "Content-Type": "application/json" },
      };
    } else {
      reject(new Error(`Docker host unavailable on ${host.name}`));
      return;
    }

    const req = http.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data ? (JSON.parse(data) as T) : (undefined as T));
        } else {
          reject(new Error(`Docker API ${method} ${path} on ${host.name}: ${res.statusCode} ${data}`));
        }
      });
    });
    req.on("error", reject);
    req.setTimeout(timeout, () => {
      req.destroy();
      reject(new Error(`Docker API timeout: ${method} ${path} on ${host.name}`));
    });
    req.end();
  });
}

function getContainerLogsFromHost(host: DockerHost, idOrName: string, tail = 100): Promise<string> {
  return new Promise((resolve, reject) => {
    const timeout = host.socketPath ? 10_000 : 5_000;
    const path = `/containers/${encodeURIComponent(idOrName)}/logs?stdout=true&stderr=true&tail=${tail}&timestamps=true`;
    let options: http.RequestOptions;

    if (host.socketPath) {
      options = { socketPath: host.socketPath, path, method: "GET" };
    } else if (host.host) {
      const url = new URL(path, host.host);
      options = { hostname: url.hostname, port: url.port, path: url.pathname + url.search, method: "GET" };
    } else {
      reject(new Error(`Docker host unavailable on ${host.name}`));
      return;
    }

    const req = http.request(options, (res) => {
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
    });
    req.on("error", reject);
    req.setTimeout(timeout, () => {
      req.destroy();
      reject(new Error(`Docker logs timeout on ${host.name}`));
    });
    req.end();
  });
}

function getHostByName(name: string): DockerHost | undefined {
  return DOCKER_HOSTS.find((h) => h.name === name);
}

async function listContainersFromHost(host: DockerHost): Promise<DockerContainerWithNode[]> {
  const containers = await dockerRequest<DockerContainer[]>("GET", "/containers/json?all=true", host);
  return containers.map((c) => ({ ...c, node: host.name }));
}

export async function listAllContainers(): Promise<DockerContainerWithNode[]> {
  const results = await Promise.allSettled(
    DOCKER_HOSTS.map((host) => listContainersFromHost(host))
  );
  const containers: DockerContainerWithNode[] = [];
  for (const result of results) {
    if (result.status === "fulfilled") {
      containers.push(...result.value);
    }
  }
  return containers;
}

export async function restartContainer(nodeName: string, idOrName: string): Promise<void> {
  const host = getHostByName(nodeName);
  if (!host) throw new Error(`Unknown node: ${nodeName}`);
  if (!host.allowRestart) throw new Error(`Restart not allowed on ${nodeName}`);
  await dockerRequest<void>("POST", `/containers/${encodeURIComponent(idOrName)}/restart?t=10`, host);
}

export async function getContainerLogs(nodeName: string, idOrName: string, tail = 100): Promise<string> {
  const host = getHostByName(nodeName);
  if (!host) throw new Error(`Unknown node: ${nodeName}`);
  return getContainerLogsFromHost(host, idOrName, tail);
}

export function isDockerAvailable(): boolean {
  return Boolean(getWorkshopDockerProxyUrl());
}

export function getDockerHosts(): DockerHost[] {
  return DOCKER_HOSTS;
}
