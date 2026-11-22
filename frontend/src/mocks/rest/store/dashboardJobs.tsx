import type {
  DashboardJob,
  DashboardJobApplication,
  DashboardJobSummary,
} from '../../../types/dashboardJob';
import type { MockResult } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';
import { todayInJapan } from '../../../utils/jobFormat';
import {
  conflict,
  idFromPath,
  imageUrlFor,
  isObject,
  loadState,
  nextId,
  notFound,
  nowIso,
  paginate,
  readJsonBody,
  saveState,
  validationError,
} from './common';

// ダッシュボード求人のモックストア
//
// 求人（一覧・詳細・登録・更新・削除）、応募者（一覧・状態変更）の各モックが、このデータを読み書きする
// レスポンスの形・入力チェックは実API（backend/api/views/dashboard/jobs.py、serializers/dashboard/jobs.py）に合わせる
// - 一覧・詳細に応募件数・採用人数を含む。
// - 応募があっても求人の項目は変更できる。ただし応募者が希望している勤務日の削除・日付変更は 409
// - 応募されたことがある求人は削除できない（409）
// - 応募の状態を変えたときのレスポンスは { id, status, decidedAt, hiredCount, slots, isOverCapacity }
// - ETag・Idempotency-Key は使わない
//
// 初期データ（ログイン中の生産者 = 山本農園）
//   求人1: りんごの収穫・選果スタッフ（公開中。応募3件: 新着2・辞退1）
//   求人2: 冬の剪定作業補助（公開中。応募1件: 選考中）
//   求人5: りんごジュースの加工・出荷（下書き。応募なし）

const STORAGE_KEY = 'tsunagaru-marche.mock-dashboard-jobs.v2';
// 都道府県を省略したときに使う、生産者の都道府県（長野県）
const PRODUCER_PREFECTURE_ID = 20;
const MAX_INT = 2147483647;
const JOB_NOT_FOUND = '求人が見つかりません。';
const APPLICATION_NOT_FOUND = '応募者が見つかりません。';
// 退会した会員の氏名（実APIの anonymize と同じ）
const DELETED_NAME = '退会ユーザー';

type StoredJob = Omit<DashboardJob, 'applicationCount' | 'hiredCount' | 'coverImageUrl'>;
type StoredApplication = DashboardJobApplication & { jobId: number };

type State = {
  jobs: StoredJob[];
  applications: StoredApplication[];
};

