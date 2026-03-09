import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useUrlState } from "@/lib/url-state";

let pathname = "/services";
let search = "status=degraded";
const replace = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(search),
}));

function UrlStateHarness() {
  const { getSearchValue, setSearchValue, setSearchValues } = useUrlState();

  return (
    <div>
      <span data-testid="status">{getSearchValue("status", "all")}</span>
      <span data-testid="window">{getSearchValue("window", "3h")}</span>
      <button type="button" onClick={() => setSearchValue("search", "grafana")}>
        Set search
      </button>
      <button type="button" onClick={() => setSearchValue("status", null)}>
        Clear status
      </button>
      <button
        type="button"
        onClick={() =>
          setSearchValues({
            service: "grafana",
            node: "vault",
            status: null,
          })
        }
      >
        Set many
      </button>
    </div>
  );
}

describe("useUrlState", () => {
  beforeEach(() => {
    pathname = "/services";
    search = "status=degraded";
    replace.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("reads values with fallbacks", () => {
    render(<UrlStateHarness />);

    expect(screen.getByTestId("status")).toHaveTextContent("degraded");
    expect(screen.getByTestId("window")).toHaveTextContent("3h");
  });

  it("sets a single search value without scrolling", async () => {
    const user = userEvent.setup();
    render(<UrlStateHarness />);

    await user.click(screen.getByRole("button", { name: "Set search" }));

    expect(replace).toHaveBeenCalledWith("/services?status=degraded&search=grafana", {
      scroll: false,
    });
  });

  it("removes keys when null is passed", async () => {
    const user = userEvent.setup();
    render(<UrlStateHarness />);

    await user.click(screen.getByRole("button", { name: "Clear status" }));

    expect(replace).toHaveBeenCalledWith("/services", { scroll: false });
  });

  it("updates multiple keys together", async () => {
    const user = userEvent.setup();
    render(<UrlStateHarness />);

    await user.click(screen.getByRole("button", { name: "Set many" }));

    expect(replace).toHaveBeenCalledWith("/services?service=grafana&node=vault", {
      scroll: false,
    });
  });
});
