import { demoJobApplications, getAllJobApplications } from '../../demoJobApplications';
import { getMockJob } from './get_api_v1_jobs_jobId';
import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 求人応募API POST /api/v1/jobs/{jobId}/applications
//
// ログイン中の会員（山本 健太）が求人3（海風水産・干物の加工）の勤務日7 に応募した結果を返す
// ※ 自分が所有する求人（求人1・2）への応募は本来 403 になる
// 応募は「希望日の申請」で、採用が決まるまで status は applied のまま
//
// エラーにしたい場合は status と body を下記に書き換える
//
// 未ログイン（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
// 自分の求人に応募した（status: 403）:
//   { errorCode: 'FORBIDDEN', errorMsg: 'ご自身の求人には応募できません。' }
// 応募済み（status: 409）:
//   { errorCode: 'ALREADY_APPLIED', errorMsg: 'この求人には応募済みです。' }
// 募集終了・枠が埋まった（status: 409）:
//   { errorCode: 'CONFLICT', errorMsg: '選択した勤務日は募集を締め切りました。' }
const jobApply: RestMock = {
  method: 'POST',
  path: '/api/v1/jobs/:jobId/applications',
  status: 201,
  body: {
    id: 4,
    jobId: 3,
    workDateIds: [7],
    message: '早朝の作業も大丈夫です。干物づくりを体験してみたいです。',
    answers: [],
    status: 'applied',
    decidedAt: null,
    createdAt: hoursFromNow(0),
  },
};

export { jobApply };

// タブを再読み込みするとリセットされる、デモ応募履歴。

jobApply.handler = (url, init) => {
  const jobId = Number(url.pathname.split('/').at(-2));
  const job = getMockJob(jobId);
  if (!job) return { status: 404, body: { errorMsg: '求人が見つかりません。' } };
  let input: Record<string, unknown>;
  try { input = JSON.parse(String(init?.body)); } catch { return { status: 400, body: { errorMsg: '応募内容を確認してください。' } }; }
  if (!job.isAcceptingApplications) return { status: 409, body: { errorMsg: '募集を締め切りました。' } };
  if (!Array.isArray(input.workDateIds) || !input.workDateIds.length) return { status: 400, body: { errorMsg: '勤務希望日を選択してください。' } };
  const selected = job.workDates.items.filter(day => (input.workDateIds as unknown[]).includes(day.id));
  if (selected.length !== input.workDateIds.length || selected.some(day => !day.isSelectable || day.remainingCount <= 0)) return { status: 409, body: { errorMsg: '選択した勤務日は募集を締め切りました。' } };
  if (getAllJobApplications().some(application => application.job.id === jobId)) return { status: 409, body: { errorCode: 'ALREADY_APPLIED', errorMsg: 'この求人には応募済みです。' } };
  const id = 100 + demoJobApplications.length;
  demoJobApplications.unshift({ id, job: { id: jobId, title: job.title, isPublic: true }, workDates: selected.map(day => ({ id: day.id, workDate: day.workDate })), status: 'applied', createdAt: hoursFromNow(0) });
  return { status: 201, body: { ...input, id, jobId, status: 'applied', createdAt: hoursFromNow(0) } };
};