function seedState(): State {
  const jobs: StoredJob[] = [
    {
      id: 1,
      title: 'りんごの収穫・選果スタッフ',
      prefectureId: 20,
      termType: 'short',
      payUnit: 'hourly',
      payAmount: 1200,
      periodStart: daysFromNow(-14),
      periodEnd: daysFromNow(40),
      workHours: '8:00〜15:00',
      workPlace: '長野県安曇野市 山本農園 りんご園・選果場',
      slots: 5,
      description:
        '収穫最盛期のりんご園で、ふじの収穫と選果（大きさ・色づきの仕分け）をお手伝いいただきます。\n' +
        '未経験の方にも、はさみの使い方から丁寧にお教えします。住み込み可（個室・食事付き）です。',
      requirements: ['18歳以上の方', '3日以上勤務できる方', '屋外での立ち仕事に抵抗のない方'],
      belongings: ['汚れてもよい服装', '長靴', '帽子', '飲み物'],
      notes: [
        '雨天時は選果場での作業になります。',
        '住み込みを希望される方は応募メッセージでお知らせください。',
      ],
      inexperiencedOk: true,
      coverImage: 'jobs/job-1-cover.jpg',
      publishStatus: 'public',
      workDates: [
        { id: 1, workDate: daysFromNow(5), neededCount: 5 },
        { id: 2, workDate: daysFromNow(6), neededCount: 5 },
        { id: 3, workDate: daysFromNow(12), neededCount: 5 },
        { id: 4, workDate: daysFromNow(13), neededCount: 5 },
        { id: 5, workDate: daysFromNow(26), neededCount: 3 },
        { id: 6, workDate: daysFromNow(34), neededCount: 3 },
      ],
      createdAt: hoursFromNow(-24 * 14),
      updatedAt: hoursFromNow(-24 * 1),
    },
    {
      id: 2,
      title: '冬の剪定作業補助',
      prefectureId: 20,
      termType: 'short',
      payUnit: 'daily',
      payAmount: 9000,
      periodStart: null,
      periodEnd: daysFromNow(60),
      workHours: '9:00〜16:00（休憩1時間）',
      workPlace: '長野県安曇野市 山本農園 りんご園',
      slots: 2,
      description:
        '来年の実りに向けた、りんごの木の剪定作業を補助していただきます。\n' +
        '枝の片付けや運搬が中心です。剪定のコツも教えます。',
      requirements: ['2日以上勤務できる方'],
      belongings: ['防寒着', '軍手', '長靴'],
      notes: null,
      inexperiencedOk: true,
      coverImage: null,
      publishStatus: 'public',
      workDates: [
        { id: 7, workDate: daysFromNow(40), neededCount: 2 },
        { id: 8, workDate: daysFromNow(41), neededCount: 2 },
      ],
      createdAt: hoursFromNow(-24 * 5),
      updatedAt: hoursFromNow(-24 * 2),
    },
    {
      id: 5,
      title: 'りんごジュースの加工・出荷',
      prefectureId: 20,
      termType: 'one_day',
      payUnit: 'hourly',
      payAmount: 1100,
      periodStart: null,
      periodEnd: null,
      workHours: '9:00〜12:00',
      workPlace: '長野県安曇野市 山本農園 加工場',
      slots: 2,
      description: '搾ったりんごジュースの瓶詰め・ラベル貼り・箱詰めをお願いします。',
      requirements: null,
      belongings: null,
      notes: null,
      inexperiencedOk: true,
      coverImage: null,
      publishStatus: 'draft',
      workDates: [],
      createdAt: hoursFromNow(-3),
      updatedAt: hoursFromNow(-3),
    },
  ];

  const applications: StoredApplication[] = [
    {
      id: 2,
      jobId: 1,
      userId: 6,
      lastName: '松本',
      firstName: '隼',
      phone: '090-2345-6789',
      age: 24,
      message: '長野県内に住んでいます。収穫期は週末を中心に勤務できます。',
      answers: null,
      workDates: [
        { id: 2, workDate: daysFromNow(6) },
        { id: 4, workDate: daysFromNow(13) },
      ],
      status: 'applied',
      decidedAt: null,
      createdAt: hoursFromNow(-24 * 1),
      updatedAt: hoursFromNow(-24 * 1),
    },
    {
      id: 1,
      jobId: 1,
      userId: 5,
      lastName: '高橋',
      firstName: 'ゆい',
      phone: '080-3456-7890',
      age: 31,
      message:
        '週末に家庭菜園をしています。りんご農家の仕事を間近で学びたいです。体力には自信があります。',
      answers: null,
      workDates: [
        { id: 1, workDate: daysFromNow(5) },
        { id: 2, workDate: daysFromNow(6) },
        { id: 3, workDate: daysFromNow(12) },
      ],
      status: 'applied',
      decidedAt: null,
      createdAt: hoursFromNow(-24 * 3),
      updatedAt: hoursFromNow(-24 * 3),
    },
    {
      // 退会した会員の応募（氏名は「退会ユーザー」、電話・年齢は空になる）
      id: 3,
      jobId: 1,
      userId: 9,
      lastName: DELETED_NAME,
      firstName: '',
      phone: null,
      age: null,
      message: null,
      answers: null,
      workDates: [{ id: 5, workDate: daysFromNow(26) }],
      status: 'withdrawn',
      decidedAt: null,
      createdAt: hoursFromNow(-24 * 6),
      updatedAt: hoursFromNow(-24 * 4),
    },
    {
      id: 4,
      jobId: 2,
      userId: 7,
      lastName: '中村',
      firstName: '陽向',
      phone: '070-4567-8901',
      age: 27,
      message: '冬の間だけ地元で働きたいと考えています。2日とも勤務できます。',
      answers: null,
      workDates: [
        { id: 7, workDate: daysFromNow(40) },
        { id: 8, workDate: daysFromNow(41) },
      ],
      status: 'screening',
      decidedAt: null,
      createdAt: hoursFromNow(-24 * 2),
      updatedAt: hoursFromNow(-24 * 1),
    },
  ];

  return { jobs, applications };
}

