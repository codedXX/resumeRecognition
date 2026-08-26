import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type Candidate, type Role } from "./api";
import { canStart, diffMarkerForStatus, filterCandidates, statusLabel } from "./lib";
import { Select } from "./components/Select";

type DraftRequirement = { id?: string; description: string; priority: string };
type RoleDraft = { name: string; evaluation_prompt: string; passing_score: number; requirements: DraftRequirement[] };
const emptyDraft: RoleDraft = { name: "", evaluation_prompt: "", passing_score: 80, requirements: [] };
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = [".pdf", ".docx"];
type NoticeTone = "success" | "warning" | "error";
type Notice = { tone: NoticeTone; message: string };
type UploadIssue = { fileName: string; reason: string; detail?: string };
type UploadFeedback = { issues: UploadIssue[]; readyCount: number; totalCount: number };

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  const mib = bytes / (1024 * 1024);
  return `${Number.isInteger(mib) ? mib : mib.toFixed(2)} MiB`;
};

function preflightFiles(files: File[]) {
  const accepted: File[] = [];
  const issues: UploadIssue[] = [];
  files.forEach((file) => {
    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      issues.push({ fileName: file.name, reason: "文件类型不支持", detail: "请选择 PDF 或 DOCX 文件。" });
    } else if (file.size > MAX_UPLOAD_BYTES) {
      issues.push({ fileName: file.name, reason: `文件超过 ${formatFileSize(MAX_UPLOAD_BYTES)} 大小限制`, detail: `当前大小 ${formatFileSize(file.size)}（${file.size.toLocaleString()} B），上限 ${formatFileSize(MAX_UPLOAD_BYTES)}。请压缩或重新选择文件。` });
    } else {
      accepted.push(file);
    }
  });
  return { accepted, issues };
}

