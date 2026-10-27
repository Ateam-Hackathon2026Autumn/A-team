import { hoursFromNow } from '../../helpers';
import type { RestMock } from '../../types';

// 生産者申請状況取得API GET /api/v1/producer-applications/me
//
// ログイン中の山本さん（承認済み）の最新申請を返す
//
// 状態を切り替えたい場合は status / reviewComment / reviewedAt / canResubmit を書き換える
//   審査中    : 'pending'  / null                                   / null               / false
//   差し戻し  : 'returned' / '生産品目を具体的に記載してください。' / hoursFromNow(-24) / true
//   却下      : 'rejected' / '（却下理由）'                         / hoursFromNow(-24) / false
//
// 申請が一度もない（404）:
//   { errorCode: 'APPLICATION_NOT_FOUND', errorMsg: '生産者登録申請はありません。' }
const producerApplicationMe: RestMock = {
  method: 'GET',
  path: '/api/v1/producer-applications/me',
  status: 200,
  body: {
    applicationId: 1,
    producerId: 1,
    status: 'approved',
    reviewComment: null,
    submittedAt: hoursFromNow(-24 * 400),
    reviewedAt: hoursFromNow(-24 * 397),
    canResubmit: false,
    producer: {
      businessName: '山本農園',
      representativeName: '山本 健太',
      // agriculture（農業）/ livestock（畜産）/ fishery（漁業）
      genre: 'agriculture',
      // 長野県
      prefectureId: 20,
      city: '安曇野市',
      productionItems: 'りんご・ぶどう',
      intro:
        '北アルプスの雪どけ水で育てる、蜜たっぷりのりんご。三代目として減農薬栽培に取り組んでいます。',
      acceptsExperience: true,
      recruiting: true,
      careerStartYear: 2015,
      foundedYear: null,
      // S3 のキー
      profileImage: 'producers/yamamoto-farm-profile.jpg',
      coverImage: 'producers/yamamoto-farm-cover.jpg',
      applicationReason:
        '祖父の代から続く園地を、次の世代にも残したいと思い会社を辞めて戻りました。',
    },
  },
};

export { producerApplicationMe };