function isState(value: unknown): value is State {
  return (
    isObject(value) &&
    Array.isArray(value.jobs) &&
    value.jobs.every(
      (job) => isObject(job) && typeof job.id === 'number' && Array.isArray(job.workDates),
    ) &&
    Array.isArray(value.applications) &&
    value.applications.every(
      (item) =>
        isObject(item) &&
        typeof item.id === 'number' &&
        typeof item.jobId === 'number' &&
        typeof item.lastName === 'string' &&
        Array.isArray(item.workDates),
    )
  );
}

let state: State | null = null;

// 最初に使われたときに、保存内容（なければ初期データ）を読み込む
function getState(): State {
  state ??= loadState(STORAGE_KEY, isState) ?? seedState();

  return state;
}

function save(): void {
  saveState(STORAGE_KEY, getState());
}

// ---------------------------------------------------------------------------
// 参照・変換
// ---------------------------------------------------------------------------

function findJob(id: number): StoredJob | undefined {
  return getState().jobs.find((job) => job.id === id);
}

function applicationsOf(jobId: number): StoredApplication[] {
  return getState().applications.filter((application) => application.jobId === jobId);
}

// 応募者が希望している勤務日か
function hasApplicants(jobId: number, workDateId: number): boolean {
  return applicationsOf(jobId).some((application) =>
    application.workDates.some((day) => day.id === workDateId),
  );
}

function toDetail(job: StoredJob): DashboardJob {
  return {
    ...job,
    coverImageUrl: job.coverImage === null ? null : imageUrlFor(job.coverImage),
    applicationCount: applicationsOf(job.id).filter((item) => item.status !== 'withdrawn').length,
    hiredCount: applicationsOf(job.id).filter((item) => item.status === 'hired' || item.status === 'completed').length,
    workDates: [...job.workDates].sort(
      (a, b) => a.workDate.localeCompare(b.workDate) || a.id - b.id,
    ),
  };
}

function toSummary(job: StoredJob): DashboardJobSummary {
  return {
    id: job.id,
    title: job.title,
    termType: job.termType,
    payUnit: job.payUnit,
    payAmount: job.payAmount,
    periodStart: job.periodStart,
    periodEnd: job.periodEnd,
    workHours: job.workHours,
    workPlace: job.workPlace,
    slots: job.slots,
    inexperiencedOk: job.inexperiencedOk,
    coverImage: job.coverImage,
    coverImageUrl: job.coverImage === null ? null : imageUrlFor(job.coverImage),
    applicationCount: applicationsOf(job.id).filter((item) => item.status !== 'withdrawn').length,
    hiredCount: applicationsOf(job.id).filter((item) => item.status === 'hired' || item.status === 'completed').length,
    publishStatus: job.publishStatus,
    createdAt: job.createdAt,
    updatedAt: job.updatedAt,
  };
}

function toApplication(application: StoredApplication): DashboardJobApplication {
  const { jobId: _jobId, ...rest } = application;

  return {
    ...rest,
    workDates: [...application.workDates].sort(
      (a, b) => a.workDate.localeCompare(b.workDate) || a.id - b.id,
    ),
  };
}

// ---------------------------------------------------------------------------
// 入力チェック（実API の JobCreateSerializer / JobUpdateSerializer と同じ条件）
// ---------------------------------------------------------------------------

type WorkDateField = { id?: number; workDate: string; neededCount: number };

type JobFields = Partial<
  Omit<StoredJob, 'id' | 'workDates' | 'createdAt' | 'updatedAt'>
> & { workDates?: WorkDateField[] };

const UNKNOWN_FIELD = 'この項目は受け付けていません。';

const isText = (value: unknown, max: number) =>
  typeof value === 'string' && value.trim() !== '' && value.length <= max;
