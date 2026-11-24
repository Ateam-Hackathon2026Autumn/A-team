import { Link } from 'react-router';

import { getMyProducerApplication } from '../api/producerApplicationApi';
import { PRODUCER_GENRE_LABELS } from '../components/producer/ProducerApplicationForm';
import {
  ContentImage,
  ContentPage,
  ContentStatus,
  EmptyContent,
  dateLabel,
  linkClass,
  panelClass,
  textLinkClass,
} from '../components/ui/ContentPage';
import { usePublicContent } from '../hooks/usePublicContent';
import type { ProducerApplicationStatusValue } from '../types/producerApplication';
import { prefectureName } from '../utils/prefectures';

const STATUS_LABELS: Record<ProducerApplicationStatusValue, string> = {
  pending: '審査中',
  approved: '承認済み',
  returned: '差し戻し（修正が必要です）',
  rejected: '却下',
};

const STATUS_BADGE_CLASSES: Record<ProducerApplicationStatusValue, string> = {
  pending: 'bg-marche-orange/20 text-marche-ink',
  approved: 'bg-marche-sage text-marche-green',
  returned: 'bg-marche-red/15 text-marche-red',
  rejected: 'bg-marche-red/15 text-marche-red',
};

const STATUS_DESCRIPTIONS: Record<ProducerApplicationStatusValue, string> = {
  pending:
    '運営スタッフが申請内容を確認しています。審査が完了するまで、しばらくお待ちください。',
  approved:
    '生産者登録が承認されました。生産者管理画面から商品・体験・求人・ストーリーを掲載できます。',
  returned:
    '申請内容に確認・修正いただきたい項目があります。運営からのコメントをご確認のうえ、申請内容を修正して再申請してください。',
  rejected:
    '審査の結果、今回は登録を見送らせていただきました。内容を修正して再申請することができます。',
};

