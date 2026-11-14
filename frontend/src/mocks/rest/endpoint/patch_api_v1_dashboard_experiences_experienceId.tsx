import type { RestMock } from '../../types';
import { updateExperience } from '../store/dashboardExperiences';

// 体験更新API PATCH /api/v1/dashboard/experiences/:experienceId
//
// 送信した項目だけを更新し、更新後の ID と公開状態を返す（If-Match に詳細取得の ETag が必要。新しい ETag はヘッダー）
//
// 予約がある体験の内容（タイトル・説明・開催地・料金）を変えようとした場合（status: 409）:
//   {
//     errorCode: 'ACTIVE_RESERVATIONS_EXIST',
//     errorMsg: '予約があるため、この項目は変更できません。',
//   }
//
// 他の画面で先に更新されていた場合（status: 412）:
//   {
//     errorCode: 'PRECONDITION_FAILED',
//     errorMsg: '他の操作で更新されています。再読み込みしてください。',
//   }
const dashboardExperienceUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/experiences/:experienceId',
  status: 200,
  handler: (url, init) => updateExperience(url, init),
};

export { dashboardExperienceUpdate };
