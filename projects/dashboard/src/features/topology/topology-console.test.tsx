import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { TopologyConsole, type TopologyProps } from "./topology-console";

const { requestJson } = vi.hoisted(() => ({
  requestJson: vi.fn(),
}));

vi.mock("@/features/workforce/helpers", () => ({
  requestJson,
}));

vi.mock("@/components/master-atlas-relationship-panel", () => ({
  MasterAtlasRelationshipPanel: () => <div>Atlas relationship panel</div>,
}));

function buildWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

const topologyProps: TopologyProps = {
  nodes: [
    { id: "foundry", name: "FOUNDRY", ip: "192.168.1.244", role: "Heavy compute" },
    { id: "vault", name: "VAULT", ip: "192.168.1.203", role: "Storage and proxy" },
  ],
  models: [
    { nodeId: "foundry", name: "DeepSeek", alias: "deepseek", port: 8000, description: "Primary code lane" },
    { nodeId: "vault", name: "LiteLLM", alias: "litellm", port: 4000, description: "Proxy lane" },
  ],
  nodeServices: {
    foundry: ["agents", "gpu-orchestrator", "promptfoo"],
    vault: ["litellm", "storage"],
  },
};

describe("TopologyConsole", () => {
  it("renders the slimmer topology surfaces around ledger, node detail, and control relationships", async () => {
    requestJson.mockImplementation(async (url: string) => {
      if (url === "/api/gpu") {
        return {
          gpus: [
            {
              id: "gpu-1",
              node: "foundry",
              gpuName: "RTX 5090",
              temperatureC: 52,
              utilization: 42,
              memoryUsedMiB: 12000,
              memoryTotalMiB: 32768,
            },
          ],
        };
      }

      if (url === "/api/agents") {
        return {
          agents: [
            { id: "agent-1", name: "Scheduler", status: "ready", description: "Dispatches compute work." },
          ],
        };
      }

      if (url === "/api/overview") {
        return {
          nodes: [
            { id: "foundry", name: "FOUNDRY", healthyServices: 5, totalServices: 6, degradedServices: 1 },
            { id: "vault", name: "VAULT", healthyServices: 4, totalServices: 4, degradedServices: 0 },
          ],
        };
      }

      if (url === "/api/master-atlas") {
        return {
          nodes: [],
          edges: [],
          summary: {},
          turnover_readiness: {
            autonomous_turnover_status: "devstack_primary_build_and_shadow",
            provider_gate_state: "completed",
            work_economy_status: "ready",
            next_gate: "packet_review:goose",
            top_dispatchable_autonomous_task_title: "Capacity and Harvest Truth",
          },
          autonomous_queue_summary: {
            queue_count: 4,
            dispatchable_queue_count: 3,
            blocked_queue_count: 1,
          },
          node_capacity: [
            {
              node_id: "foundry",
              node_role: "Heavy compute",
              gpu_count: 4,
              interactive_reserve_gpu_slots: 1,
              background_fill_gpu_slots: 4,
              utilization_targets: {
                interactive_reserve_floor_gpu_slots: 1,
                background_harvest_target_gpu_slots: 4,
                max_noncritical_preemptible_gpu_slots: 4,
              },
            },
            {
              node_id: "vault",
              node_role: "Storage and proxy",
              gpu_count: 1,
              interactive_reserve_gpu_slots: 0,
              background_fill_gpu_slots: 1,
              utilization_targets: {
                interactive_reserve_floor_gpu_slots: 0,
                background_harvest_target_gpu_slots: 1,
                max_noncritical_preemptible_gpu_slots: 1,
              },
            },
          ],
          dispatch_lanes: [
            {
              lane_id: "foundry-bulk",
              provider_id: "athanor_local",
              reserve_class: "primary_sovereign_bulk",
              max_parallel_slots: 4,
              reserved_parallel_slots: 1,
              harvestable_parallel_slots: 3,
            },
            {
              lane_id: "vault-support",
              provider_id: "vault_arc",
              reserve_class: "support_lane_hold",
              max_parallel_slots: 1,
              reserved_parallel_slots: 1,
              harvestable_parallel_slots: 0,
            },
          ],
          quota_posture: {
            quota_posture: "protect_reserve_then_harvest",
            respect_vendor_policy_before_harvest: true,
            other_metered_disabled_for_auto_harvest_by_default: true,
            record_count: 3,
            degraded_record_count: 0,
            low_confidence_record_count: 0,
            degraded_records: [],
            local_compute_capacity: {
              remaining_units: 6,
              sample_posture: "scheduler_projection_backed",
              scheduler_queue_depth: 0,
              scheduler_slot_count: 5,
              harvestable_scheduler_slot_count: 2,
              harvestable_by_zone: { F: 2 },
              harvestable_by_slot: { "F:TP4": 2 },
              open_harvest_slot_ids: ["F:TP4"],
              open_harvest_slot_target_ids: ["foundry-bulk-pool"],
              scheduler_conflict_gpu_count: 0,
            },
          },
        };
      }

      return {};
    });

    render(<TopologyConsole {...topologyProps} />, { wrapper: buildWrapper() });

    expect(await screen.findByRole("heading", { name: /System Topology/i })).toBeInTheDocument();
    expect(screen.getByText(/Topology spine/i)).toBeInTheDocument();
    expect(screen.getByText(/Operational shape before inventory/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Control posture/i).length).toBeGreaterThan(0);
    expect(await screen.findByText(/Capacity and Harvest Truth/i)).toBeInTheDocument();
    expect(
      await screen.findByText((content) => content.includes("dispatchable of 4 total"))
    ).toBeInTheDocument();
    expect(
      await screen.findByText((content) => content.includes("approval held"))
    ).toBeInTheDocument();
    expect(screen.getByText(/Harvestable truth/i)).toBeInTheDocument();
    expect(screen.getByText(/Live local compute economy/i)).toBeInTheDocument();
    expect(screen.getByText(/2\/5/i)).toBeInTheDocument();
    expect(screen.getByText(/Reserve and harvest posture/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Reserve-bound/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Harvestable/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Harvest target 4/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Preemptible 4/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Node posture at a glance/i)).toBeInTheDocument();
    expect(screen.getByText(/Node details/i)).toBeInTheDocument();
    expect(screen.getByText(/Orchestration layer/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Authority and system map/i })).toBeInTheDocument();
    expect(screen.getAllByText("FOUNDRY").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Use this section as the quick-read ledger/i).length).toBeGreaterThan(0);
  });
});
