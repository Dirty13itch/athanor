import { ProjectsConsole } from "@/features/projects/projects-console";
import { loadProjectFactorySnapshot } from "@/lib/project-factory";

export const revalidate = 15;

export default async function ProjectsPage() {
  const initialSnapshot = await loadProjectFactorySnapshot();
  return <ProjectsConsole initialSnapshot={initialSnapshot} />;
}
