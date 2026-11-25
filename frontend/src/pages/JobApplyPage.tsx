import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import { applyJob, getJob } from "../api/jobApi";
import { payLabel } from "../components/jobs/JobCard";
import Button from "../components/ui/Button";
import { ContentPage, ContentStatus, dateLabel, fieldClass, panelClass, textLinkClass } from "../components/ui/ContentPage";
import { USE_MOCK } from "../config/env";
import { usePublicContent } from "../hooks/usePublicContent";
import ApiError from "../api/apiError";

export default function JobApplyPage() {
  const { jobId } = useParams();
  return (
    <JobForm
      key={jobId}
      id={Number(jobId)}
    />
  );
}
function JobForm({ id }: { id: number }) {
  const loader = useCallback((signal: AbortSignal) => getJob(id, signal), [id]);
  const state = usePublicContent(loader);
  const [dates, setDates] = useState<number[]>([]);
  const [message, setMessage] = useState("");
  const [requirementsConfirmed, setRequirementsConfirmed] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loginRequired, setLoginRequired] = useState(false);
  const [alreadyApplied, setAlreadyApplied] = useState(false);
  const [ownApplication, setOwnApplication] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState("");
  const [dateError, setDateError] = useState(false);
  const [validationAttempt, setValidationAttempt] = useState(0);
  const [sending, setSending] = useState(false);
  const [receipt, setReceipt] = useState<number | null>(null);
  const locked = useRef(false);
  const formPanel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (confirming || receipt !== null) formPanel.current?.focus();
  }, [confirming, receipt]);
  useEffect(() => {
    if (dateError && !confirming) formPanel.current?.querySelector<HTMLElement>('input[type="checkbox"]:not(:disabled)')?.focus();
  }, [dateError, validationAttempt, confirming]);
  const job = state.data;
  const available = job?.workDates.items.filter((day) => day.isSelectable && day.remainingCount > 0) ?? [];
  // APIが応募可かつ勤務日0件なら、勤務日を指定しない求人。
  const withoutDates = job?.workDates.total === 0;
  function validate() {
    const invalidDates = !withoutDates && (!dates.length || dates.length > 100 || new Set(dates).size !== dates.length
      || dates.some((id) => !available.some((day) => day.id === id)));
    const next: Record<string, string> = {};
    if (!requirementsConfirmed) next.requirementsConfirmed = "応募条件の確認が必要です。";
    if (Array.from(message.trim()).length > 2000) next.message = "メッセージは2000文字以内で入力してください。";
    setFieldErrors(next);
    setDateError(invalidDates);
    setValidationAttempt(value => value + 1);
    if (!job?.isAcceptingApplications || job.hasApplied || alreadyApplied || invalidDates || Object.keys(next).length) {
      setConfirming(false);
      setError(invalidDates ? "勤務希望日を1〜100日選択してください。" : "募集状況と入力内容をご確認ください。");
      return false;
    }
    return true;
  }
  async function submit() {
    if (locked.current || !validate()) return;
    locked.current = true;
    setSending(true);
    setError("");
    setLoginRequired(false);
    try {
      const result = await applyJob(id, { workDateIds: withoutDates ? [] : dates, message: message.trim() || null, answers: [], requirementsConfirmed });
      setReceipt(result.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "応募できませんでした。");
      if (cause instanceof ApiError) {
        setLoginRequired(cause.status === 401);
        if (cause.status === 400) {
          if (cause.details.workDateIds) setError(cause.details.workDateIds.join(' '));
          setConfirming(false);
          setDateError(Boolean(cause.details.workDateIds));
          setValidationAttempt(value => value + 1);
          setFieldErrors(Object.fromEntries(Object.entries(cause.details)
            .filter(([key]) => ['requirementsConfirmed', 'message'].includes(key))
            .map(([key, messages]) => [key, messages.join(' ')])));
        } else if (cause.status === 409 && cause.errorCode === 'ALREADY_APPLIED') {
          setAlreadyApplied(true);
        } else if (cause.status === 409 && cause.errorCode === 'CANNOT_APPLY_OWN') {
          setOwnApplication(true);
          setError('');
        } else if (cause.status === 409 && ['JOB_NOT_ACCEPTING', 'WORK_DATE_UNAVAILABLE'].includes(cause.errorCode ?? '')) {
          setConfirming(false); setDates([]); setRequirementsConfirmed(false); setFieldErrors({});
          state.retry();
        }
      }
    } finally {
      locked.current = false;
      setSending(false);
    }
  }
  return (
    <ContentPage
      eyebrow="JOB APPLICATION"
      title="求人への応募"
    >
      <Link
        to={`/jobs/${id}`}
        className={textLinkClass}
      >
        ← 求人詳細
      </Link>
      <ContentStatus {...state} notFoundTo="/jobs" />
      {error && <p id="job-error" role="alert" className="text-marche-red">{error}</p>}
      {loginRequired && <Link to="/signin" state={{ from: `/jobs/${id}/apply` }} className={textLinkClass}>ログインして応募する →</Link>}
      {job && (
        <div
          ref={formPanel}
          tabIndex={-1}
          className="mx-auto mt-5 max-w-3xl"
        >
          <h2 className="font-serif text-xl">{job.title}</h2>
          <p>
            {job.producer.businessName} ・ {payLabel(job)}
          </p>
          {receipt !== null ? (
            <section
              role="status"
              className={panelClass}
            >
              <h2 className="font-serif text-2xl">{USE_MOCK ? "デモ応募を受け付けました" : "応募を受け付けました"}</h2>
              <p>受付番号：{receipt}</p>
              <p>応募は採用の確定を意味しません。</p>
              {USE_MOCK && <p>実際の応募・通知は行いません。</p>}
              <Link
                to="/mypage/jobs"
                className={textLinkClass}
              >
                応募状況を見る →
              </Link>
            </section>
          ) : ownApplication ? (
            <p className={panelClass}>自分の求人には応募できません。</p>
          ) : job.hasApplied || alreadyApplied ? (
            <p className={panelClass}>この求人には応募済みです。<Link to="/mypage/jobs" className={textLinkClass}>応募状況を見る →</Link></p>
          ) : !job.isAcceptingApplications || (!withoutDates && !available.length) ? (
            <p
              role="status"
              className={panelClass}
            >
              現在応募を受け付けていません。
            </p>
          ) : (
            <form
              noValidate
              className={panelClass}
              onSubmit={(event) => {
                event.preventDefault();
                if (!confirming) {
                  if (validate()) {
                    setConfirming(true);
                    setError("");
                  }
                } else void submit();
              }}
            >
              <p className="text-sm font-bold text-marche-green">{confirming ? "2. 応募内容を確認" : "1. 応募内容を入力"}</p>
              {!confirming ? (
                <>
                  {withoutDates ? <p>勤務日の指定はありません。</p> : <fieldset
                    className="m-0 border-0 p-0"
                    aria-invalid={dateError}
                    aria-describedby={dateError ? "job-error" : undefined}
                  >
                    <legend className="font-bold">勤務希望日（1日以上選択）</legend>
                    {job.workDates.items.map((day) => (
                      <label
                        key={day.id}
                        className="my-2 flex min-h-12 items-center gap-3 rounded-xl border border-marche-line p-3"
                      >
                        <input
                          aria-invalid={dateError}
                          aria-describedby={dateError ? "job-error" : undefined}
                          type="checkbox"
                          className="size-5 accent-marche-green"
                          disabled={!day.isSelectable || day.remainingCount <= 0}
                          checked={dates.includes(day.id)}
                          onChange={(event) => setDates((previous) => (event.target.checked ? [...previous, day.id] : previous.filter((id) => id !== day.id)))}
                        />
                        {dateLabel(day.workDate)} ・ {day.isSelectable && day.remainingCount > 0 ? `残り${day.remainingCount}名` : "受付終了"}
                      </label>
                    ))}
                  </fieldset>}
                  <h3 className="text-base">応募条件</h3>
                  <ul className="pl-5">
                    {(job.requirements ?? []).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <label className="flex min-h-11 items-start gap-3">
                    <input id="requirements-confirmed" type="checkbox" className="mt-2 size-5 shrink-0 accent-marche-green"
                      checked={requirementsConfirmed} onChange={event => setRequirementsConfirmed(event.target.checked)}
                      aria-invalid={Boolean(fieldErrors.requirementsConfirmed)}
                      aria-describedby={fieldErrors.requirementsConfirmed ? "requirements-error" : undefined} />
                    応募条件を確認しました
                  </label>
                  {fieldErrors.requirementsConfirmed && <p id="requirements-error" role="alert" className="text-marche-red">{fieldErrors.requirementsConfirmed}</p>}
                  <label
                    htmlFor="job-message"
                    className="mb-2 mt-5 block font-bold"
                  >
                    ひとことメッセージ（任意）
                  </label>
                  <textarea
                    id="job-message"
                    className={fieldClass}
                    rows={5}
                    maxLength={2000}
                    value={message}
                    aria-invalid={Boolean(fieldErrors.message)}
                    aria-describedby={fieldErrors.message ? "message-error" : undefined}
                    onChange={(event) => setMessage(event.target.value)}
                  />
                  {fieldErrors.message && <p id="message-error" role="alert" className="text-marche-red">{fieldErrors.message}</p>}
                  <p className="text-sm text-marche-muted">登録済みのプロフィール情報と応募内容を生産者が確認します。</p>
                </>
              ) : (
                <section aria-label="応募内容の確認">
                  <h3 className="text-lg">勤務希望日</h3>
                  {withoutDates && <p>勤務日の指定なし</p>}
                  <ul className="pl-5">
                    {available
                      .filter((day) => dates.includes(day.id))
                      .map((day) => (
                        <li key={day.id}>{dateLabel(day.workDate)}</li>
                      ))}
                  </ul>
                  <h3 className="text-lg">メッセージ</h3>
                  <p className="whitespace-pre-wrap">{message || "なし"}</p>
                  <p>応募条件：確認済み</p>
                </section>
              )}
              <div className="mt-6 flex flex-wrap gap-3">
                {confirming && (
                  <Button
                    variant="outline"
                    disabled={sending}
                    onClick={() => {
                      setConfirming(false);
                      setError("");
                    }}
                  >
                    入力内容を修正
                  </Button>
                )}
                <Button
                  type="submit"
                  disabled={sending}
                >
                  {sending ? "送信中…" : confirming ? (USE_MOCK ? "デモ応募を送信する" : "応募を送信する") : "応募内容を確認する"}
                </Button>
              </div>
            </form>
          )}
        </div>
      )}
    </ContentPage>
  );
}