export function App() {
  const client = useQueryClient();
  const [roleId, setRoleId] = useState("");
  const [batchId, setBatchId] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [uploadFeedback, setUploadFeedback] = useState<UploadFeedback | null>(null);
  const [roleAttention, setRoleAttention] = useState(false);
  const roleSelectRef = useRef<HTMLButtonElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const roles = useQuery({ queryKey: ["roles"], queryFn: api.roles });
  const batch = useQuery({ queryKey: ["batch", batchId], queryFn: () => api.batch(batchId!), enabled: Boolean(batchId), refetchInterval: (query) => query.state.data?.status === "processing" ? 2000 : false });
  const results = useQuery({ queryKey: ["results", batchId], queryFn: () => api.results(batchId!), enabled: Boolean(batchId), refetchInterval: batch.data?.status === "processing" ? 2000 : false });
  const visibleCandidates = useMemo(() => filterCandidates(results.data ?? [], filter), [results.data, filter]);

  const upload = useMutation({
    mutationFn: async ({ files, localIssues }: { files: File[]; localIssues: UploadIssue[] }) => {
      const created = batchId ? null : await api.createBatch();
      const id = created?.id ?? batchId!;
      const uploaded = await api.upload(id, files);
      return { id, uploaded, localIssues };
    },
    onSuccess: ({ id, uploaded, localIssues }) => {
      setBatchId(id);
      client.invalidateQueries({ queryKey: ["batch", id] });
      const failed = uploaded.filter((file) => file.status === "failed" || file.status === "unreadable").map((file) => ({ fileName: file.original_name, reason: statusLabel(file.status), detail: file.error ?? "服务未返回具体原因，请稍后重试。" }));
      const issues = [...localIssues, ...failed];
      const readyCount = uploaded.filter((file) => file.status === "ready").length;
      setUploadFeedback(issues.length ? { issues, readyCount, totalCount: uploaded.length + localIssues.length } : null);
      setNotice(issues.length ? { tone: readyCount ? "warning" : "error", message: readyCount ? `${readyCount} 份文件已就绪，另有 ${issues.length} 份需要处理。` : "上传未完成，请根据提示重新选择文件。" } : { tone: "success", message: "文件已准备完成；选择岗位后可开始评估。" });
      setRoleAttention(!roleId && readyCount > 0);
    },
    onError: (error: Error) => setNotice({ tone: "error", message: `${error.message}。请检查网络后重试。` }),
  });
  const start = useMutation({
    mutationFn: () => api.start(batchId!, roleId),
    onSuccess: () => { client.invalidateQueries({ queryKey: ["batch", batchId] }); client.invalidateQueries({ queryKey: ["results", batchId] }); setNotice({ tone: "success", message: "评估已开始。此结果仅供人工复核，不会自动作出招聘决定。" }); },
    onError: (error: Error) => setNotice({ tone: "error", message: `${error.message}。请稍后重试，失败详情仍保留在队列中。` }),
  });

  useEffect(() => {
    if (roleAttention && !uploadFeedback && !roleId) roleSelectRef.current?.focus();
  }, [roleAttention, uploadFeedback, roleId]);

  const handleFilesSelected = (files: File[]) => {
    const { accepted, issues } = preflightFiles(files);
    if (!accepted.length) {
      setUploadFeedback({ issues, readyCount: 0, totalCount: files.length });
      setNotice({ tone: "error", message: "文件未上传，请根据提示重新选择文件。" });
      return;
    }
    upload.mutate({ files: accepted, localIssues: issues });
  };

  const selectedRole = roles.data?.find((role) => role.id === roleId);
  const startAllowed = canStart(batch.data ?? null, roleId);
  const hasReadableFile = Boolean(batch.data?.files.some((file) => file.status === "ready"));
  const startHelp = batch.data?.status === "expired" ? "本批次已过期，临时解析文本已清理，请重新上传。" : batch.data?.status === "processing" ? "评估进行中，请等待当前批次完成。" : batch.data?.status === "completed" ? "本批次已完成；如需重新评估，请重新上传文件。" : !roleId ? "请先选择岗位。" : !hasReadableFile ? "请添加至少一份可读取的 PDF 或 DOCX。" : "当前批次暂时无法开始评估，请稍后重试。";
  return <main className="app-shell">
    <header className="masthead">
      <div><p className="eyebrow">招聘评估</p><h1>简历评估档案台</h1><p className="command-line"> 评估 --岗位 {selectedRole?.name ?? "待选择岗位"}</p></div>
      <div className="human-review"><span className="status-marker">&gt;</span> 智能初筛建议<br /><strong>最终判断由招聘人员作出</strong></div>
    </header>
    <p className="privacy-note">简历仅用于本次分析，不保留原始文件；启用阿里百炼时，提取文本会由后端发送给评分服务。</p>
    <section className="role-strip" aria-label="当前岗位">
      <div className="role-command"><span>岗位</span><Select ref={roleSelectRef} value={roleId} options={(roles.data ?? []).map((role) => ({ value: role.id, label: `${role.name} · ${role.passing_score} 分合格` }))} placeholder="选择筛选岗位" onChange={(value) => { setRoleId(value); setRoleAttention(false); }} className={roleAttention ? "needs-attention" : ""} aria-label="选择岗位" aria-describedby={!roleId && roleAttention ? "role-help" : undefined} /></div>
      {selectedRole && <><span className="rule-version">/ 岗位要求 {selectedRole.requirements.length}</span><span className="threshold"><small>合格分数</small>≥ {selectedRole.passing_score}</span></>}
      <RoleManager roles={roles.data ?? []} onChanged={() => client.invalidateQueries({ queryKey: ["roles"] })} />
    </section>
    {notice && <p className={`notice notice-${notice.tone}`} role={notice.tone === "error" ? "alert" : "status"}>{notice.message}</p>}
    <section className="workbench" aria-label="简历审阅工作台">
      <aside className="queue-panel" data-review-region="queue">
        <div className="section-heading"><p className="eyebrow">文件队列</p><h2>待评估简历</h2><p className="section-caption">文件准备 · 仅解析文本</p></div>
        <label className="dropzone"><input ref={fileInputRef} type="file" accept=".pdf,.docx" multiple onChange={(event) => { if (event.target.files?.length) handleFilesSelected(Array.from(event.target.files)); event.currentTarget.value = ""; }} /><span>添加 PDF 或 DOCX</span><small>上传只解析文本，不会自动评分；单文件上限 {formatFileSize(MAX_UPLOAD_BYTES)}</small></label>
        <ul className="file-list">{batch.data?.files.map((file) => <li key={file.id}><span className={`file-status ${file.status}`} aria-hidden="true">{file.status === "failed" || file.status === "unreadable" ? "-" : file.status === "completed" ? "+" : "·"}</span><div><b>{file.original_name}</b><small>{statusLabel(file.status)}{file.error ? ` · ${file.error}` : ""}</small></div></li>)}</ul>
        {!batch.data?.files.length && <p className="empty-copy">还没有简历。先添加文件，再选择岗位标准。</p>}
        <button className="primary-action" aria-label="开始评估" disabled={!startAllowed || start.isPending} onClick={() => start.mutate()}><span>&gt;</span> {start.isPending ? "正在启动…" : "开始评估"}</button>
        {!startAllowed && <p id="role-help" className={`start-help ${roleAttention ? "needs-attention" : ""}`} role="alert">{startHelp}</p>}
        {batch.data && <div className="batch-counts" aria-label="批次进度">{Object.entries(batch.data.counts).filter(([, count]) => count > 0).map(([key, count]) => <span key={key}><b>{count}</b> {statusLabel(key)}</span>)}</div>}
      </aside>
      <section className="results-panel" data-review-region="candidates">
        <div className="result-toolbar"><div><p className="eyebrow">候选人</p><h2>候选人审阅记录</h2><p className="section-caption">{batch.data?.criteria_snapshot?.name ?? "选择岗位后开始"}</p></div><div className="filters" aria-label="结果筛选">{[["all", "全部"], ["qualified", "+ 合格"], ["unqualified", "- 不合格"], ["failed", "! 失败"]].map(([value, label]) => <button key={value} className={filter === value ? "active" : ""} onClick={() => setFilter(value)}>{label}</button>)}</div></div>
        <div className="candidate-list" role="list">{visibleCandidates.map((candidate) => <CandidateRow key={candidate.file.id} candidate={candidate} threshold={batch.data?.criteria_snapshot?.passing_score} selected={selected?.file.id === candidate.file.id} onSelect={() => setSelected(candidate)} />)}</div>
        {!visibleCandidates.length && <div className="result-empty"><span className="empty-marker">&gt;_</span><p>上传并启动评估后，候选人的证据会出现在这里。</p></div>}
      </section>
      <aside className="evidence-panel" data-review-region="evidence">{selected ? <EvidenceDetail candidate={selected} threshold={batch.data?.criteria_snapshot?.passing_score ?? 80} /> : <div className="evidence-empty"><span className="evidence-label">证据对照</span><h2>选择一份简历</h2><p>分数、理由和简历原文证据会在同一条评估轨道上呈现。</p><div className="evidence-empty-code"><span>01</span> 等待候选人选择<br /><span>02</span> 等待评估结果</div></div>}</aside>
    </section>
    <UploadFeedbackDialog feedback={uploadFeedback} onClose={() => setUploadFeedback(null)} onReselect={() => { setUploadFeedback(null); fileInputRef.current?.click(); }} />
  </main>;
}

