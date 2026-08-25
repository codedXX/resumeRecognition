import { describe, expect, it } from "vitest";
import { canStart, filterCandidates, statusLabel } from "./lib";
import type { Batch, Candidate } from "./api";

const batch: Batch = { id: "batch", status: "pending", profile_id: null, criteria_snapshot: null, files: [{ id: "file", original_name: "alice.docx", status: "ready", error: null }], counts: {} };
const candidates: Candidate[] = [
  { file: batch.files[0], evaluation: { id: "one", score: 80, qualified: true, reason: "满足要求", satisfied: [], unmet: [], evidence: [], provider: "mock", error: null } },
  { file: { ...batch.files[0], id: "two" }, evaluation: { id: "two", score: 79, qualified: false, reason: "证据不足", satisfied: [], unmet: [], evidence: [], provider: "mock", error: null } },
];

describe("workbench flow guards", () => {
  it("requires both a role and a ready file before starting", () => {
    expect(canStart(batch, "role")).toBe(true);
    expect(canStart(batch, "")).toBe(false);
    expect(canStart({ ...batch, status: "processing" }, "role")).toBe(false);
  });
  it("keeps qualified and unqualified candidates distinct at the threshold", () => {
    expect(filterCandidates(candidates, "qualified")).toHaveLength(1);
    expect(filterCandidates(candidates, "unqualified")[0].evaluation?.score).toBe(79);
  });
  it("uses readable text labels independent of colour", () => expect(statusLabel("unreadable")).toBe("无法读取"));
});