const isCount = (value: unknown) =>
  Number.isInteger(value) && Number(value) >= 1 && Number(value) <= MAX_INT;
const isDate = (value: unknown) =>
  typeof value === 'string' &&
  /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  !Number.isNaN(Date.parse(`${value}T00:00:00Z`)) &&
  new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
// requirements などは JSON（実APIは形を確かめない）。画面からは文字列の配列か null を送る
const isJson = () => true;

// 項目ごとのチェックとエラーメッセージ
const jobChecks: Record<keyof JobFields, { check: (value: unknown) => boolean; message: string }> = {
  prefectureId: {
    check: (value) => Number.isInteger(value) && Number(value) >= 1 && Number(value) <= 47,
    message: '指定された都道府県が存在しません。',
  },
  title: { check: (value) => isText(value, 100), message: '求人タイトルは100文字以内で入力してください。' },
  termType: {
    check: (value) => value === 'one_day' || value === 'short' || value === 'long',
    message: '雇用期間の種類が正しくありません。',
  },
  payUnit: {
    check: (value) => value === 'hourly' || value === 'daily' || value === 'monthly',
    message: '給与単位が正しくありません。',
  },
  payAmount: { check: isCount, message: '給与金額は1以上にしてください。' },
  periodStart: {
    check: (value) => value === null || isDate(value),
    message: '募集開始日の形式が正しくありません。',
  },
  periodEnd: {
    check: (value) => value === null || isDate(value),
    message: '募集終了日の形式が正しくありません。',
  },
  workHours: { check: (value) => isText(value, 50), message: '勤務時間は50文字以内で入力してください。' },
  workPlace: { check: (value) => isText(value, 200), message: '勤務地は200文字以内で入力してください。' },
  slots: { check: isCount, message: '募集人数は1人以上にしてください。' },
  description: {
    check: (value) => typeof value === 'string' && value.trim() !== '',
    message: '求人詳細を入力してください。',
  },
  requirements: { check: isJson, message: '' },
  belongings: { check: isJson, message: '' },
  notes: { check: isJson, message: '' },
  inexperiencedOk: {
    check: (value) => typeof value === 'boolean',
    message: '未経験者の応募可否は真偽値で指定してください。',
  },
  coverImage: {
    check: (value) => value === null || (typeof value === 'string' && value.length <= 500),
    message: '画像のキーは500文字以内で指定してください。',
  },
  publishStatus: {
    check: (value) => value === 'draft' || value === 'public' || value === 'private',
    message: '掲載状態が正しくありません。',
  },
  workDates: {
    check: (value) =>
      Array.isArray(value) &&
      value.every(
        (day) =>
          isObject(day) &&
          Object.keys(day).every((key) => ['id', 'workDate', 'neededCount'].includes(key)) &&
          (day.id === undefined || isCount(day.id)) &&
          isDate(day.workDate) &&
          isCount(day.neededCount),
      ),
    message: '勤務日の形式が正しくありません。',
  },
};

const ALL_FIELDS = Object.keys(jobChecks);
// 登録時に必須の項目
const REQUIRED_ON_CREATE = [
  'title',
  'termType',
  'payUnit',
  'payAmount',
  'workHours',
  'workPlace',
  'slots',
  'description',
  'inexperiencedOk',
];

type ParseResult =
  | { ok: true; fields: JobFields }
  | { ok: false; errors: Record<string, string[]> };

// 送られた項目だけチェックする（required の項目は、送られていなければエラー）。定義にない項目は 400
function parseFields(input: unknown, required: string[]): ParseResult {
  if (!isObject(input)) {
    return { ok: false, errors: { nonFieldErrors: ['リクエストの形式が正しくありません。'] } };
  }

  const errors: Record<string, string[]> = {};
  const fields: Record<string, unknown> = {};

  for (const name of Object.keys(input)) {
    if (!ALL_FIELDS.includes(name)) {
      errors[name] = [UNKNOWN_FIELD];
    }
  }

  for (const [name, { check, message }] of Object.entries(jobChecks)) {
    if (!(name in input)) {
      if (required.includes(name)) {
        errors[name] = ['この項目は必須です。'];
      }
    } else if (check(input[name])) {
      fields[name] = input[name];
    } else {
      errors[name] = [message];
    }
  }

  return Object.keys(errors).length > 0
    ? { ok: false, errors }
    : { ok: true, fields: fields as JobFields };
}

