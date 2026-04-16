import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";

const STASH_URL = process.env.STASH_URL ?? "http://192.168.1.203:9999";

interface StashPerformer {
  id: string;
  name: string;
  image_path: string | null;
  scene_count: number;
  image_count: number;
}


/**
 * GET /api/stash?performer=Name — fetch performer data and images from Stash
 * Returns performer profile + gallery images for PuLID reference selection.
 */
export async function GET(req: Request) {
  const url = new URL(req.url);
  const performerName = url.searchParams.get("performer");

  if (!performerName) {
    return Response.json({ error: "performer query param required" }, { status: 400 });
  }

  if (EOQ_FIXTURE_MODE) {
    return Response.json({
      performer: {
        id: "fixture-1",
        name: performerName,
        image_path: null,
        scene_count: 5,
        image_count: 10,
      },
      images: [],
    });
  }

  // Find performer by exact name
  const performer = await findPerformer(performerName);
  if (!performer) {
    return Response.json({ error: `Performer "${performerName}" not found` }, { status: 404 });
  }

  // Check if performer has a real image (not a placeholder) via is_missing filter.
  // Stash's HEAD endpoint returns 405, so we can't check content-length.
  // Instead, query GraphQL: if is_missing:"image" returns 0 results for this
  // performer, they have a real image.
  const hasRealProfileImage = performer.image_path
    ? await checkHasRealImage(performer.name)
    : false;

  // Fetch scene screenshots for this performer (for PuLID reference variety)
  const screenshots = await fetchPerformerScreenshots(performer.id);

  return Response.json({
    performer,
    hasRealProfileImage,
    screenshots,
  });
}

async function findPerformer(name: string): Promise<StashPerformer | null> {
  const query = `{
    findPerformers(performer_filter: {name: {value: "${escapeGraphQL(name)}", modifier: EQUALS}}) {
      performers { id name image_path scene_count image_count }
    }
  }`;

  try {
    const resp = await fetch(`${STASH_URL}/graphql`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    if (!resp.ok) return null;
    const data = await resp.json();
    const performers = data?.data?.findPerformers?.performers ?? [];
    return performers[0] ?? null;
  } catch {
    return null;
  }
}

async function checkHasRealImage(performerName: string): Promise<boolean> {
  const query = `{
    findPerformers(performer_filter: {
      name: {value: "${escapeGraphQL(performerName)}", modifier: EQUALS},
      is_missing: "image"
    }) { count }
  }`;
  try {
    const resp = await fetch(`${STASH_URL}/graphql`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!resp.ok) return false;
    const data = await resp.json();
    // If count is 0, the performer is NOT missing an image → has a real one
    return (data?.data?.findPerformers?.count ?? 1) === 0;
  } catch {
    return false;
  }
}

interface SceneScreenshot {
  sceneId: string;
  title: string;
  screenshotUrl: string;
}

async function fetchPerformerScreenshots(performerId: string): Promise<SceneScreenshot[]> {
  const query = `{
    findScenes(scene_filter: {performers: {value: ["${escapeGraphQL(performerId)}"], modifier: INCLUDES}}, filter: {per_page: 20, sort: "random"}) {
      scenes { id title paths { screenshot } }
    }
  }`;

  try {
    const resp = await fetch(`${STASH_URL}/graphql`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    if (!resp.ok) return [];
    const data = await resp.json();
    const scenes = data?.data?.findScenes?.scenes ?? [];
    return scenes
      .filter((s: { paths?: { screenshot?: string } }) => s.paths?.screenshot)
      .map((s: { id: string; title: string; paths: { screenshot: string } }) => ({
        sceneId: s.id,
        title: s.title,
        screenshotUrl: s.paths.screenshot,
      }));
  } catch {
    return [];
  }
}

function escapeGraphQL(str: string): string {
  return str.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}