function UploadFeedbackDialog({ feedback, onClose, onReselect }: { feedback: UploadFeedback | null; onClose: () => void; onReselect: () => void }) {
  return <Dialog.Root open={Boolean(feedback)} onOpenChange={(open) => { if (!open) onClose(); }}>
    <Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="dialog-content upload-feedback-dialog" role="alertdialog" aria-describedby="upload-feedback-description">
      <Dialog.Title>上传结果需要处理</Dialog.Title>
      <Dialog.Description id="upload-feedback-description">部分文件未能加入评估队列，请根据失败原因重新选择或处理文件。</Dialog.Description>
      {feedback && <><p className="upload-summary">{feedback.readyCount > 0 ? `${feedback.readyCount} 份文件已就绪，可选择岗位后开始评估。` : "没有文件就绪，请重新选择可读取的文件。"}</p><ul className="upload-issues">{feedback.issues.map((issue, index) => <li key={`${issue.fileName}-${index}`}><b>{issue.fileName}</b><span>{issue.reason}</span>{issue.detail && <small>{issue.detail}</small>}</li>)}</ul></>}
      <div className="dialog-actions"><button type="button" className="quiet-button" onClick={onClose}>关闭</button><button type="button" className="primary-action" onClick={onReselect}>重新选择文件</button></div>
    </Dialog.Content></Dialog.Portal>
  </Dialog.Root>;
}