// 項目どうしの条件（JobCreateSerializer.validate と同じ順番）。問題があれば 400 の details を返す
function checkConsistency(job: {
  termType: string;
  publishStatus: string;
  periodStart: string | null;
  periodEnd: string | null;
  workDates: WorkDateField[];
}): Record<string, string[]> | null {
  if (job.periodStart !== null && job.periodEnd !== null && job.periodStart > job.periodEnd) {
    return { periodEnd: ['募集終了日は募集開始日以降にしてください。'] };
  }

  if (job.termType === 'long' && job.workDates.length > 0) {
    return { workDates: ['長期求人には勤務日を登録できません。'] };
  }

  const dates = job.workDates.map((day) => day.workDate);

  if (new Set(dates).size !== dates.length) {
    return { workDates: ['同じ勤務日を重複して登録することはできません。'] };
  }

  if (
    job.termType !== 'long' &&
    job.publishStatus === 'public' &&
    !dates.some((date) => date >= todayInJapan())
  ) {
    return { workDates: ['公開する単発・短期求人には今日以降の勤務日を1日以上登録してください。'] };
  }

  for (const [index, date] of dates.entries()) {
    if (job.periodStart !== null && date < job.periodStart) {
      return { [`workDates.${index}.workDate`]: ['勤務日は募集開始日以降にしてください。'] };
    }

    if (job.periodEnd !== null && date > job.periodEnd) {
      return { [`workDates.${index}.workDate`]: ['勤務日は募集終了日以前にしてください。'] };
    }
  }

  return null;
}

function newWorkDateId(): number {
  return (
    Math.max(0, ...getState().jobs.flatMap((job) => job.workDates.map((day) => day.id))) + 1
  );
}

// ---------------------------------------------------------------------------
// 求人
// ---------------------------------------------------------------------------

const PUBLISH_STATUSES = ['draft', 'public', 'private', 'suspended'];

// GET /api/v1/dashboard/jobs?publishStatus=&keyword=&page=&pageSize=（作成の新しい順）
function listJobs(url: URL): MockResult {
  const publishStatus = url.searchParams.get('publishStatus');
  const keyword = url.searchParams.get('keyword') ?? '';

  if (publishStatus !== null && !PUBLISH_STATUSES.includes(publishStatus)) {
    return validationError({ publishStatus: ['指定された掲載状態は正しくありません。'] });
  }

  const items = getState()
    .jobs.filter((job) => publishStatus === null || job.publishStatus === publishStatus)
    .filter(
      (job) => keyword === '' || job.title.includes(keyword) || job.description.includes(keyword),
    )
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt) || b.id - a.id)
    .map(toSummary);
  const page = paginate(items, url);

  return page === null
    ? validationError({ page: ['ページ番号は1以上にしてください。'] })
    : { status: 200, body: page };
}

// GET /api/v1/dashboard/jobs/:jobId
function getJob(url: URL): MockResult {
  const job = findJob(idFromPath(url));

  return job === undefined ? notFound(JOB_NOT_FOUND) : { status: 200, body: toDetail(job) };
}

// POST /api/v1/dashboard/jobs（求人と勤務日をまとめて登録。登録後の詳細を返す）
function createJob(init?: RequestInit): MockResult {
  const parsed = parseFields(readJsonBody(init), REQUIRED_ON_CREATE);

  if (!parsed.ok) {
    return validationError(parsed.errors);
  }

  const fields = parsed.fields;
  const workDates = fields.workDates ?? [];

  if (workDates.some((day) => day.id !== undefined)) {
    return validationError({ workDates: ['新規登録時に勤務日IDは指定できません。'] });
  }

  const job = {
    prefectureId: PRODUCER_PREFECTURE_ID,
    periodStart: null,
    periodEnd: null,
    requirements: null,
    belongings: null,
    notes: null,
    coverImage: null,
    publishStatus: 'draft' as const,
    ...fields,
  } as Omit<StoredJob, 'id' | 'workDates' | 'createdAt' | 'updatedAt'>;
  const consistency = checkConsistency({ ...job, workDates });

  if (consistency !== null) {
    return validationError(consistency);
  }

  const jobs = getState().jobs;
  const now = nowIso();
  let workDateId = newWorkDateId();
  const created: StoredJob = {
    ...job,
    id: nextId(jobs),
    workDates: workDates.map((day) => ({
      id: workDateId++,
      workDate: day.workDate,
      neededCount: day.neededCount,
    })),
    createdAt: now,
    updatedAt: now,
  };

  jobs.push(created);
  save();

  return { status: 201, body: toDetail(created) };
}

