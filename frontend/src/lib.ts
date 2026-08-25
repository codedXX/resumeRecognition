import type { Batch, Candidate } from "./api";

export const canStart = (batch: Batch | null, roleId: string) => Boolean(roleId && batch?.files.some((file) => file.status === "ready") && batch.status === "pending");
export const statusLabel = (status: string) => ({ ready: "已就绪", pending: "等待中", processing: "正在评分", completed: "已完成", failed: "失败", unreadable: "无法读取" }[status] ?? status);
export const filterCandidates = (items: Candidate[], filter: string) => filter === "all" ? items : items.filter((item) => filter === "failed" ? item.file.status === "failed" : filter === "qualified" ? item.evaluation?.qualified : item.evaluation?.qualified === false);
