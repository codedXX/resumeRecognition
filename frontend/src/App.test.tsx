import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { diffMarkerForStatus } from "./lib";

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

  it("shows an actionable dialog before submitting an oversized file", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    renderApp();
    const input = document.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    const oversized = new File(["resume"], "large.pdf", { type: "application/pdf" });
    Object.defineProperty(oversized, "size", { value: 10 * 1024 * 1024 + 1 });

    fireEvent.change(input, { target: { files: [oversized] } });

    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
    expect(screen.getAllByText("large.pdf").length).toBeGreaterThan(0);
    expect(screen.getByText(/超过.*10\s*MiB|10\s*MiB.*限制/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("rejects an over-limit selection before beginning upload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    renderApp();
    const input = document.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    const files = Array.from({ length: 6 }, (_, index) => new File(["resume"], `resume-${index + 1}.pdf`, { type: "application/pdf" }));

    fireEvent.change(input, { target: { files } });

    expect(await screen.findByRole("alertdialog")).toHaveTextContent("单次最多上传 5 个文件");
    expect(screen.getByRole("alertdialog")).toHaveTextContent("当前选择 6 个文件");
    expect(screen.getByRole("button", { name: "重新选择文件" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([, init]) => (init as RequestInit | undefined)?.method === "POST")).toBe(false);
  });

  it("summarizes partial upload failures without claiming all files are ready", async () => {
    const batch = {
      id: "batch-1", status: "pending", profile_id: null, criteria_snapshot: null,
      files: [], counts: { pending: 0, ready: 0, processing: 0, completed: 0, failed: 0, unreadable: 0 },
    };
    const failedFile = { id: "file-failed", original_name: "large.pdf", status: "failed", error: "文件超过大小限制" };
    const readyFile = { id: "file-ready", original_name: "ok.pdf", status: "ready", error: null };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/roles")) return new Response(JSON.stringify([]), { status: 200 });
      if (init?.method === "POST" && url.endsWith("/api/batches")) return new Response(JSON.stringify(batch), { status: 201 });
      if (init?.method === "POST" && url.endsWith("/api/batches/batch-1/files")) return new Response(JSON.stringify([failedFile, readyFile]), { status: 201 });
      if (url.endsWith("/api/batches/batch-1")) return new Response(JSON.stringify({ ...batch, files: [failedFile, readyFile], counts: { ...batch.counts, ready: 1, failed: 1 } }), { status: 200 });
      return new Response(JSON.stringify([]), { status: 200 });
    }));
    renderApp();
    const input = document.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    fireEvent.change(input, { target: { files: [new File(["a"], "large.pdf"), new File(["b"], "ok.pdf")] } });

    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
    expect(screen.getAllByText("large.pdf").length).toBeGreaterThan(0);
    expect(screen.getByText("文件超过大小限制")).toBeInTheDocument();
    expect(screen.getAllByText(/1 份文件已就绪/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "关闭" }));
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("combobox", { name: "选择岗位" })));
    expect(screen.queryByText("文件已准备完成；选择岗位后可开始评估。")).not.toBeInTheDocument();
  });

  it("announces upload service errors with a retry suggestion", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/roles")) return new Response(JSON.stringify([]), { status: 200 });
      if (init?.method === "POST" && url.endsWith("/api/batches")) return new Response(JSON.stringify({ detail: "服务暂时不可用" }), { status: 503 });
      return new Response(JSON.stringify([]), { status: 200 });
    }));
    renderApp();
    const input = document.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    fireEvent.change(input, { target: { files: [new File(["a"], "ok.pdf")] } });
    expect(await screen.findByText(/服务暂时不可用.*请检查网络后重试/)).toBeInTheDocument();
  });

  it("explains when no readable files remain after preflight", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify([]), { status: 200 }))));
    renderApp();
    const input = document.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    fireEvent.change(input, { target: { files: [new File(["a"], "notes.txt", { type: "text/plain" })] } });
    expect(await screen.findByRole("alertdialog")).toHaveTextContent("没有文件就绪");
    expect(screen.getByText("notes.txt")).toBeInTheDocument();
  });

  it("keeps a five-file selection on the successful upload path", async () => {
    const batch = { id: "batch-success", status: "pending", profile_id: null, criteria_snapshot: null, files: [], counts: { pending: 0, ready: 0, processing: 0, completed: 0, failed: 0, unreadable: 0 } };
    const readyFile = { id: "file-ready", original_name: "ok.pdf", status: "ready", error: null };
    let uploadedFileCount = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/roles")) return new Response(JSON.stringify([]), { status: 200 });
      if (init?.method === "POST" && url.endsWith("/api/batches")) return new Response(JSON.stringify(batch), { status: 201 });
      if (init?.method === "POST" && url.endsWith("/api/batches/batch-success/files")) {
        uploadedFileCount = (init.body as FormData).getAll("files").length;
        return new Response(JSON.stringify([readyFile]), { status: 201 });
      }
      if (url.endsWith("/api/batches/batch-success")) return new Response(JSON.stringify({ ...batch, files: [readyFile], counts: { ...batch.counts, ready: 1 } }), { status: 200 });
      return new Response(JSON.stringify([]), { status: 200 });
    }));
    renderApp();
    const input = document.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    fireEvent.change(input, { target: { files: Array.from({ length: 5 }, (_, index) => new File(["a"], `ok-${index + 1}.pdf`)) } });
    expect(await screen.findByRole("status")).toHaveTextContent("文件已准备完成；选择岗位后可开始评估。");
    expect(uploadedFileCount).toBe(5);
  });

  it("opens a role form with the documented default score", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 })));
    renderApp();
    fireEvent.click(await screen.findByRole("button", { name: "管理岗位" }));
    expect(screen.getByRole("spinbutton", { name: /合格线/ })).toHaveValue(80);
    expect(screen.getByText("默认 80 分，岗位可单独调整。")).toBeInTheDocument();
  });

  it("accepts a complete multiline job rule without splitting it", async () => {
    const role = { id: "role-1", name: "视觉设计师", evaluation_prompt: "1、负责电商视觉；\n2、熟悉 AI 工作流", passing_score: 80, archived: false, requirements: [] };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/api/roles")) return new Response(JSON.stringify([role]), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    }));
    renderApp();
    fireEvent.click(await screen.findByRole("button", { name: "管理岗位" }));
    fireEvent.click(await screen.findByRole("button", { name: /视觉设计师/ }));
    const rule = screen.getByRole("textbox", { name: "岗位规则" });
    expect(rule).toHaveValue(role.evaluation_prompt);
    expect(rule).toHaveAttribute("rows");
  });

  it("sends the complete rule text unchanged when creating a role", async () => {
    let createBody: Record<string, unknown> = {};
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/roles") && init?.method === "POST") {
        createBody = JSON.parse(String(init.body));
        return new Response(JSON.stringify({ id: "role-new", name: "视觉设计师", evaluation_prompt: createBody.evaluation_prompt ?? "", passing_score: 80, archived: false, requirements: [] }), { status: 201 });
      }
      if (url.endsWith("/api/roles")) return new Response(JSON.stringify([]), { status: 200 });
      return new Response(JSON.stringify([]), { status: 200 });
    }));
    renderApp();
    fireEvent.click(await screen.findByRole("button", { name: "管理岗位" }));
    const text = "1、负责电商视觉；\n2、熟悉 AI 工作流。";
    fireEvent.change(screen.getByRole("textbox", { name: "岗位名称" }), { target: { value: "视觉设计师" } });
    fireEvent.change(screen.getByRole("textbox", { name: "岗位规则" }), { target: { value: text } });
    fireEvent.click(screen.getByRole("button", { name: "保存岗位" }));
    await screen.findByRole("button", { name: "管理岗位" });
    expect(createBody.evaluation_prompt).toBe(text);
  });

  it("requires usable job rule text before saving", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 })));
    renderApp();
    fireEvent.click(await screen.findByRole("button", { name: "管理岗位" }));
    fireEvent.change(screen.getByRole("textbox", { name: "岗位名称" }), { target: { value: "设计师" } });
    expect(screen.getByRole("button", { name: "保存岗位" })).toBeDisabled();
  });

  it("keeps existing structured requirements when advanced settings stay untouched", async () => {
    const requirement = { id: "req-1", description: "熟悉 Figma", priority: "required", position: 0 };
    const role = { id: "role-1", name: "视觉设计师", evaluation_prompt: "负责视觉设计", passing_score: 80, archived: false, requirements: [requirement] };
    const calls: Array<{ url: string; method: string }> = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, method: init?.method ?? "GET" });
      if (url.endsWith("/api/roles") && !init?.method) return new Response(JSON.stringify([role]), { status: 200 });
      if (url.endsWith("/api/roles/role-1") && init?.method === "PUT") return new Response(JSON.stringify(role), { status: 200 });
      return new Response(JSON.stringify([]), { status: 200 });
    }));
    renderApp();
    fireEvent.click(await screen.findByRole("button", { name: "管理岗位" }));
    fireEvent.click(await screen.findByRole("button", { name: /视觉设计师/ }));
    fireEvent.change(screen.getByRole("textbox", { name: "岗位规则" }), { target: { value: "更新后的完整岗位规则" } });
    fireEvent.click(screen.getByRole("button", { name: "保存岗位" }));
    expect(await screen.findByRole("button", { name: "管理岗位" })).toBeInTheDocument();
    expect(calls.some((call) => call.method === "DELETE" && call.url.includes("requirements"))).toBe(false);
  });

  it("maps review states to explicit diff markers", () => {
    expect(diffMarkerForStatus("qualified")).toBe("+");
    expect(diffMarkerForStatus("unqualified")).toBe("-");
    expect(diffMarkerForStatus("selected")).toBe(">");
  });

  it("exposes the editorial review regions in the empty workbench", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 })));
    renderApp();
    expect(await screen.findByText("候选人审阅记录")).toBeInTheDocument();
    expect(screen.getAllByText("证据对照").length).toBeGreaterThan(0);
    expect(screen.getByText("选择一份简历")).toBeInTheDocument();
    expect(screen.getByText("文件队列")).toBeInTheDocument();
    expect(screen.queryByText("/ 文件队列")).not.toBeInTheDocument();
    expect(screen.queryByText("/ 候选人")).not.toBeInTheDocument();
    expect(screen.queryByText("/ 证据对照")).not.toBeInTheDocument();
    expect(screen.queryByText("RECRUIT REVIEW / 证据优先")).not.toBeInTheDocument();
    expect(screen.queryByText("/ evidence diff")).not.toBeInTheDocument();
  });

  it("keeps completed evidence tied to diff findings", async () => {
    const role = { id: "role-1", name: "Python 后端工程师", evaluation_prompt: "引用原文", passing_score: 80, archived: false, requirements: [] };
    const completedFile = { id: "file-1", original_name: "lin-resume.pdf", status: "completed", error: null };
    const batch = { id: "batch-1", status: "completed", profile_id: role.id, criteria_snapshot: { name: role.name, passing_score: 80, requirements: [] }, files: [completedFile], counts: { pending: 0, ready: 0, processing: 0, completed: 1, failed: 0, unreadable: 0 } };
    const candidate = { file: completedFile, evaluation: { id: "evaluation-1", score: 92, qualified: true, reason: "经验与岗位要求匹配", satisfied: ["3 年 Python 服务端经验"], unmet: ["教育背景未提供"], evidence: [{ requirement: "Python 服务端经验", evidence: "负责 FastAPI 服务拆分与接口设计" }], provider: "heuristic", error: null } };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/api/roles")) return new Response(JSON.stringify([role]), { status: 200 });
      if (method === "POST" && url.endsWith("/api/batches")) return new Response(JSON.stringify({ ...batch, files: [], counts: { pending: 0, ready: 0, processing: 0, completed: 0, failed: 0, unreadable: 0 } }), { status: 201 });
      if (method === "POST" && url.endsWith("/api/batches/batch-1/files")) return new Response(JSON.stringify([completedFile]), { status: 201 });
      if (url.endsWith("/api/batches/batch-1")) return new Response(JSON.stringify(batch), { status: 200 });
      if (url.endsWith("/api/batches/batch-1/results")) return new Response(JSON.stringify([candidate]), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    }));
    const view = renderApp();
    const input = view.container.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    fireEvent.change(input, { target: { files: [new File(["resume"], "lin-resume.pdf", { type: "application/pdf" })] } });
    fireEvent.click(await screen.findByRole("button", { name: /lin-resume/ }));
    expect(screen.getAllByText("证据对照").length).toBeGreaterThan(0);
    expect(screen.getByText(/满足条件/)).toBeInTheDocument();
    expect(screen.getByText(/待补证据/)).toBeInTheDocument();
    expect(screen.getByText("“负责 FastAPI 服务拆分与接口设计”")).toBeInTheDocument();
  });

  it("explains when a pending batch has expired and cannot start", async () => {
    const role = { id: "role-1", name: "Python 后端工程师", evaluation_prompt: "引用原文", passing_score: 80, archived: false, requirements: [] };
    const expiredFile = { id: "file-expired", original_name: "expired.pdf", status: "failed", error: "临时上传内容已过期，请重新上传" };
    const batch = { id: "batch-expired", status: "expired", profile_id: null, criteria_snapshot: null, files: [expiredFile], counts: { pending: 0, ready: 0, processing: 0, completed: 0, failed: 1, unreadable: 0 } };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/api/roles")) return new Response(JSON.stringify([role]), { status: 200 });
      if (method === "POST" && url.endsWith("/api/batches")) return new Response(JSON.stringify({ ...batch, status: "pending", files: [], counts: { pending: 0, ready: 0, processing: 0, completed: 0, failed: 0, unreadable: 0 } }), { status: 201 });
      if (method === "POST" && url.endsWith("/api/batches/batch-expired/files")) return new Response(JSON.stringify([expiredFile]), { status: 201 });
      if (url.endsWith("/api/batches/batch-expired")) return new Response(JSON.stringify(batch), { status: 200 });
      if (url.endsWith("/api/batches/batch-expired/results")) return new Response(JSON.stringify([]), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    }));
    const view = renderApp();
    const input = view.container.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    fireEvent.change(input, { target: { files: [new File(["resume"], "expired.pdf", { type: "application/pdf" })] } });
    expect(await screen.findByText(/本批次已过期/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "关闭" }));
    expect(screen.getByRole("button", { name: "开始评估" })).toBeDisabled();
  });

  it("displays both red upload limits before a file is selected", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 })));
    renderApp();

    const selectionLimit = await screen.findByText("单次上传上限为 5 个文件");
    const sizeLimit = screen.getByText("单文件上限 10 MB");

    expect(selectionLimit).toHaveClass("upload-limit");
    expect(sizeLimit).toHaveClass("upload-limit");
  });

  it("starts a new cycle by deleting a completed batch before creating the next upload batch", async () => {
    const role = { id: "role-1", name: "Python 后端工程师", evaluation_prompt: "引用原文", passing_score: 80, archived: false, requirements: [] };
    const completedFile = { id: "file-1", original_name: "first.pdf", status: "completed", error: null };
    const completedBatch = { id: "batch-completed", status: "completed", profile_id: role.id, criteria_snapshot: { name: role.name, passing_score: 80, requirements: [] }, files: [completedFile], counts: { pending: 0, ready: 0, processing: 0, completed: 1, failed: 0, unreadable: 0 } };
    const candidate = { file: completedFile, evaluation: { id: "evaluation-1", score: 92, qualified: true, reason: "经验匹配", satisfied: [], unmet: [], evidence: [], provider: "heuristic", error: null } };
    const nextBatch = { id: "batch-next", status: "pending", profile_id: null, criteria_snapshot: null, files: [], counts: { pending: 0, ready: 0, processing: 0, completed: 0, failed: 0, unreadable: 0 } };
    const nextFile = { id: "file-2", original_name: "next.pdf", status: "ready", error: null };
    const calls: Array<{ url: string; method: string }> = [];
    let createdBatches = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      calls.push({ url, method });
      if (url.endsWith("/api/roles")) return new Response(JSON.stringify([role]), { status: 200 });
      if (method === "POST" && url.endsWith("/api/batches")) {
        createdBatches += 1;
        return new Response(JSON.stringify(createdBatches === 1 ? { ...completedBatch, files: [], counts: { pending: 0, ready: 0, processing: 0, completed: 0, failed: 0, unreadable: 0 } } : nextBatch), { status: 201 });
      }
      if (method === "POST" && url.endsWith("/api/batches/batch-completed/files")) return new Response(JSON.stringify([completedFile]), { status: 201 });
      if (method === "POST" && url.endsWith("/api/batches/batch-next/files")) return new Response(JSON.stringify([nextFile]), { status: 201 });
      if (method === "DELETE" && url.endsWith("/api/batches/batch-completed")) return new Response(null, { status: 204 });
      if (url.endsWith("/api/batches/batch-completed/results")) return new Response(JSON.stringify([candidate]), { status: 200 });
      if (url.endsWith("/api/batches/batch-completed")) return new Response(JSON.stringify(completedBatch), { status: 200 });
      if (url.endsWith("/api/batches/batch-next")) return new Response(JSON.stringify({ ...nextBatch, files: [nextFile], counts: { ...nextBatch.counts, ready: 1 } }), { status: 200 });
      if (url.endsWith("/api/batches/batch-next/results")) return new Response(JSON.stringify([{ file: nextFile, evaluation: null }]), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    }));
    const view = renderApp();
    const input = view.container.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    fireEvent.change(input, { target: { files: [new File(["resume"], "first.pdf", { type: "application/pdf" })] } });

    fireEvent.click(await screen.findByRole("button", { name: "开始新一轮评估" }));
    await waitFor(() => expect(calls).toContainEqual({ url: expect.stringMatching(/\/api\/batches\/batch-completed$/), method: "DELETE" }));
    expect(screen.getByText("还没有简历。先添加文件，再选择岗位标准。")).toBeInTheDocument();

    fireEvent.change(input, { target: { files: [new File(["resume"], "next.pdf", { type: "application/pdf" })] } });
    await waitFor(() => expect(calls).toContainEqual({ url: expect.stringMatching(/\/api\/batches\/batch-next\/files$/), method: "POST" }));
  });

  it("does not offer a new-cycle action while the batch is still pending", async () => {
    const pendingBatch = { id: "batch-pending", status: "pending", profile_id: null, criteria_snapshot: null, files: [], counts: { pending: 0, ready: 0, processing: 0, completed: 0, failed: 0, unreadable: 0 } };
    const readyFile = { id: "file-ready", original_name: "pending.pdf", status: "ready", error: null };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/api/roles")) return new Response(JSON.stringify([]), { status: 200 });
      if (method === "POST" && url.endsWith("/api/batches")) return new Response(JSON.stringify(pendingBatch), { status: 201 });
      if (method === "POST" && url.endsWith("/api/batches/batch-pending/files")) return new Response(JSON.stringify([readyFile]), { status: 201 });
      if (url.endsWith("/api/batches/batch-pending")) return new Response(JSON.stringify({ ...pendingBatch, files: [readyFile], counts: { ...pendingBatch.counts, ready: 1 } }), { status: 200 });
      return new Response(JSON.stringify([]), { status: 200 });
    }));
    const view = renderApp();
    const input = view.container.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    fireEvent.change(input, { target: { files: [new File(["resume"], "pending.pdf", { type: "application/pdf" })] } });

    await screen.findByText("pending.pdf");
    expect(screen.queryByRole("button", { name: "开始新一轮评估" })).not.toBeInTheDocument();
  });

  it("keeps completed results visible when starting a new cycle fails", async () => {
    const completedFile = { id: "file-1", original_name: "failed-reset.pdf", status: "completed", error: null };
    const completedBatch = { id: "batch-completed", status: "completed", profile_id: null, criteria_snapshot: null, files: [completedFile], counts: { pending: 0, ready: 0, processing: 0, completed: 1, failed: 0, unreadable: 0 } };
    const candidate = { file: completedFile, evaluation: { id: "evaluation-1", score: 92, qualified: true, reason: "经验匹配", satisfied: [], unmet: [], evidence: [], provider: "heuristic", error: null } };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/api/roles")) return new Response(JSON.stringify([]), { status: 200 });
      if (method === "POST" && url.endsWith("/api/batches")) return new Response(JSON.stringify({ ...completedBatch, files: [], counts: { pending: 0, ready: 0, processing: 0, completed: 0, failed: 0, unreadable: 0 } }), { status: 201 });
      if (method === "POST" && url.endsWith("/api/batches/batch-completed/files")) return new Response(JSON.stringify([completedFile]), { status: 201 });
      if (method === "DELETE" && url.endsWith("/api/batches/batch-completed")) return new Response(JSON.stringify({ detail: "批次暂不可清理" }), { status: 409 });
      if (url.endsWith("/api/batches/batch-completed/results")) return new Response(JSON.stringify([candidate]), { status: 200 });
      if (url.endsWith("/api/batches/batch-completed")) return new Response(JSON.stringify(completedBatch), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    }));
    const view = renderApp();
    const input = view.container.querySelector("input[type=file]");
    if (!input) throw new Error("file input not found");
    fireEvent.change(input, { target: { files: [new File(["resume"], "failed-reset.pdf", { type: "application/pdf" })] } });

    fireEvent.click(await screen.findByRole("button", { name: "开始新一轮评估" }));

    expect(await screen.findByText(/批次暂不可清理.*当前结果仍保留/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /failed-reset/ })).toBeInTheDocument();
  });
});
