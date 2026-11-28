import { useRef, useState } from 'react';
import { Link } from 'react-router';

import {
  cancelExperienceApplication,
  getExperienceApplications,
} from '../api/experienceApi';
import MyPageNavigation from '../components/mypage/MyPageNavigation';
import Button from '../components/ui/Button';
import {
  ContentPage,
  ContentStatus,
  EmptyContent,
} from '../components/ui/ContentPage';
import {
  dateLabel,
  linkClass,
  panelClass,
  textLinkClass,
  timeLabel,
  yen,
} from '../components/ui/contentPageValues';
import { usePublicContent } from '../hooks/usePublicContent';
import type { MyExperienceApplication } from '../types/experience';

const STATUS_LABELS: Record<string, string> = {
  applied: '申込済み',
  confirmed: '予約確定',
  canceled: 'キャンセル済み',
  attended: '参加済み',
};

const STATUS_CLASSES: Record<string, string> = {
  applied: 'bg-marche-sage text-marche-green',
  confirmed: 'bg-marche-sage text-marche-green',
  canceled: 'bg-marche-red/15 text-marche-red',
  attended: 'bg-marche-canvas text-marche-muted',
};

function participantText(app: MyExperienceApplication): string {
  const parts = [`大人 ${app.adultCount}名`];
  if (app.childCount > 0) parts.push(`子ども ${app.childCount}名`);
  if (app.infantCount > 0) parts.push(`未就学児 ${app.infantCount}名`);
  const total = app.adultCount + app.childCount + app.infantCount;
  return `${parts.join('・')}（計 ${total}名）`;
}

export default function ExperienceApplicationsPage() {
  const state = usePublicContent(getExperienceApplications);
  const [canceledMap, setCanceledMap] = useState<
    Record<number, MyExperienceApplication>
  >({});
  const [cancelingId, setCancelingId] = useState<number | null>(null);
  const [cancelError, setCancelError] = useState<{
    id: number;
    message: string;
  } | null>(null);
  const [cancelNotice, setCancelNotice] = useState<{
    id: number;
    message: string;
  } | null>(null);

  const cancelLock = useRef(false);
  const handleCancel = async (applicationId: number) => {
    if (cancelLock.current) return;
    if (
      !window.confirm(
        'この予約をキャンセルしますか？キャンセルは取り消せず、生産者に通知されます。',
      )
    )
      return;
    cancelLock.current = true;
    setCancelingId(applicationId);
    setCancelError(null);
    setCancelNotice(null);
    try {
      const updated = await cancelExperienceApplication(applicationId);
      setCanceledMap((prev) => ({ ...prev, [applicationId]: updated }));
      setCancelNotice({
        id: applicationId,
        message: '予約をキャンセルしました。',
      });
    } catch (cause) {
      setCancelError({
        id: applicationId,
        message:
          cause instanceof Error
            ? cause.message
            : '予約をキャンセルできませんでした。',
      });
    } finally {
      cancelLock.current = false;
      setCancelingId(null);
    }
  };

  const applications = state.data?.map((item) => canceledMap[item.id] ?? item);

  return (
    <ContentPage
      eyebrow="MY EXPERIENCES"
      title="体験申込状況"
      intro="申し込んだ産地体験の予約内容とステータスを確認できます。"
    >
      <MyPageNavigation />
      <Link to="/experiences" className={textLinkClass}>
        体験を探す →
      </Link>
      <ContentStatus {...state} />
      {applications &&
        (applications.length ? (
          <div className="mt-6 space-y-5">
            {applications.map((application) => {
              const isCanceling = cancelingId === application.id;
              return (
                <article key={application.id} className={panelClass}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span
                      className={`rounded-full px-4 py-1.5 text-sm font-bold ${
                        STATUS_CLASSES[application.status] ??
                        'bg-marche-sage text-marche-green'
                      }`}
                    >
                      {STATUS_LABELS[application.status] ?? '状況確認中'}
                    </span>
                    <span className="text-sm font-bold text-marche-muted">
                      予約番号：{application.reservationNo}
                    </span>
                  </div>

                  <h2 className="mb-2 mt-3 font-serif text-xl">
                    {application.experience.title ?? '公開を終了した体験'}
                  </h2>

                  <dl className="my-4 grid gap-3 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="font-bold text-marche-muted">開催日時</dt>
                      <dd className="m-0 mt-1">
                        {dateLabel(application.slot.startAt)}{' '}
                        {timeLabel(application.slot.startAt)}〜（約
                        {application.slot.durationMin}分）
                      </dd>
                    </div>
                    <div>
                      <dt className="font-bold text-marche-muted">参加人数</dt>
                      <dd className="m-0 mt-1">
                        {participantText(application)}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-bold text-marche-muted">合計金額</dt>
                      <dd className="m-0 mt-1 text-base font-bold">
                        {yen(application.totalAmount)}（税込）
                      </dd>
                    </div>
                    <div>
                      <dt className="font-bold text-marche-muted">申込日</dt>
                      <dd className="m-0 mt-1">
                        {dateLabel(application.createdAt)}
                      </dd>
                    </div>
                  </dl>

                  {application.cancelDeadlineAt &&
                    application.status === 'confirmed' && (
                      <p className="m-0 mb-3 text-xs text-marche-muted">
                        キャンセル受付期限：
                        {dateLabel(application.cancelDeadlineAt)}{' '}
                        {timeLabel(application.cancelDeadlineAt)}まで
                      </p>
                    )}

                  {cancelError?.id === application.id && (
                    <p
                      role="alert"
                      className="my-2 text-sm font-bold text-marche-red"
                    >
                      {cancelError.message}
                    </p>
                  )}
                  {cancelNotice?.id === application.id && (
                    <p
                      role="status"
                      className="my-2 text-sm font-bold text-marche-green"
                    >
                      {cancelNotice.message}
                    </p>
                  )}

                  <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
                    {application.experience.isPublic ? (
                      <Link
                        to={`/experiences/${application.experience.id}`}
                        className={textLinkClass}
                      >
                        体験詳細を見る →
                      </Link>
                    ) : (
                      <p className="m-0 text-sm text-marche-muted">
                        この体験は現在公開されていません。
                      </p>
                    )}

                    {application.cancellable && (
                      <Button
                        variant="outline"
                        disabled={cancelingId !== null}
                        onClick={() => void handleCancel(application.id)}
                      >
                        {isCanceling ? 'キャンセル中…' : '予約をキャンセルする'}
                      </Button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="mt-6">
            <EmptyContent>
              <p>申し込んだ体験はまだありません。</p>
              <Link to="/experiences" className={linkClass}>
                体験を探す
              </Link>
            </EmptyContent>
          </div>
        ))}
    </ContentPage>
  );
}
