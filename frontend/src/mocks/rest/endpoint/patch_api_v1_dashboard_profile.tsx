import type { RestMock } from '../../types';
import { patchProfile } from '../store/dashboardProfile';

// 生産者プロフィール更新API PATCH /api/v1/dashboard/profile
//
// 実API: backend/api/views/dashboard/profile.py・serializers/dashboard/profile.py
// 送った項目だけ変え、更新後のプロフィール全体を GET と同じ形で返す（ETag・If-Match は使わない）
//   変えられる項目: prefectureId, city, productionItems, intro, careerStartYear, foundedYear,
//                   acceptsExperience, recruiting, profileImage, coverImage, imageKeys, publishStatus
//   事業者名・代表者名・ジャンルは変えられない（未知の項目として 400）。reason・goal はストーリーAPIで変える
// 処理は store/dashboardProfile.tsx
//
// 入力エラー（400）:
//   { errorCode: 'VALIDATION_ERROR', errorMsg: '入力内容に誤りがあります。',
//     details: { city: ['この項目が50文字より長くならないようにしてください。'] } }
//   空のオブジェクト: details: { nonFieldErrors: ['変更する項目を指定してください。'] }
//   自分がアップロードしていない画像: details: { imageKeys: ['アップロードした画像を指定してください。'] }
// 掲載停止中に publishStatus を送った（409）:
//   { errorCode: 'PRODUCER_SUSPENDED', errorMsg: '掲載停止中のため、この操作はできません。運営にお問い合わせください。' }
const dashboardProfileUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/profile',
  status: 200,
  handler: (_url, init) => patchProfile(init),
};

export { dashboardProfileUpdate };
