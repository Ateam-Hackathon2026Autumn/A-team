import { useAtom } from 'jotai';
import { Link, useNavigate } from 'react-router';

import { createProducerApplication } from '../api/producerApplicationApi';
import ProducerApplicationForm from '../components/producer/ProducerApplicationForm';
import { ContentPage, textLinkClass } from '../components/ui/ContentPage';
import { userInfoAtom } from '../stores/userAtom';
import type { ProducerApplicationInput } from '../types/producerApplication';

export default function ProducerApplicationNewPage() {
  const navigate = useNavigate();
  const [userInfo, setUserInfo] = useAtom(userInfoAtom);

  const handleSubmit = async (input: ProducerApplicationInput) => {
    const accepted = await createProducerApplication(input);
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
      title="生産者登録申請"
      intro="つながるマルシェで商品・体験・お仕事を掲載するための生産者登録申請です。運営にて内容を確認後、結果をお知らせいたします。"
    >
      <div className="flex flex-wrap gap-4">
        <Link to="/mypage" className={textLinkClass}>
          ← マイページへ
        </Link>
        <Link to="/producer-application" className={textLinkClass}>
          申請状況を確認する →
        </Link>
      </div>
      <ProducerApplicationForm
        mode="create"
        submitLabel="生産者登録を申請する"
        submittingLabel="申請を送信中…"
        cancelTo="/mypage"
        onSubmit={handleSubmit}
      />
    </ContentPage>
  );
}