// PATCH /api/v1/dashboard/jobs/:jobId（送った項目だけ更新。更新後の詳細を返す）
// workDates を送ると、id 付きは更新・id なしは追加・送らなかった既存の勤務日は削除
function updateJob(url: URL, init?: RequestInit): MockResult {
  const job = findJob(idFromPath(url));

  if (job === undefined) {
    return notFound(JOB_NOT_FOUND);
  }

  const input = readJsonBody(init);

  // 掲載停止中の求人は公開状態を変えられない（入力チェックより先に確かめる）
  if (
    job.publishStatus === 'suspended' &&
    isObject(input) &&
    input.publishStatus !== undefined &&
    input.publishStatus !== job.publishStatus
  ) {
    return conflict('CONTENT_SUSPENDED', '運営により掲載停止中のため、公開状態は変更できません。');
  }

  const parsed = parseFields(input, []);

  if (!parsed.ok) {
    return validationError(parsed.errors);
  }

  const { workDates: inputDates, ...fields } = parsed.fields;
  const existingIds = job.workDates.map((day) => day.id);

  if (inputDates !== undefined) {
    const ids = inputDates.flatMap((day) => (day.id === undefined ? [] : [day.id]));

    if (new Set(ids).size !== ids.length) {
      return validationError({ workDates: ['同じ勤務日IDを複数指定することはできません。'] });
    }

    if (ids.some((id) => !existingIds.includes(id))) {
      return validationError({ workDates: ['指定された勤務日がこの求人に存在しません。'] });
    }
  }

  const next = { ...job, ...fields };
  const nextDates = inputDates ?? job.workDates;
  const consistency = checkConsistency({ ...next, workDates: nextDates });

  if (consistency !== null) {
    return validationError(consistency);
  }

  if (inputDates !== undefined) {
    // 応募者が希望している勤務日は、日付の変更も削除もできない
    const changed = inputDates.some((day) => {
      const before = job.workDates.find((item) => item.id === day.id);

      return before !== undefined && before.workDate !== day.workDate && hasApplicants(job.id, before.id);
    });
    const removed = existingIds.filter((id) => !inputDates.some((day) => day.id === id));

    if (changed) {
      return conflict('WORK_DATE_HAS_APPLICATIONS', '応募者がいる勤務日は変更できません。');
    }

    if (removed.some((id) => hasApplicants(job.id, id))) {
      return conflict('WORK_DATE_HAS_APPLICATIONS', '応募者が希望している勤務日は削除できません。');
    }
  }

  Object.assign(job, fields);

  if (inputDates !== undefined) {
    let workDateId = newWorkDateId();
    job.workDates = inputDates.map((day) => ({
      id: day.id ?? workDateId++,
      workDate: day.workDate,
      neededCount: day.neededCount,
    }));
  }

  job.updatedAt = nowIso();
  save();

  return { status: 200, body: toDetail(job) };
}

// DELETE /api/v1/dashboard/jobs/:jobId（応募されたことがある求人は削除できない）
function deleteJob(url: URL): MockResult {
  const job = findJob(idFromPath(url));

  if (job === undefined) {
    return notFound(JOB_NOT_FOUND);
  }

  if (applicationsOf(job.id).length > 0) {
    return conflict(
      'JOB_HAS_APPLICATIONS',
      '応募履歴がある求人は削除できません。非公開にしてください。',
    );
  }

  const current = getState();
  current.jobs = current.jobs.filter((item) => item.id !== job.id);
  save();

  return { status: 204 };
}

