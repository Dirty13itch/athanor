import { ProjectsConsole } from "@/features/projects/projects-console";

export const revalidate = 15;

export default async function ProjectsPage() {
  return <ProjectsConsole />;
}
