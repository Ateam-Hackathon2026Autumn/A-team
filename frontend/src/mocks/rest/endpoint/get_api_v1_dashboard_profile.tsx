import type { RestMock } from '../../types';
import { getProfile } from '../store/dashboardProfile';

// 生産者プロフィール取得API GET /api/v1/dashboard/profile
//
// 実API: backend/api/views/dashboard/profile.py・serializers/dashboard/profile.py
//   {id, businessName, representativeName, genre, prefectureId, city, productionItems, intro,
//    careerStartYear, foundedYear, acceptsExperience, recruiting,
//    profileImage, coverImage, profileImageUrl, coverImageUrl, images: [{id, key, url, sortOrder}],
//    approvalStatus, publishStatus, reason, goal, storyPublishStatus, updatedAt}
//   reason・goal・storyPublishStatus はストーリーの値（ストーリーがなければ null）。掲載停止中でも取得できる
//
// 内容は store/dashboardProfile.tsx が持つ（更新APIの結果がここに反映される）
// 未ログイン（401）: { errorCode: 'NOT_AUTHENTICATED', errorMsg: 'ログインしてください。' }
// 承認済みの生産者でない（403）: { errorCode: 'FORBIDDEN', errorMsg: 'この操作を行う権限がありません。' }
const dashboardProfile: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/profile',
  status: 200,
  handler: () => getProfile(),
};

export { dashboardProfile };
