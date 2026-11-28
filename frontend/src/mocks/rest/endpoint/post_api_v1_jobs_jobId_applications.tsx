import {
  demoJobApplications,
  getAllJobApplications,
} from '../../demoJobApplications';
import { getMockJob, markMockJobApplied } from './get_api_v1_jobs_jobId';
import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 求人応募API POST /api/v1/jobs/{jobId}/applications

// ログイン中の会員（山本 健太）が求人3（海風水産・干物の加工）の勤務日7 に応募した結果を返す
// ※ 自分が所有する求人への応募は実APIで409 CANNOT_APPLY_OWNになる
// 応募は「希望日の申請」で、採用が決まるまで status は applied のまま

// エラーにしたい場合は status と body を下記に書き換える

// 未ログイン（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
// 自分の求人に応募した（status: 409）:
//   { errorCode: 'CANNOT_APPLY_OWN', errorMsg: 'ご自身の求人には応募できません。' }
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
  if (!job)
    return { status: 404, body: { errorMsg: '求人が見つかりません。' } };
  let input: Record<string, unknown>;
  try {
    input = JSON.parse(String(init?.body));
  } catch {
    return { status: 400, body: { errorMsg: '応募内容を確認してください。' } };
  }
  if (!input || typeof input !== 'object' || Array.isArray(input))
    return {
      status: 400,
      body: {
        errorCode: 'VALIDATION_ERROR',
        errorMsg: '応募内容を確認してください。',
      },
    };
  const details: Record<string, string[]> = {};
  for (const key of Object.keys(input))
    if (
      !['workDateIds', 'message', 'answers', 'requirementsConfirmed'].includes(
        key,
      )
    )
      details[key] = ['この項目は受け付けていません。'];
  if (input.requirementsConfirmed !== true)
    details.requirementsConfirmed = ['応募条件の確認が必要です。'];
  if (
    !Array.isArray(input.workDateIds) ||
    input.workDateIds.length > 100 ||
    input.workDateIds.some(
      (id) => typeof id !== 'number' || !Number.isSafeInteger(id) || id < 1,
    ) ||
    new Set(input.workDateIds).size !== input.workDateIds.length
  )
    details.workDateIds = ['勤務希望日を確認してください。'];
  if (
    input.message != null &&
    (typeof input.message !== 'string' ||
      Array.from(input.message.trim()).length > 2000)
  )
    details.message = ['メッセージは2000文字以内で入力してください。'];
  if (
    input.answers !== undefined &&
    (!Array.isArray(input.answers) || input.answers.length)
  )
    details.answers = ['回答は空の配列を指定してください。'];
  if (Object.keys(details).length)
    return {
      status: 400,
      body: {
        errorCode: 'VALIDATION_ERROR',
        errorMsg: '応募内容を確認してください。',
        details,
      },
    };
  if (
    getAllJobApplications().some((application) => application.job.id === jobId)
  )
    return {
      status: 409,
      body: {
        errorCode: 'ALREADY_APPLIED',
        errorMsg: 'この求人には応募済みです。',
      },
    };
  if (!job.isAcceptingApplications)
    return {
      status: 409,
      body: {
        errorCode: 'JOB_NOT_ACCEPTING',
        errorMsg: '募集を締め切りました。',
      },
    };
  if (
    !Array.isArray(input.workDateIds) ||
    (job.workDates.total > 0 && !input.workDateIds.length)
  )
    return {
      status: 400,
      body: {
        errorCode: 'VALIDATION_ERROR',
        errorMsg: '勤務希望日を選択してください。',
        details: { workDateIds: ['勤務希望日を1日以上選択してください。'] },
      },
    };
  const selected = job.workDates.items.filter((day) =>
    (input.workDateIds as unknown[]).includes(day.id),
  );
  if (selected.length !== input.workDateIds.length)
    return {
      status: 400,
      body: {
        errorCode: 'VALIDATION_ERROR',
        errorMsg: '勤務希望日を確認してください。',
        details: {
          workDateIds: ['この求人の勤務日ではない日が含まれています。'],
        },
      },
    };
  if (selected.some((day) => !day.isSelectable || day.remainingCount <= 0))
    return {
      status: 409,
      body: {
        errorCode: 'WORK_DATE_UNAVAILABLE',
        errorMsg: '選択した勤務日は募集を締め切りました。',
      },
    };
  const id = 100 + demoJobApplications.length;
  demoJobApplications.unshift({
    id,
    job: { id: jobId, title: job.title, isPublic: true },
    workDates: selected.map((day) => ({ id: day.id, workDate: day.workDate })),
    status: 'applied',
    createdAt: hoursFromNow(0),
  });
  markMockJobApplied(jobId);
  return {
    status: 201,
    body: {
      id,
      jobId,
      workDateIds: [...input.workDateIds].sort((a, b) => Number(a) - Number(b)),
      message:
        typeof input.message === 'string' ? input.message.trim() || null : null,
      answers: [],
      status: 'applied',
      decidedAt: null,
      createdAt: hoursFromNow(0),
    },
  };
};