// ---------------------------------------------------------------------------
// 応募者
// ---------------------------------------------------------------------------

const APPLICATION_STATUSES = ['applied', 'screening', 'hired', 'rejected', 'withdrawn', 'completed'];
const UPDATABLE_STATUSES = ['screening', 'hired', 'rejected', 'completed'];

// 生産者が変更できる状態の遷移（長期の求人だけ hired → completed もできる）
function canChange(from: string, to: string, termType: string): boolean {
  const transitions: Record<string, string[]> = {
    applied: ['screening', 'hired', 'rejected'],
    screening: ['hired', 'rejected'],
    hired: termType === 'long' ? ['completed'] : [],
  };

  return (transitions[from] ?? []).includes(to);
}

// GET /api/v1/dashboard/jobs/:jobId/applications?status=&page=&pageSize=（応募の新しい順）
function listApplications(url: URL): MockResult {
  const job = findJob(idFromPath(url, 1));

  if (job === undefined) {
    return notFound(JOB_NOT_FOUND);
  }

  const status = url.searchParams.get('status');

  if (status !== null && !APPLICATION_STATUSES.includes(status)) {
    return validationError({ status: ['応募状態が正しくありません。'] });
  }

  const items = applicationsOf(job.id)
    .filter((application) => status === null || application.status === status)
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt) || b.id - a.id)
    .map(toApplication);
  const page = paginate(items, url);

  return page === null
    ? validationError({ page: ['ページ番号は1以上にしてください。'] })
    : { status: 200, body: page };
}

// PATCH /api/v1/dashboard/jobs/:jobId/applications/:applicationId（選考中・採用・不採用・勤務完了にする）
// 募集人数を超えても採用できる（超えたかを isOverCapacity で返す）
function updateApplication(url: URL, init?: RequestInit): MockResult {
  const input = readJsonBody(init);

  if (!isObject(input) || Object.keys(input).some((name) => name !== 'status')) {
    return validationError(
      Object.fromEntries(
        Object.keys(isObject(input) ? input : {})
          .filter((name) => name !== 'status')
          .map((name) => [name, [UNKNOWN_FIELD]]),
      ),
    );
  }

  if (!UPDATABLE_STATUSES.includes(String(input.status))) {
    return validationError({
      status: [input.status === undefined ? '応募状態を指定してください。' : '指定された応募状態は正しくありません。'],
    });
  }

  const job = findJob(idFromPath(url, 2));

  if (job === undefined) {
    return notFound(JOB_NOT_FOUND);
  }

  const application = applicationsOf(job.id).find((item) => item.id === idFromPath(url));

  if (application === undefined) {
    return notFound(APPLICATION_NOT_FOUND);
  }

  const status = input.status as DashboardJobApplication['status'];

  if (!canChange(application.status, status, job.termType)) {
    return conflict(
      'INVALID_APPLICATION_STATUS_TRANSITION',
      '現在の応募状態から指定された状態には変更できません。',
    );
  }

  const now = nowIso();
  application.status = status;

  if (status === 'hired' || status === 'rejected') {
    application.decidedAt = now;
  }

  application.updatedAt = now;
  save();

  const hiredCount = applicationsOf(job.id).filter((item) => item.status === 'hired').length;

  return {
    status: 200,
    body: {
      id: application.id,
      status: application.status,
      decidedAt: application.decidedAt,
      hiredCount,
      slots: job.slots,
      isOverCapacity: hiredCount > job.slots,
    },
  };
}

// ダッシュボード集計（GET /api/v1/dashboard/summary）用。公開中の求人数と、全状態の応募件数
function summarizeJobs(): { publishedCount: number; applicationCount: number } {
  const current = getState();

  return {
    publishedCount: current.jobs.filter((job) => job.publishStatus === 'public').length,
    applicationCount: current.applications.length,
  };
}

export {
  createJob,
  deleteJob,
  getJob,
  listApplications,
  listJobs,
  summarizeJobs,
  updateApplication,
  updateJob,
};
