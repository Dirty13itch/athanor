declare module "react-force-graph-2d" {
  import { Component } from "react";

  interface ForceGraph2DProps {
    graphData?: { nodes: unknown[]; links: unknown[] };
    nodeId?: string;
    nodeLabel?: string | ((node: unknown) => string);
    nodeColor?: string | ((node: unknown) => string);
    nodeVal?: string | ((node: unknown) => number);
    nodeCanvasObject?: (node: unknown, ctx: CanvasRenderingContext2D, globalScale: number) => void;
    nodeCanvasObjectMode?: string | ((node: unknown) => string);
    linkColor?: string | ((link: unknown) => string);
    linkWidth?: number | ((link: unknown) => number);
    linkDirectionalParticles?: number | ((link: unknown) => number);
    linkDirectionalParticleWidth?: number;
    linkLabel?: string | ((link: unknown) => string);
    linkCanvasObject?: (link: unknown, ctx: CanvasRenderingContext2D, globalScale: number) => void;
    linkCanvasObjectMode?: string;
    onNodeClick?: (node: unknown, event: MouseEvent) => void;
    onNodeHover?: (node: unknown | null, prevNode: unknown | null) => void;
    onLinkClick?: (link: unknown, event: MouseEvent) => void;
    onBackgroundClick?: (event: MouseEvent) => void;
    width?: number;
    height?: number;
    backgroundColor?: string;
    cooldownTicks?: number;
    warmupTicks?: number;
    d3AlphaDecay?: number;
    d3VelocityDecay?: number;
    ref?: React.Ref<unknown>;
    [key: string]: unknown;
  }

  export default class ForceGraph2D extends Component<ForceGraph2DProps> {}
}
