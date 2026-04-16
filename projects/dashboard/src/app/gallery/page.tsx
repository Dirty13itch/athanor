import { GalleryConsole } from "@/features/gallery/gallery-console";
import { getGallerySnapshot } from "@/lib/subpage-data";

export const revalidate = 15;

export default async function GalleryPage() {
  const snapshot = await getGallerySnapshot();
  return <GalleryConsole initialSnapshot={snapshot} />;
}
