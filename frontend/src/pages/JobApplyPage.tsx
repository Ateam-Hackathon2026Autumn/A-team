import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router';
import { applyJob, getJob } from '../api/jobApi';
import { payLabel } from '../components/jobs/JobCard';
import Button from '../components/ui/Button';
import { ContentPage, ContentStatus, dateLabel, fieldClass, panelClass, textLinkClass } from '../components/ui/ContentPage';
import { USE_MOCK } from '../config/env';
import { usePublicContent } from '../hooks/usePublicContent';

export default function JobApplyPage() {
  const { jobId } = useParams();
  return <JobForm key={jobId} id={Number(jobId)} />;
}
function JobForm({ id }: { id: number }) {
  const loader = useCallback((signal: AbortSignal) => getJob(id, signal), [id]);
  const state = usePublicContent(loader);
  const [dates, setDates] = useState<number[]>([]);
  const [message, setMessage] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [receipt, setReceipt] = useState<number | null>(null);
  const locked = useRef(false);
  const formPanel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (confirming || receipt !== null) formPanel.current?.focus();
  }, [confirming, receipt]);
  const job = state.data;
  const available = job?.workDates.items.filter(day => day.isSelectable && day.remainingCount > 0) ?? [];
  function validate() {
    if (!dates.length || dates.some(id => !available.some(day => day.id === id))) { setError('勤務希望日を1日以上選択してください。応募条件もご確認ください。'); return false; }
    return true;
  }
  async function submit() {
    if (locked.current || !validate()) return;
    locked.current = true; setSending(true); setError('');
    try { const result = await applyJob(id, { workDateIds: dates, message: message.trim(), answers: [] }); setReceipt(result.id); }
    catch (cause) { setError(cause instanceof Error ? cause.message : '応募できませんでした。'); }
    finally { locked.current = false; setSending(false); }
  }
  return <ContentPage eyebrow="JOB APPLICATION" title="求人への応募">
    <Link to={`/jobs/${id}`} className={textLinkClass}>← 求人詳細</Link><ContentStatus {...state} />
    {job && <div ref={formPanel} tabIndex={-1} className="mx-auto mt-5 max-w-3xl"><h2 className="font-serif text-xl">{job.title}</h2><p>{job.producer.businessName} ・ {payLabel(job)}</p>
      {receipt !== null ? <section role="status" className={panelClass}><h2 className="font-serif text-2xl">デモ応募を受け付けました</h2><p>受付番号：{receipt}</p><p>応募は採用の確定を意味しません。実際の応募・通知は行いません。</p><Link to="/mypage/jobs" className={textLinkClass}>応募状況を見る →</Link></section> : !job.isAcceptingApplications || !available.length ? <p role="status" className={panelClass}>現在応募を受け付けていません。</p> : <form noValidate className={panelClass} onSubmit={event => { event.preventDefault(); if (!confirming) { if (validate()) { setConfirming(true); setError(''); } } else void submit(); }}>
        <p className="text-sm font-bold text-marche-green">{confirming ? '2. 応募内容を確認' : '1. 応募内容を入力'}</p>
        {!confirming ? <>
          <fieldset className="m-0 border-0 p-0" aria-describedby={error ? 'job-error' : undefined}><legend className="font-bold">勤務希望日（1日以上選択）</legend>{job.workDates.items.map(day => <label key={day.id} className="my-2 flex min-h-12 items-center gap-3 rounded-xl border border-marche-line p-3"><input type="checkbox" className="size-5 accent-marche-green" disabled={!day.isSelectable || day.remainingCount <= 0} checked={dates.includes(day.id)} onChange={event => setDates(previous => event.target.checked ? [...previous, day.id] : previous.filter(id => id !== day.id))} />{dateLabel(day.workDate)} ・ {day.isSelectable && day.remainingCount > 0 ? `残り${day.remainingCount}名` : '受付終了'}</label>)}</fieldset>
          <h3 className="text-base">応募条件</h3><ul className="pl-5">{job.requirements.map(item => <li key={item}>{item}</li>)}</ul>
          <label htmlFor="job-message" className="mb-2 mt-5 block font-bold">ひとことメッセージ（任意）</label><textarea id="job-message" className={fieldClass} rows={5} maxLength={2000} value={message} onChange={event => setMessage(event.target.value)} />
          <p className="text-sm text-marche-muted">登録済みのプロフィール情報と応募内容を生産者が確認します。</p>
        </> : <section aria-label="応募内容の確認"><h3 className="text-lg">勤務希望日</h3><ul className="pl-5">{available.filter(day => dates.includes(day.id)).map(day => <li key={day.id}>{dateLabel(day.workDate)}</li>)}</ul><h3 className="text-lg">メッセージ</h3><p className="whitespace-pre-wrap">{message || 'なし'}</p></section>}
        {error && <p id="job-error" role="alert" className="text-marche-red">{error}</p>}
        {!USE_MOCK && <p className="text-marche-red">実際の応募送信は準備中です。</p>}
        <div className="mt-6 flex flex-wrap gap-3">{confirming && <Button variant="outline" disabled={sending} onClick={() => { setConfirming(false); setError(''); }}>入力内容を修正</Button>}<Button type="submit" disabled={sending || (confirming && !USE_MOCK)}>{sending ? '送信中…' : confirming ? 'デモ応募を送信する' : '応募内容を確認する'}</Button></div>
      </form>}
    </div>}
  </ContentPage>;
}