function CandidateRow({ candidate, threshold, selected, onSelect }: { candidate: Candidate; threshold?: number; selected: boolean; onSelect: () => void }) {
  const evaluation = candidate.evaluation;
  const status = evaluation?.qualified === true ? "qualified" : evaluation?.qualified === false ? "unqualified" : "failed";
  const marker = diffMarkerForStatus(selected ? "selected" : status);
  const outcome = evaluation?.qualified === true ? "合格" : evaluation?.qualified === false ? "不合格" : statusLabel(candidate.file.status);
  return <button className={`candidate-row ${status} ${selected ? "selected" : ""}`} onClick={onSelect} aria-label={`${candidate.file.original_name}，${outcome}`}><span className="candidate-marker" aria-hidden="true">{marker}</span><span className={`score ${status}`}>{evaluation?.score ?? "—"}</span><span className="candidate-meta"><span className="candidate-name">{candidate.file.original_name.replace(/\.(pdf|docx)$/i, "")}</span><small>{outcome} · 合格线 {threshold ?? "—"}</small></span><span className="candidate-reason">{evaluation?.reason ?? candidate.file.error ?? "等待评估"}</span></button>;
}

function EvidenceDetail({ candidate, threshold }: { candidate: Candidate; threshold: number }) {
  const result = candidate.evaluation;
  if (!result) return <div className="evidence-empty"><p>尚未生成评分</p></div>;
  return <div className="detail"><span className="evidence-label">证据对照</span><h2> {candidate.file.original_name}</h2><div className={`detail-score ${result.qualified ? "qualified" : "unqualified"}`}><strong>{result.score ?? "—"}</strong><span>/ 100<br />阈值 {threshold}</span><b>{result.qualified ? "+ 合格" : "- 不合格"}</b></div><p className="decision">{result.qualified ? "+ 合格：" : "- 不合格："}{result.reason}</p><div className="finding-columns"><section><h3><span className="finding-marker plus">+</span>满足条件</h3>{result.satisfied.length ? <ul>{result.satisfied.map((item) => <li key={item}>+ {item}</li>)}</ul> : <p>未提供</p>}</section><section><h3><span className="finding-marker minus">-</span>待补证据</h3>{result.unmet.length ? <ul>{result.unmet.map((item) => <li key={item}>- {item}</li>)}</ul> : <p>无</p>}</section></div><section className="evidence-rail"><h3>&gt; 简历证据</h3>{result.evidence.map((item, index) => <article key={`${item.requirement}-${index}`}><span className="evidence-gutter">{String(index + 1).padStart(2, "0")}</span><div><b>+ {item.requirement}</b><blockquote>“{item.evidence}”</blockquote></div></article>)}</section><p className="review-note">智能辅助初筛结果，仅用于人工复核。不得基于敏感个人特征作出判断。</p></div>;
}

