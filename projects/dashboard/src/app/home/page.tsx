import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const revalidate = 60;

async function checkHA(): Promise<boolean> {
  try {
    const res = await fetch("http://192.168.1.203:8123/api/", {
      signal: AbortSignal.timeout(3000),
      next: { revalidate: 60 },
    });
    return res.ok;
  } catch {
    return false;
  }
}

export default async function HomePage() {
  const haOnline = await checkHA();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Home</h1>
        <p className="text-muted-foreground">
          Home Assistant smart home control
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Home Assistant</CardTitle>
            <Badge variant={haOnline ? "default" : "outline"}>
              {haOnline ? "Online" : "Not Configured"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {haOnline ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Home Assistant is running but onboarding has not been completed.
                Complete the setup to enable smart home controls.
              </p>
              <a
                href="http://192.168.1.203:8123"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
              >
                Open Home Assistant
              </a>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Home Assistant at VAULT:8123 is not reachable.
                Once it&apos;s running and onboarded, this page will show:
              </p>
              <div className="grid gap-3 md:grid-cols-2">
                <PlaceholderCard title="Lights" description="Control lights by room — brightness, color, scenes" />
                <PlaceholderCard title="Climate" description="Temperature, humidity, HVAC controls" />
                <PlaceholderCard title="Presence" description="Who's home, device tracking, automations" />
                <PlaceholderCard title="Automations" description="Active automations, triggers, manual override" />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Setup Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <StatusLine label="HA Container" status={haOnline} />
            <StatusLine label="Onboarding" status={false} note="Requires browser session" />
            <StatusLine label="Home Agent" status={false} note="Blocked on HA onboarding" />
            <StatusLine label="MCP Integration" status={false} note="After onboarding" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PlaceholderCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border p-4 opacity-50">
      <h3 className="text-sm font-medium">{title}</h3>
      <p className="text-xs text-muted-foreground mt-1">{description}</p>
    </div>
  );
}

function StatusLine({ label, status, note }: { label: string; status: boolean; note?: string }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${status ? "bg-green-500" : "bg-muted-foreground"}`} />
        <span>{label}</span>
      </div>
      {note && <span className="text-xs text-muted-foreground">{note}</span>}
    </div>
  );
}
