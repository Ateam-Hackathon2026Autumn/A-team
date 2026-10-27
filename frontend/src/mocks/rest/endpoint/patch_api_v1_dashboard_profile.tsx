import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 生産者プロフィール更新API PATCH /api/v1/dashboard/profile
//
// 指定した項目だけを変更し、更新後のプロフィール全体を返す
//
// ストーリー未登録なのに reason / goal を指定した（409）:
//   { errorCode: 'STORY_REQUIRED', errorMsg: '先にストーリーを登録してください。' }
//
// 他の画面で先に更新されていた（412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '他の操作で更新されています。画面を再読み込みしてください。' }
const dashboardProfileUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/profile',
  status: 200,
  body: {
    id: 1,
    businessName: '山本農園',
    representativeName: '山本 健太',
    genre: 'agriculture',
    prefectureId: 20,
    city: '安曇野市',
    productionItems: 'りんご・ぶどう',
    intro:
      '北アルプスの雪どけ水で育てる、蜜たっぷりのりんご。三代目として減農薬栽培に取り組んでいます。',
    careerStartYear: 2015,
    foundedYear: 1962,
    acceptsExperience: true,
    recruiting: true,
    profileImageKey: 'producers/1/profile.jpg',
    coverImageKey: 'producers/1/cover.jpg',
    images: [
      {
        id: 1,
        imageKey: 'producers/1/gallery-1.jpg',
        url: 'https://picsum.photos/seed/yamamoto1/800/600',
        sortOrder: 0,
      },
      {
        id: 2,
        imageKey: 'producers/1/gallery-2.jpg',
        url: 'https://picsum.photos/seed/yamamoto2/800/600',
        sortOrder: 1,
      },
      {
        id: 3,
        imageKey: 'producers/1/gallery-3.jpg',
        url: 'https://picsum.photos/seed/yamamoto3/800/600',
        sortOrder: 2,
      },
    ],
    reason: '祖父の代から続く園地を、次の世代にも残したいと思い会社を辞めて戻りました。',
    goal: '収穫体験と短期スタッフ受け入れで、りんご産地の担い手を増やしたい。',
    profileImageUrl: 'https://picsum.photos/seed/yamamoto-profile/800/600',
    coverImageUrl: 'https://picsum.photos/seed/yamamoto-cover/800/600',
    approvalStatus: 'approved',
    publishStatus: 'public',
    storyExists: true,
    storyPublishStatus: 'public',
    updatedAt: hoursFromNow(0),
  },
};

export { dashboardProfileUpdate };
