import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><App /></QueryClientProvider>);
}

describe("recruiter workbench", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it("keeps evaluation disabled until a role and readable file exist", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 })));
    renderApp();
    expect(await screen.findByText("还没有简历。先添加文件，再选择岗位标准。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始评估" })).toBeDisabled();
    expect(screen.getByText("请先选择岗位。")).toBeInTheDocument();
  });

  it("opens a role form with the documented default score", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 })));
    renderApp();
    fireEvent.click(await screen.findByRole("button", { name: "管理岗位" }));
    expect(screen.getByRole("spinbutton", { name: /合格线/ })).toHaveValue(80);
    expect(screen.getByText("默认 80 分，岗位可单独调整。")).toBeInTheDocument();
  });
});
