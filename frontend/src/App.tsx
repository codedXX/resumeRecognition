import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, type Candidate, type Role } from "./api";
import { canStart, filterCandidates, statusLabel } from "./lib";

type DraftRequirement = { id?: string; description: string; priority: string };
type RoleDraft = { name: string; evaluation_prompt: string; passing_score: number; requirements: DraftRequirement[] };
const emptyDraft: RoleDraft = { name: "", evaluation_prompt: "根据岗位要求评分并引用简历原文。", passing_score: 80, requirements: [] };

export function App() {
  const client = useQueryClient();
  const [roleId, setRoleId] = useState("");
  const [batchId, setBatchId] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [notice, setNotice] = useState("");
  const roles = useQuery({ queryKey: ["roles"], queryFn: api.roles });
  const batch = useQuery({ queryKey: ["batch", batchId], queryFn: () => api.batch(batchId!), enabled: Boolean(batchId), refetchInterval: (query) => query.state.data?.status === "processing" ? 2000 : false });
  const results = useQuery({ queryKey: ["results", batchId], queryFn: () => api.results(batchId!), enabled: Boolean(batchId), refetchInterval: batch.data?.status === "processing" ? 2000 : false });
  const visibleCandidates = useMemo(() => filterCandidates(results.data ?? [], filter), [results.data, filter]);

  const upload = useMutation({
    mutationFn: async (files: File[]) => {
      const created = batchId ? null : await api.createBatch();
      const id = created?.id ?? batchId!;
      await api.upload(id, files);
      return id;
    },
    onSuccess: (id) => { setBatchId(id); client.invalidateQueries({ queryKey: ["batch", id] }); setNotice("文件已准备完成；选择岗位后可开始评估。"); },
    onError: (error: Error) => setNotice(error.message),
  });
  const start = useMutation({
    mutationFn: () => api.start(batchId!, roleId),
    onSuccess: () => { client.invalidateQueries({ queryKey: ["batch", batchId] }); client.invalidateQueries({ queryKey: ["results", batchId] }); setNotice("评估已开始。此结果仅供人工复核，不会自动作出招聘决定。"); },
    onError: (error: Error) => setNotice(error.message),
  });

  const selectedRole = roles.data?.find((role) => role.id === roleId);
  const startAllowed = canStart(batch.data ?? null, roleId);
  return <main className="app-shell">
    <header className="masthead">
      <div><p className="eyebrow">RECRUIT REVIEW / 证据优先</p><h1>简历评估档案台</h1></div>
      <div className="human-review">AI 初筛建议<br /><strong>最终判断由招聘人员作出</strong></div>
    </header>
    <section className="role-strip" aria-label="当前岗位">
      <div><span>当前岗位</span><select value={roleId} onChange={(event) => setRoleId(event.target.value)} aria-label="选择岗位"><option value="">选择筛选岗位</option>{roles.data?.map((role) => <option key={role.id} value={role.id}>{role.name} · {role.passing_score} 分合格</option>)}</select></div>
      {selectedRole && <><span className="rule-version">规则 {selectedRole.requirements.length} 条</span><span className="threshold">≥ {selectedRole.passing_score}<small>合格线</small></span></>}
      <RoleManager roles={roles.data ?? []} onChanged={() => client.invalidateQueries({ queryKey: ["roles"] })} />
    </section>
    {notice && <p className="notice" role="status">{notice}</p>}
    <section className="workbench">
      <aside className="queue-panel">
        <div className="section-heading"><p className="eyebrow">01 / 文件队列</p><h2>待评估简历</h2></div>
        <label className="dropzone"><input type="file" accept=".pdf,.docx" multiple onChange={(event) => event.target.files?.length && upload.mutate(Array.from(event.target.files))} /><span>添加 PDF 或 DOCX</span><small>上传只解析文本，不会自动评分</small></label>
        <ul className="file-list">{batch.data?.files.map((file) => <li key={file.id}><span className={`file-status ${file.status}`}></span><div><b>{file.original_name}</b><small>{statusLabel(file.status)}{file.error ? ` · ${file.error}` : ""}</small></div></li>)}</ul>
        {!batch.data?.files.length && <p className="empty-copy">还没有简历。先添加文件，再选择岗位标准。</p>}
        <button className="primary-action" disabled={!startAllowed || start.isPending} onClick={() => start.mutate()}>{start.isPending ? "正在启动…" : "开始评估"}</button>
        {!startAllowed && <p className="start-help">{!roleId ? "请先选择岗位。" : "请添加至少一份可读取的 PDF 或 DOCX。"}</p>}
        {batch.data && <div className="batch-counts" aria-label="批次进度">{Object.entries(batch.data.counts).filter(([, count]) => count > 0).map(([key, count]) => <span key={key}>{count} {statusLabel(key)}</span>)}</div>}
      </aside>
      <section className="results-panel">
        <div className="result-toolbar"><div><p className="eyebrow">02 / 审阅结果</p><h2>{batch.data?.criteria_snapshot?.name ?? "选择岗位后开始"}</h2></div><div className="filters" aria-label="结果筛选">{[["all", "全部"], ["qualified", "合格"], ["unqualified", "不合格"], ["failed", "失败"]].map(([value, label]) => <button key={value} className={filter === value ? "active" : ""} onClick={() => setFilter(value)}>{label}</button>)}</div></div>
        <div className="candidate-list" role="list">{visibleCandidates.map((candidate) => <CandidateRow key={candidate.file.id} candidate={candidate} threshold={batch.data?.criteria_snapshot?.passing_score} selected={selected?.file.id === candidate.file.id} onSelect={() => setSelected(candidate)} />)}</div>
        {!visibleCandidates.length && <div className="result-empty"><span>档</span><p>上传并启动评估后，候选人的证据会出现在这里。</p></div>}
      </section>
      <aside className="evidence-panel">{selected ? <EvidenceDetail candidate={selected} threshold={batch.data?.criteria_snapshot?.passing_score ?? 80} /> : <div className="evidence-empty"><p className="eyebrow">03 / 证据档案</p><span>↳</span><h2>选择一份简历</h2><p>分数、理由和简历原文证据会在同一条评估轨道上呈现。</p></div>}</aside>
    </section>
  </main>;
}

