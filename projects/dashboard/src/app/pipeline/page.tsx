import { PipelineConsole } from "@/features/pipeline/pipeline-console";

export const revalidate = 15;

export default async function PipelinePage() {
  return <PipelineConsole />;
}
