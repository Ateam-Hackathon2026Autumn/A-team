import { useAtom } from 'jotai';
import { Link, useNavigate } from 'react-router';

import {
  getMyProducerApplication,
  resubmitProducerApplication,
} from '../api/producerApplicationApi';
import ProducerApplicationForm from '../components/producer/ProducerApplicationForm';
import {
  ContentPage,
  ContentStatus,
  EmptyContent,
  linkClass,
  panelClass,
  textLinkClass,
} from '../components/ui/ContentPage';
import { usePublicContent } from '../hooks/usePublicContent';
import { userInfoAtom } from '../stores/userAtom';
import type {
  ProducerApplicationChanges,
  ProducerApplicationInput,
} from '../types/producerApplication';

export default function ProducerApplicationEditPage() {
  const navigate = useNavigate();
  const [userInfo, setUserInfo] = useAtom(userInfoAtom);
  const state = usePublicContent(getMyProducerApplication);
  const application = state.data;

  const handleSubmit = async (
    _fullInput: ProducerApplicationInput,
    changes: ProducerApplicationChanges,
  ) => {
    if (!application) return;
    const accepted = await resubmitProducerApplication({
      applicationId: application.applicationId,
      changes,
    });
    if (userInfo !== null) {
      setUserInfo({
        ...userInfo,
        isProducer: accepted.isProducer,
        producerApplicationStatus: accepted.approvalStatus,
      });
    }
    navigate('/producer-application', { replace: true });
  };

  return (
    <ContentPage
      eyebrow="PRODUCER APPLICATION"
      title="生産者申請修正"
      intro="差し戻し理由をご確認のうえ、申請内容を修正して再申請してください。"
    >
      <Link to="/producer-application" className={textLinkClass}>
        ← 申請状況へ戻る
      </Link>

      {state.errorStatus === 404 ? (
        <div className="mt-6">
          <EmptyContent>
            <h2 className="mt-0 font-serif text-xl">生産者登録申請はまだありません</h2>
            <p className="text-sm text-marche-muted">
              先に新規の生産者登録申請を行ってください。
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
        application.canResubmit ? (
          <ProducerApplicationForm
            key={application.applicationId}
            mode="edit"
            initialProducer={application.producer}
            reviewComment={application.reviewComment}
            submitLabel="修正内容を保存して再申請する"
            submittingLabel="再申請を送信中…"
            cancelTo="/producer-application"
            onSubmit={handleSubmit}
          />
        ) : (
          <section className={`${panelClass} mt-6`}>
            <h2 className="mt-0 font-serif text-xl">現在は申請の修正・再申請はできません</h2>
            <p className="text-sm text-marche-muted">
              現在の申請は再申請できません。掲載停止中などの理由や審査状況は申請状況画面でご確認ください。
            </p>
            <Link to="/producer-application" className={linkClass}>
              申請状況を確認する
            </Link>
          </section>
        )
      )}
    </ContentPage>
  );
}
