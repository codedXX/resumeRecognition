export const API_URL = import.meta.env.VITE_API_URL;

export type Requirement = { id: string; description: string; priority: "required" | "preferred"; position: number };
export type Role = { id: string; name: string; evaluation_prompt: string; passing_score: number; archived: boolean; requirements: Requirement[] };
export type ResumeFile = { id: string; original_name: string; status: string; error: string | null };
export type Evaluation = { id: string; score: number | null; qualified: boolean | null; reason: string | null; satisfied: string[]; unmet: string[]; evidence: { requirement: string; evidence: string }[]; provider: string | null; error: string | null };
export type Candidate = { file: ResumeFile; evaluation: Evaluation | null };
export type Batch = { id: string; status: string; profile_id: string | null; criteria_snapshot: { name: string; passing_score: number; requirements: Requirement[] } | null; files: ResumeFile[]; counts: Record<string, number> };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) }, ...init });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "请求未完成");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  roles: () => request<Role[]>("/api/roles"),
  createRole: (payload: { name: string; evaluation_prompt: string; passing_score: number; requirements: { description: string; priority: string }[] }) => request<Role>("/api/roles", { method: "POST", body: JSON.stringify(payload) }),
  updateRole: (id: string, payload: Partial<Pick<Role, "name" | "evaluation_prompt" | "passing_score">>) => request<Role>(`/api/roles/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteRole: (id: string) => request<void>(`/api/roles/${id}`, { method: "DELETE" }),
  addRequirement: (roleId: string, payload: { description: string; priority: string }) => request<Requirement>(`/api/roles/${roleId}/requirements`, { method: "POST", body: JSON.stringify(payload) }),
  updateRequirement: (roleId: string, requirementId: string, payload: { description: string; priority: string }) => request<Requirement>(`/api/roles/${roleId}/requirements/${requirementId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteRequirement: (roleId: string, requirementId: string) => request<void>(`/api/roles/${roleId}/requirements/${requirementId}`, { method: "DELETE" }),
  reorderRequirements: (roleId: string, requirement_ids: string[]) => request<Requirement[]>(`/api/roles/${roleId}/requirements/reorder`, { method: "POST", body: JSON.stringify({ requirement_ids }) }),
  createBatch: () => request<Batch>("/api/batches", { method: "POST" }),
  upload: async (batchId: string, files: File[]) => {
    const body = new FormData(); files.forEach((file) => body.append("files", file));
    const response = await fetch(`${API_URL}/api/batches/${batchId}/files`, { method: "POST", body });
    if (!response.ok) throw new Error((await response.json()).detail ?? "上传失败");
    return response.json() as Promise<ResumeFile[]>;
  },
  start: (batchId: string, profile_id: string) => request<Batch>(`/api/batches/${batchId}/start`, { method: "POST", body: JSON.stringify({ profile_id }) }),
  batch: (id: string) => request<Batch>(`/api/batches/${id}`),
  results: (id: string, state?: string) => request<Candidate[]>(`/api/batches/${id}/results${state ? `?state=${state}` : ""}`),
};