function RoleManager({ roles, onChanged }: { roles: Role[]; onChanged: () => void }) {
  const [open, setOpen] = useState(false); const [draft, setDraft] = useState<RoleDraft>(emptyDraft); const [editing, setEditing] = useState<Role | null>(null); const [error, setError] = useState(""); const [requirementsOpen, setRequirementsOpen] = useState(false); const [requirementsTouched, setRequirementsTouched] = useState(false);
  const save = useMutation({ mutationFn: async () => { const requirements = draft.requirements.filter((item) => item.description.trim()); if (!editing) return api.createRole({ ...draft, requirements: requirementsTouched ? requirements : [] }); await api.updateRole(editing.id, draft); if (!requirementsTouched) return api.roles(); const ids = new Set(requirements.flatMap((item) => item.id ? [item.id] : [])); await Promise.all(editing.requirements.filter((item) => !ids.has(item.id)).map((item) => api.deleteRequirement(editing.id, item.id))); const persisted = await Promise.all(requirements.map((item) => item.id ? api.updateRequirement(editing.id, item.id, item) : api.addRequirement(editing.id, item))); await api.reorderRequirements(editing.id, persisted.map((item) => item.id)); return api.roles(); }, onSuccess: () => { onChanged(); setOpen(false); setDraft(emptyDraft); setEditing(null); setRequirementsOpen(false); setRequirementsTouched(false); }, onError: (reason: Error) => setError(reason.message) });
  const remove = useMutation({ mutationFn: api.deleteRole, onSuccess: onChanged });
  const openCreate = () => { setEditing(null); setDraft(emptyDraft); setError(""); setRequirementsOpen(false); setRequirementsTouched(false); setOpen(true); };
  const openEdit = (role: Role) => { setEditing(role); setDraft({ name: role.name, evaluation_prompt: role.evaluation_prompt, passing_score: role.passing_score, requirements: role.requirements }); setError(""); setRequirementsOpen(role.requirements.length > 0); setRequirementsTouched(false); setOpen(true); };
  const updateRequirements = (next: RoleDraft) => { setRequirementsTouched(true); setDraft(next); };
  return <Dialog.Root open={open} onOpenChange={setOpen}><Dialog.Trigger asChild><button className="quiet-button" onClick={openCreate}>管理岗位</button></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="dialog-content"><Dialog.Title>{editing ? "编辑岗位规则" : "新建岗位规则"}</Dialog.Title><label>岗位名称<input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="例如：Python 后端工程师" /></label><label>合格线<input type="number" min="0" max="100" value={draft.passing_score} onChange={(event) => setDraft({ ...draft, passing_score: Number(event.target.value) })} /><small>默认 80 分，岗位可单独调整。</small></label><label>岗位规则<textarea aria-label="岗位规则" rows={8} value={draft.evaluation_prompt} onChange={(event) => setDraft({ ...draft, evaluation_prompt: event.target.value })} placeholder="粘贴完整岗位说明，可包含职责、任职要求、优先条件和备注。" /><small>保留原文段落，评估时由 AI 区分职责、必要条件与优先条件。</small></label><button type="button" className="advanced-toggle" aria-expanded={requirementsOpen} onClick={() => setRequirementsOpen((current) => !current)}>{requirementsOpen ? "收起高级评估要点" : "添加高级评估要点"}</button>{requirementsOpen && <RequirementsEditor draft={draft} setDraft={updateRequirements} />}{error && <p className="form-error">{error}</p>}<div className="dialog-actions">{editing && <button className="danger" onClick={() => remove.mutate(editing.id)}>删除岗位</button>}<Dialog.Close asChild><button className="quiet-button">取消</button></Dialog.Close><button className="primary-action" disabled={!draft.name.trim() || !draft.evaluation_prompt.trim() || draft.passing_score < 0 || draft.passing_score > 100} onClick={() => save.mutate()}>保存岗位</button></div>{roles.length > 0 && !editing && <div className="existing-roles"><h3>已有岗位</h3>{roles.map((role) => <button key={role.id} onClick={() => openEdit(role)}>{role.name}<span>{role.passing_score} 分</span></button>)}</div>}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}

function RequirementsEditor({ draft, setDraft }: { draft: RoleDraft; setDraft: (draft: RoleDraft) => void }) {
  const add = () => setDraft({ ...draft, requirements: [...draft.requirements, { description: "", priority: "required" }] });
  const move = (index: number, offset: number) => { const target = index + offset; if (target < 0 || target >= draft.requirements.length) return; const requirements = [...draft.requirements]; [requirements[index], requirements[target]] = [requirements[target], requirements[index]]; setDraft({ ...draft, requirements }); };
  return <fieldset><legend>岗位要求</legend>{draft.requirements.map((requirement, index) => <div className="requirement-input" key={requirement.id ?? index}><input value={requirement.description} onChange={(event) => { const requirements = [...draft.requirements]; requirements[index] = { ...requirement, description: event.target.value }; setDraft({ ...draft, requirements }); }} placeholder="例如：3 年 Python 项目经验" /><Select value={requirement.priority} options={[{ value: "required", label: "必要" }, { value: "preferred", label: "加分" }]} placeholder="优先级" onChange={(value) => { const requirements = [...draft.requirements]; requirements[index] = { ...requirement, priority: value }; setDraft({ ...draft, requirements }); }} aria-label={`第 ${index + 1} 条要求优先级`} /><span className="requirement-controls"><button type="button" aria-label="上移要求" onClick={() => move(index, -1)}>↑</button><button type="button" aria-label="下移要求" onClick={() => move(index, 1)}>↓</button><button type="button" className="remove-requirement" aria-label="删除该要求" onClick={() => setDraft({ ...draft, requirements: draft.requirements.filter((_, itemIndex) => itemIndex !== index) })}>×</button></span></div>)}<button type="button" className="add-requirement" onClick={add}>+ 添加要求</button></fieldset>;
}