function CandidateRow({ candidate, threshold, selected, onSelect }: { candidate: Candidate; threshold?: number; selected: boolean; onSelect: () => void }) {
  const evaluation = candidate.evaluation;
  const status = evaluation?.qualified === true ? "qualified" : evaluation?.qualified === false ? "unqualified" : "failed";
  return <button className={`candidate-row ${selected ? "selected" : ""}`} onClick={onSelect} role="listitem"><span className={`score ${status}`}>{evaluation?.score ?? "—"}</span><span className="candidate-name">{candidate.file.original_name.replace(/\.(pdf|docx)$/i, "")}</span><span className={`outcome ${status}`}>{evaluation?.qualified === true ? "合格" : evaluation?.qualified === false ? "不合格" : statusLabel(candidate.file.status)}</span><span className="mini-rail" aria-hidden="true"></span><span className="candidate-reason">{evaluation?.reason ?? candidate.file.error ?? "等待评估"}</span><small>合格线 {threshold ?? "—"}</small></button>;
}

function EvidenceDetail({ candidate, threshold }: { candidate: Candidate; threshold: number }) {
  const result = candidate.evaluation;
  if (!result) return <div className="evidence-empty"><p>尚未生成评分</p></div>;
  return <div className="detail"><p className="eyebrow">03 / 证据档案</p><h2>{candidate.file.original_name}</h2><div className={`detail-score ${result.qualified ? "qualified" : "unqualified"}`}><strong>{result.score ?? "—"}</strong><span>/ 100<br />阈值 {threshold}</span></div><p className="decision">{result.qualified ? "合格：" : "不合格："}{result.reason}</p><div className="finding-columns"><section><h3>满足条件</h3>{result.satisfied.length ? <ul>{result.satisfied.map((item) => <li key={item}>✓ {item}</li>)}</ul> : <p>未提供</p>}</section><section><h3>待补证据</h3>{result.unmet.length ? <ul>{result.unmet.map((item) => <li key={item}>— {item}</li>)}</ul> : <p>无</p>}</section></div><section className="evidence-rail"><h3>简历证据</h3>{result.evidence.map((item, index) => <article key={`${item.requirement}-${index}`}><span></span><div><b>{item.requirement}</b><blockquote>“{item.evidence}”</blockquote></div></article>)}</section><p className="review-note">AI 辅助初筛结果，仅用于人工复核。不得基于敏感个人特征作出判断。</p></div>;
}