export default function ProducerApplicationStatusPage() {
  const state = usePublicContent(getMyProducerApplication);
  const application = state.data;

  return (
    <ContentPage
      eyebrow="PRODUCER APPLICATION"
      title="生産者申請状況"
      intro="生産者登録申請の審査状況と申請内容を確認できます。"
    >
      <Link to="/mypage" className={textLinkClass}>
        ← マイページへ
      </Link>

      {state.errorStatus === 404 ? (
        <div className="mt-6">
          <EmptyContent>
            <h2 className="mt-0 font-serif text-xl">生産者登録申請はまだありません</h2>
            <p className="text-sm text-marche-muted">
              つながるマルシェで商品や体験、求人を掲載するには、生産者登録申請を行ってください。
            </p>
            <Link to="/producer-application/new" className={linkClass}>
              生産者登録を申請する
            </Link>
          </EmptyContent>
        </div>
      ) : (
        <ContentStatus {...state} />
      )}

      {application && (
        <div className="mt-6 space-y-6">
          <section className={panelClass}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span
                className={`rounded-full px-4 py-1.5 text-sm font-bold ${
                  STATUS_BADGE_CLASSES[application.status] ?? 'bg-marche-sage text-marche-green'
                }`}
              >
                {STATUS_LABELS[application.status] ?? application.status}
              </span>
              <span className="text-sm text-marche-muted">
                申請日：{dateLabel(application.submittedAt)}
                {application.reviewedAt && ` / 審査日：${dateLabel(application.reviewedAt)}`}
              </span>
            </div>

            <p className="mt-4 text-sm leading-relaxed">
              {STATUS_DESCRIPTIONS[application.status]}
            </p>

            {application.reviewComment && (
              <div
                role="region"
                aria-label="審査コメント"
                className="mt-4 rounded-xl border border-solid border-marche-line bg-marche-canvas p-4 text-sm"
              >
                <p className="m-0 font-bold">運営からのコメント</p>
                <p className="m-0 mt-2 whitespace-pre-line">{application.reviewComment}</p>
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-4">
              {(application.status === 'returned' || application.canResubmit) && (
                <Link to="/producer-application/edit" className={linkClass}>
                  申請内容を修正して再申請する
                </Link>
              )}
              {application.status === 'approved' && (
                <Link to="/dashboard" className={linkClass}>
                  生産者管理画面へ →
                </Link>
              )}
              {application.status === 'pending' && (
                <Link to="/dashboard" className={textLinkClass}>
                  生産者管理画面を見る →
                </Link>
              )}
            </div>
          </section>

          <section className={panelClass}>
            <h2 className="mt-0 font-serif text-xl">申請内容</h2>
            {(application.producer.coverImageUrl || application.producer.profileImageUrl) && (
              <div className="mb-6 flex flex-wrap items-center gap-6">
                {application.producer.coverImageUrl && (
                  <div>
                    <p className="m-0 mb-2 text-xs font-bold text-marche-muted">カバー画像</p>
                    <ContentImage
                      src={application.producer.coverImageUrl}
                      alt={`${application.producer.businessName}のカバー画像`}
                      className="aspect-[2/1] w-64 rounded-xl"
                    />
                  </div>
                )}
                {application.producer.profileImageUrl && (
                  <div>
                    <p className="m-0 mb-2 text-xs font-bold text-marche-muted">プロフィール画像</p>
                    <ContentImage
                      src={application.producer.profileImageUrl}
                      alt={`${application.producer.representativeName}のプロフィール画像`}
                      className="size-24 rounded-full"
                    />
                  </div>
                )}
              </div>
            )}

            <dl className="m-0 grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl bg-marche-canvas p-4">
                <dt className="text-xs font-bold text-marche-muted">事業者名</dt>
                <dd className="m-0 mt-1 font-bold">{application.producer.businessName}</dd>
              </div>
              <div className="rounded-xl bg-marche-canvas p-4">
                <dt className="text-xs font-bold text-marche-muted">代表者名</dt>
                <dd className="m-0 mt-1 font-bold">{application.producer.representativeName}</dd>
              </div>
              <div className="rounded-xl bg-marche-canvas p-4">
                <dt className="text-xs font-bold text-marche-muted">業種</dt>
                <dd className="m-0 mt-1">
                  {PRODUCER_GENRE_LABELS[application.producer.genre] ?? application.producer.genre}
                </dd>
              </div>
              <div className="rounded-xl bg-marche-canvas p-4">
                <dt className="text-xs font-bold text-marche-muted">所在地</dt>
                <dd className="m-0 mt-1">
                  {prefectureName(application.producer.prefectureId)} {application.producer.city}
                </dd>
              </div>
              <div className="rounded-xl bg-marche-canvas p-4 sm:col-span-2">
                <dt className="text-xs font-bold text-marche-muted">生産品目</dt>
                <dd className="m-0 mt-1">{application.producer.productionItems}</dd>
              </div>
              <div className="rounded-xl bg-marche-canvas p-4 sm:col-span-2">
                <dt className="text-xs font-bold text-marche-muted">ひとこと紹介</dt>
                <dd className="m-0 mt-1 whitespace-pre-line">{application.producer.intro}</dd>
              </div>
              <div className="rounded-xl bg-marche-canvas p-4">
                <dt className="text-xs font-bold text-marche-muted">この仕事を始めた年 / 創業年</dt>
                <dd className="m-0 mt-1">
                  {[
                    application.producer.careerStartYear !== null
                      ? `就業 ${application.producer.careerStartYear}年`
                      : null,
                    application.producer.foundedYear !== null
                      ? `創業 ${application.producer.foundedYear}年`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(' · ') || '未設定'}
                </dd>
              </div>
              <div className="rounded-xl bg-marche-canvas p-4">
                <dt className="text-xs font-bold text-marche-muted">受け入れ・募集</dt>
                <dd className="m-0 mt-1">
                  {[
                    application.producer.acceptsExperience ? '体験受け入れ中' : null,
                    application.producer.recruiting ? '担い手募集中' : null,
                  ]
                    .filter(Boolean)
                    .join(' · ') || 'なし'}
                </dd>
              </div>
              {application.producer.applicationReason && (
                <div className="rounded-xl bg-marche-canvas p-4 sm:col-span-2">
                  <dt className="text-xs font-bold text-marche-muted">申請理由・自己紹介</dt>
                  <dd className="m-0 mt-1 whitespace-pre-line">
                    {application.producer.applicationReason}
                  </dd>
                </div>
              )}
            </dl>
          </section>
        </div>
      )}
    </ContentPage>
  );
}