function RoleManager({ roles, onChanged }: { roles: Role[]; onChanged: () => void }) {
  const [open, setOpen] = useState(false); const [draft, setDraft] = useState<RoleDraft>(emptyDraft); const [editing, setEditing] = useState<Role | null>(null); const [error, setError] = useState("");
  const save = useMutation({ mutationFn: async () => { const requirements = draft.requirements.filter((item) => item.description.trim()); if (!editing) return api.createRole({ ...draft, requirements }); await api.updateRole(editing.id, draft); const ids = new Set(requirements.flatMap((item) => item.id ? [item.id] : [])); await Promise.all(editing.requirements.filter((item) => !ids.has(item.id)).map((item) => api.deleteRequirement(editing.id, item.id))); const persisted = await Promise.all(requirements.map((item) => item.id ? api.updateRequirement(editing.id, item.id, item) : api.addRequirement(editing.id, item))); await api.reorderRequirements(editing.id, persisted.map((item) => item.id)); return api.roles(); }, onSuccess: () => { onChanged(); setOpen(false); setDraft(emptyDraft); setEditing(null); }, onError: (reason: Error) => setError(reason.message) });
  const remove = useMutation({ mutationFn: api.deleteRole, onSuccess: onChanged });
  const openCreate = () => { setEditing(null); setDraft(emptyDraft); setError(""); setOpen(true); };
  const openEdit = (role: Role) => { setEditing(role); setDraft({ name: role.name, evaluation_prompt: role.evaluation_prompt, passing_score: role.passing_score, requirements: role.requirements }); setError(""); setOpen(true); };
  return <Dialog.Root open={open} onOpenChange={setOpen}><Dialog.Trigger asChild><button className="quiet-button" onClick={openCreate}>管理岗位</button></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="dialog-content"><Dialog.Title>{editing ? "编辑岗位规则" : "新建岗位规则"}</Dialog.Title><label>岗位名称<input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="例如：Python 后端工程师" /></label><label>合格线<input type="number" min="0" max="100" value={draft.passing_score} onChange={(event) => setDraft({ ...draft, passing_score: Number(event.target.value) })} /><small>默认 80 分，岗位可单独调整。</small></label><label>筛选提示词<textarea value={draft.evaluation_prompt} onChange={(event) => setDraft({ ...draft, evaluation_prompt: event.target.value })} /></label><RequirementsEditor draft={draft} setDraft={setDraft} />{error && <p className="form-error">{error}</p>}<div className="dialog-actions">{editing && <button className="danger" onClick={() => remove.mutate(editing.id)}>删除岗位</button>}<Dialog.Close asChild><button className="quiet-button">取消</button></Dialog.Close><button className="primary-action" disabled={!draft.name || !draft.evaluation_prompt || draft.passing_score < 0 || draft.passing_score > 100} onClick={() => save.mutate()}>保存岗位</button></div>{roles.length > 0 && !editing && <div className="existing-roles"><h3>已有岗位</h3>{roles.map((role) => <button key={role.id} onClick={() => openEdit(role)}>{role.name}<span>{role.passing_score} 分</span></button>)}</div>}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}

function RequirementsEditor({ draft, setDraft }: { draft: RoleDraft; setDraft: (draft: RoleDraft) => void }) {
  const add = () => setDraft({ ...draft, requirements: [...draft.requirements, { description: "", priority: "required" }] });
  const move = (index: number, offset: number) => { const target = index + offset; if (target < 0 || target >= draft.requirements.length) return; const requirements = [...draft.requirements]; [requirements[index], requirements[target]] = [requirements[target], requirements[index]]; setDraft({ ...draft, requirements }); };
  return <fieldset><legend>岗位要求</legend>{draft.requirements.map((requirement, index) => <div className="requirement-input" key={requirement.id ?? index}><input value={requirement.description} onChange={(event) => { const requirements = [...draft.requirements]; requirements[index] = { ...requirement, description: event.target.value }; setDraft({ ...draft, requirements }); }} placeholder="例如：3 年 Python 项目经验" /><select value={requirement.priority} onChange={(event) => { const requirements = [...draft.requirements]; requirements[index] = { ...requirement, priority: event.target.value }; setDraft({ ...draft, requirements }); }}><option value="required">必要</option><option value="preferred">加分</option></select><span className="requirement-controls"><button type="button" aria-label="上移要求" onClick={() => move(index, -1)}>↑</button><button type="button" aria-label="下移要求" onClick={() => move(index, 1)}>↓</button><button type="button" className="remove-requirement" aria-label="删除该要求" onClick={() => setDraft({ ...draft, requirements: draft.requirements.filter((_, itemIndex) => itemIndex !== index) })}>×</button></span></div>)}<button type="button" className="add-requirement" onClick={add}>+ 添加要求</button></fieldset>;
}
