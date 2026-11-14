import type {
  DashboardJob,
  DashboardJobApplication,
  DashboardJobSummary,
  JobWorkDate,
} from '../../../types/dashboardJob';
import type { MockResult } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';
import {
  JOB_MAX_LIST_ITEMS,
  JOB_MAX_LIST_ITEM_LENGTH,
  JOB_MAX_WORK_DATES,
  todayInJapan,
} from '../../../utils/jobFormat';
import {
  conflict,
  idFromPath,
  isObject,
  isStale,
  loadState,
  nextEtag,
  nextId,
  notFound,
  nowIso,
  paginate,
  preconditionFailed,
  readHeader,
  readJsonBody,
  saveState,
  validationError,
} from './common';

// ダッシュボード求人のモックストア
//
// 求人（一覧・詳細・登録・更新・削除）、応募者（一覧・採用／不採用）の各モックが、このデータを読み書きする
// - 求人の ETag はレスポンスヘッダー（ETag）で返す。応募の状態を変えると求人の ETag も変わる
// - 応募の etag は本文に含める（"application-{id}-v{版数}"）
// - 一覧・詳細の applicationCount・hiredCount、勤務日の hiredCount・remainingCount は応募データから毎回計算する
//   （採用数は hired / completed の応募。applied / screening は枠を使わない）
//
// 初期データ（ログイン中の生産者 = 山本農園）
//   求人1: りんごの収穫・選果スタッフ（公開中。応募3件: 新着2・辞退1）
//   求人2: 冬の剪定作業補助（公開中。応募1件: 選考中）
//   求人5: りんごジュースの加工・出荷（下書き。応募なし）

const STORAGE_KEY = 'tsunagaru-marche.mock-dashboard-jobs.v1';
const PRODUCER_ID = 1;
const MAX_INT = 2147483647;
const JOB_NOT_FOUND = '求人が見つかりません。';
const APPLICATION_NOT_FOUND = '応募が見つかりません。';

// 採用人数に数える応募の状態
const HIRED_STATUSES = ['hired', 'completed'];
// 削除できなくなる「対応中」の応募の状態
const ACTIVE_STATUSES = ['applied', 'screening', 'hired'];
// 応募があっても変更できる項目（ほかは募集条件・日程の後変更になるため 409）
const EDITABLE_WITH_APPLICATIONS = ['publishStatus', 'slots'];

type StoredWorkDate = { id: number; workDate: string; neededCount: number };

type StoredJob = Omit<DashboardJob, 'workDates' | 'applicationCount' | 'hiredCount'> & {
  workDates: StoredWorkDate[];
};

type StoredApplication = DashboardJobApplication;

type State = {
  jobs: StoredJob[];
  // 求人ID → ETag
  etags: Record<string, string>;
  applications: StoredApplication[];
  // Idempotency-Key → 送信内容と作成した求人ID
  idempotency: Record<string, { body: string; id: number }>;
};

function seedState(): State {
  const jobs: StoredJob[] = [
    {
      id: 1,
      producerId: PRODUCER_ID,
      title: 'りんごの収穫・選果スタッフ',
      prefectureId: 20,
      termType: 'short',
      payUnit: 'hourly',
      payAmount: 1200,
      periodStart: daysFromNow(-14),
      periodEnd: daysFromNow(30),
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
      coverImageKey: 'jobs/job-1-cover.jpg',
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
      producerId: PRODUCER_ID,
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
      coverImageKey: null,
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
      producerId: PRODUCER_ID,
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
      coverImageKey: null,
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
      applicant: {
        id: 6,
        lastName: '松本',
        firstName: '隼',
        email: 'matsumoto@example.com',
        phone: '090-2345-6789',
        isActive: true,
      },
      message: '長野県内に住んでいます。収穫期は週末を中心に勤務できます。',
      answers: [],
      workDates: [
        { id: 2, workDate: daysFromNow(6) },
        { id: 4, workDate: daysFromNow(13) },
      ],
      status: 'applied',
      decidedAt: null,
      createdAt: hoursFromNow(-24 * 1),
      updatedAt: hoursFromNow(-24 * 1),
      etag: '"application-2-v1"',
    },
    {
      id: 1,
      jobId: 1,
      applicant: {
        id: 5,
        lastName: '高橋',
        firstName: 'ゆい',
        email: 'takahashi@example.com',
        phone: '080-3456-7890',
        isActive: true,
      },
      message:
        '週末に家庭菜園をしています。りんご農家の仕事を間近で学びたいです。体力には自信があります。',
      answers: [],
      workDates: [
        { id: 1, workDate: daysFromNow(5) },
        { id: 2, workDate: daysFromNow(6) },
        { id: 3, workDate: daysFromNow(12) },
      ],
      status: 'applied',
      decidedAt: null,
      createdAt: hoursFromNow(-24 * 3),
      updatedAt: hoursFromNow(-24 * 3),
      etag: '"application-1-v1"',
    },
    {
      // 退会した会員の応募（氏名・連絡先は伏せて返る）
      id: 3,
      jobId: 1,
      applicant: {
        id: 9,
        lastName: null,
        firstName: null,
        email: null,
        phone: null,
        isActive: false,
      },
      message: null,
      answers: [],
      workDates: [{ id: 5, workDate: daysFromNow(26) }],
      status: 'withdrawn',
      decidedAt: null,
      createdAt: hoursFromNow(-24 * 6),
      updatedAt: hoursFromNow(-24 * 4),
      etag: '"application-3-v2"',
    },
    {
      id: 4,
      jobId: 2,
      applicant: {
        id: 7,
        lastName: '中村',
        firstName: '陽向',
        email: 'nakamura@example.com',
        phone: '070-4567-8901',
        isActive: true,
      },
      message: '冬の間だけ地元で働きたいと考えています。2日とも勤務できます。',
      answers: [],
      workDates: [
        { id: 7, workDate: daysFromNow(40) },
        { id: 8, workDate: daysFromNow(41) },
      ],
      status: 'screening',
      decidedAt: null,
      createdAt: hoursFromNow(-24 * 2),
      updatedAt: hoursFromNow(-24 * 1),
      etag: '"application-4-v2"',
    },
  ];

  return {
    jobs,
    etags: Object.fromEntries(jobs.map((job) => [job.id, nextEtag('job', job.id)])),
    applications,
    idempotency: {},
  };
}

function isState(value: unknown): value is State {
  return (
    isObject(value) &&
    Array.isArray(value.jobs) &&
    value.jobs.every(
      (job) => isObject(job) && typeof job.id === 'number' && Array.isArray(job.workDates),
    ) &&
    isObject(value.etags) &&
    Array.isArray(value.applications) &&
    value.applications.every(
      (item) =>
        isObject(item) &&
        typeof item.id === 'number' &&
        typeof item.jobId === 'number' &&
        typeof item.etag === 'string' &&
        Array.isArray(item.workDates),
    ) &&
    isObject(value.idempotency)
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
// 参照・計算
// ---------------------------------------------------------------------------

function findJob(id: number): StoredJob | undefined {
  return getState().jobs.find((job) => job.id === id);
}

function etagOf(job: StoredJob): string {
  const { etags } = getState();
  etags[job.id] ??= nextEtag('job', job.id);

  return etags[job.id];
}

// 求人・応募を変更したときに、求人の更新日時と ETag を新しくする
function touchJob(job: StoredJob, now: string): void {
  job.updatedAt = now;
  getState().etags[job.id] = nextEtag('job', job.id, etagOf(job));
}

function etagHeader(job: StoredJob): Record<string, string> {
  return { ETag: etagOf(job) };
}

function applicationsOf(jobId: number): StoredApplication[] {
  return getState().applications.filter((application) => application.jobId === jobId);
}

function isHired(application: StoredApplication): boolean {
  return HIRED_STATUSES.includes(application.status);
}

// 採用人数（同じ会員は1人として数える）
function hiredCountOf(jobId: number, exceptApplicationId?: number): number {
  return new Set(
    applicationsOf(jobId)
      .filter((application) => isHired(application) && application.id !== exceptApplicationId)
      .map((application) => application.applicant.id),
  ).size;
}

function hiredCountOnDate(jobId: number, workDateId: number, exceptApplicationId?: number): number {
  return new Set(
    applicationsOf(jobId)
      .filter(
        (application) =>
          isHired(application) &&
          application.id !== exceptApplicationId &&
          application.workDates.some((day) => day.id === workDateId),
      )
      .map((application) => application.applicant.id),
  ).size;
}

function toWorkDate(jobId: number, day: StoredWorkDate): JobWorkDate {
  const hiredCount = hiredCountOnDate(jobId, day.id);

  return { ...day, hiredCount, remainingCount: Math.max(day.neededCount - hiredCount, 0) };
}

function toDetail(job: StoredJob): DashboardJob {
  return {
    ...job,
    workDates: [...job.workDates]
      .sort((a, b) => a.workDate.localeCompare(b.workDate) || a.id - b.id)
      .map((day) => toWorkDate(job.id, day)),
    applicationCount: applicationsOf(job.id).length,
    hiredCount: hiredCountOf(job.id),
  };
}

function toSummary(job: StoredJob): DashboardJobSummary {
  return {
    id: job.id,
    title: job.title,
    publishStatus: job.publishStatus,
    slots: job.slots,
    applicationCount: applicationsOf(job.id).length,
    hiredCount: hiredCountOf(job.id),
    createdAt: job.createdAt,
    updatedAt: job.updatedAt,
  };
}

function writeResult(job: StoredJob) {
  return {
    id: job.id,
    producerId: job.producerId,
    publishStatus: job.publishStatus,
    createdAt: job.createdAt,
    updatedAt: job.updatedAt,
  };
}

// ---------------------------------------------------------------------------
// 入力チェック（画面側と同じ条件の最低限。本物の API の代わりに 400 / 409 を返す）
// ---------------------------------------------------------------------------

type WorkDateField = { id?: number; workDate: string; neededCount: number };

type JobFields = Partial<
  Omit<StoredJob, 'id' | 'producerId' | 'workDates' | 'createdAt' | 'updatedAt'>
> & { workDates?: WorkDateField[] };

const isText = (value: unknown, max: number) =>
  typeof value === 'string' && value.trim() !== '' && value.length <= max;
const isCount = (value: unknown) =>
  Number.isInteger(value) && Number(value) >= 1 && Number(value) <= MAX_INT;
const isDate = (value: unknown) =>
  typeof value === 'string' &&
  /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  !Number.isNaN(Date.parse(`${value}T00:00:00Z`)) &&
  new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
const isLines = (value: unknown) =>
  value === null ||
  (Array.isArray(value) &&
    value.length <= JOB_MAX_LIST_ITEMS &&
    value.every(
      (line) =>
        typeof line === 'string' && line.trim() !== '' && line.length <= JOB_MAX_LIST_ITEM_LENGTH,
    ));

const jobChecks: Record<keyof JobFields, (value: unknown) => boolean> = {
  title: (value) => isText(value, 100),
  prefectureId: (value) => Number.isInteger(value) && Number(value) >= 1 && Number(value) <= 47,
  termType: (value) => value === 'one_day' || value === 'short' || value === 'long',
  payUnit: (value) => value === 'hourly' || value === 'daily' || value === 'monthly',
  payAmount: (value) => Number.isInteger(value) && Number(value) >= 0 && Number(value) <= MAX_INT,
  periodStart: (value) => value === null || isDate(value),
  periodEnd: (value) => value === null || isDate(value),
  workHours: (value) => isText(value, 50),
  workPlace: (value) => isText(value, 200),
  slots: isCount,
  description: (value) => isText(value, 10000),
  requirements: isLines,
  belongings: isLines,
  notes: isLines,
  inexperiencedOk: (value) => typeof value === 'boolean',
  coverImageKey: (value) =>
    value === null || (typeof value === 'string' && value !== '' && value.length <= 500),
  publishStatus: (value) => value === 'draft' || value === 'public' || value === 'private',
  workDates: (value) =>
    Array.isArray(value) &&
    value.length <= JOB_MAX_WORK_DATES &&
    value.every(
      (day) =>
        isObject(day) &&
        (day.id === undefined || isCount(day.id)) &&
        isDate(day.workDate) &&
        isCount(day.neededCount),
    ),
};

const ALL_FIELDS = Object.keys(jobChecks);

type ParseResult =
  | { ok: true; fields: JobFields }
  | { ok: false; errors: Record<string, string[]> };

// 送られた項目だけチェックする（required の項目は、送られていなければエラー）。未知の項目は 400
function parseFields(input: unknown, required: string[]): ParseResult {
  if (!isObject(input) || Object.keys(input).length === 0) {
    return { ok: false, errors: { body: ['リクエストの形式が正しくありません。'] } };
  }

  const errors: Record<string, string[]> = {};
  const fields: Record<string, unknown> = {};

  for (const name of Object.keys(input)) {
    if (!ALL_FIELDS.includes(name)) {
      errors[name] = ['指定できない項目です。'];
    }
  }

  for (const [name, check] of Object.entries(jobChecks)) {
    if (!(name in input)) {
      if (required.includes(name)) {
        errors[name] = ['入力してください。'];
      }
    } else if (check(input[name])) {
      fields[name] = input[name];
    } else {
      errors[name] = ['正しい値を入力してください。'];
    }
  }

  return Object.keys(errors).length > 0
    ? { ok: false, errors }
    : { ok: true, fields: fields as JobFields };
}

// 項目どうしの条件（募集期間・勤務日・必要人数）。問題があれば 400 の details を返す
function checkConsistency(
  job: { periodStart: string | null; periodEnd: string | null; slots: number; workDates: WorkDateField[] },
  existingIds: number[],
): Record<string, string[]> | null {
  const errors: Record<string, string[]> = {};
  const today = todayInJapan();

  if (job.periodStart !== null && job.periodEnd !== null && job.periodStart > job.periodEnd) {
    errors.periodEnd = ['募集終了日は募集開始日以降にしてください。'];
  }

  const dates = job.workDates.map((day) => day.workDate);
  const ids = job.workDates.flatMap((day) => (day.id === undefined ? [] : [day.id]));

  if (new Set(dates).size !== dates.length) {
    errors.workDates = ['同じ勤務日が重複しています。'];
  } else if (new Set(ids).size !== ids.length || ids.some((id) => !existingIds.includes(id))) {
    errors.workDates = ['勤務日の指定が正しくありません。'];
  } else if (job.workDates.some((day) => day.id === undefined && day.workDate < today)) {
    errors.workDates = ['新しく追加する勤務日は今日以降にしてください。'];
  } else if (job.workDates.some((day) => day.neededCount > job.slots)) {
    errors.workDates = ['勤務日ごとの必要人数は募集人数以下にしてください。'];
  }

  return Object.keys(errors).length > 0 ? errors : null;
}

// 公開に必要な条件（勤務日がある求人は、今日以降の勤務日が1件以上必要）
function canPublish(workDates: { workDate: string }[]): boolean {
  return workDates.length === 0 || workDates.some((day) => day.workDate >= todayInJapan());
}

function toStoredWorkDates(workDates: WorkDateField[]): StoredWorkDate[] {
  let lastId = Math.max(
    0,
    ...getState().jobs.flatMap((job) => job.workDates.map((day) => day.id)),
  );

  return workDates.map((day) => {
    if (day.id !== undefined) {
      return { id: day.id, workDate: day.workDate, neededCount: day.neededCount };
    }

    lastId += 1;

    return { id: lastId, workDate: day.workDate, neededCount: day.neededCount };
  });
}

// 同じ Idempotency-Key の再送なら前回作成したIDを返す。同じキーで内容が違えば 409。初回は null
function replayed(init: RequestInit | undefined): number | MockResult | null {
  const key = readHeader(init, 'Idempotency-Key');
  const saved = key === null ? undefined : getState().idempotency[key];

  if (saved === undefined) {
    return null;
  }

  return saved.body === init?.body
    ? saved.id
    : conflict('CONFLICT', '同じ Idempotency-Key で異なる内容が送られました。');
}

function remember(init: RequestInit | undefined, id: number): void {
  const key = readHeader(init, 'Idempotency-Key');

  if (key !== null && typeof init?.body === 'string') {
    getState().idempotency[key] = { body: init.body, id };
  }
}

function forbiddenSuspended(): MockResult {
  return {
    status: 403,
    body: { errorCode: 'FORBIDDEN', errorMsg: '掲載停止中の求人は変更できません。' },
  };
}

// ---------------------------------------------------------------------------
// 求人
// ---------------------------------------------------------------------------

const PUBLISH_STATUSES = ['draft', 'public', 'private', 'suspended'];

// GET /api/v1/dashboard/jobs?publishStatus=&page=（作成の新しい順）
function listJobs(url: URL): MockResult {
  const publishStatus = url.searchParams.get('publishStatus');

  if (publishStatus !== null && !PUBLISH_STATUSES.includes(publishStatus)) {
    return validationError({ publishStatus: ['指定できない値です。'] });
  }

  const items = getState()
    .jobs.filter((job) => publishStatus === null || job.publishStatus === publishStatus)
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt) || b.id - a.id)
    .map(toSummary);
  const page = paginate(items, url);

  return page === null
    ? validationError({ page: ['正しい値を指定してください。'] })
    : { status: 200, body: page };
}

// GET /api/v1/dashboard/jobs/:jobId
function getJob(url: URL): MockResult {
  const job = findJob(idFromPath(url));

  return job === undefined
    ? notFound(JOB_NOT_FOUND)
    : { status: 200, body: toDetail(job), headers: etagHeader(job) };
}

// POST /api/v1/dashboard/jobs（求人と勤務日をまとめて登録）
function createJob(init?: RequestInit): MockResult {
  const replay = replayed(init);

  if (typeof replay === 'number') {
    const created = findJob(replay);

    if (created !== undefined) {
      return { status: 201, body: writeResult(created), headers: etagHeader(created) };
    }
  } else if (replay !== null) {
    return replay;
  }

  const parsed = parseFields(readJsonBody(init), ALL_FIELDS);

  if (!parsed.ok) {
    return validationError(parsed.errors);
  }

  const fields = parsed.fields as Required<JobFields>;
  const consistency = checkConsistency(fields, []);

  if (consistency !== null) {
    return validationError(consistency);
  }

  if (fields.publishStatus === 'public' && !canPublish(fields.workDates)) {
    return conflict('CONFLICT', '公開するには、今日以降の勤務日が1日以上必要です。');
  }

  const jobs = getState().jobs;
  const id = nextId(jobs);
  const now = nowIso();
  const job: StoredJob = {
    ...fields,
    id,
    producerId: PRODUCER_ID,
    workDates: toStoredWorkDates(fields.workDates),
    createdAt: now,
    updatedAt: now,
  };

  jobs.push(job);
  getState().etags[id] = nextEtag('job', id);
  remember(init, id);
  save();

  return { status: 201, body: writeResult(job), headers: etagHeader(job) };
}

// PATCH /api/v1/dashboard/jobs/:jobId（送った項目だけ更新。workDates は送った内容で置き換え）
function updateJob(url: URL, init?: RequestInit): MockResult {
  const job = findJob(idFromPath(url));

  if (job === undefined) {
    return notFound(JOB_NOT_FOUND);
  }

  if (isStale(init, etagOf(job))) {
    return preconditionFailed();
  }

  if (job.publishStatus === 'suspended') {
    return forbiddenSuspended();
  }

  const parsed = parseFields(readJsonBody(init), []);

  if (!parsed.ok) {
    return validationError(parsed.errors);
  }

  const fields = parsed.fields;
  const applications = applicationsOf(job.id);

  // 応募がある求人は、公開状態と募集人数以外を変更できない（同じ値を送っても 409）
  if (
    applications.length > 0 &&
    Object.keys(fields).some((name) => !EDITABLE_WITH_APPLICATIONS.includes(name))
  ) {
    return conflict('CONFLICT', '応募がある求人は公開状態と募集人数以外を変更できません。');
  }

  // 募集人数は、採用済みの人数・既存の勤務日の必要人数より少なくできない
  if (fields.slots !== undefined) {
    const hiredOnDates = job.workDates.map((day) => hiredCountOnDate(job.id, day.id));
    const neededCounts =
      fields.workDates === undefined ? job.workDates.map((day) => day.neededCount) : [];

    if (
      fields.slots < hiredCountOf(job.id) ||
      fields.slots < Math.max(0, ...hiredOnDates, ...neededCounts)
    ) {
      return conflict('CAPACITY_CONFLICT', '採用済みの人数・勤務日の必要人数より少なくはできません。');
    }
  }

  // 既存の勤務日は ID 付きで送られる（今日以降のチェックは追加分だけ）
  const next = {
    periodStart: fields.periodStart === undefined ? job.periodStart : fields.periodStart,
    periodEnd: fields.periodEnd === undefined ? job.periodEnd : fields.periodEnd,
    slots: fields.slots ?? job.slots,
    workDates: fields.workDates ?? job.workDates,
  };
  const consistency = checkConsistency(
    next,
    job.workDates.map((day) => day.id),
  );

  if (consistency !== null) {
    return validationError(consistency);
  }

  const nextStatus = fields.publishStatus ?? job.publishStatus;

  if (nextStatus === 'public' && !canPublish(next.workDates)) {
    return conflict('CONFLICT', '公開するには、今日以降の勤務日が1日以上必要です。');
  }

  const before = JSON.stringify(job);
  const { workDates, ...rest } = fields;
  Object.assign(job, rest);

  if (workDates !== undefined) {
    job.workDates = toStoredWorkDates(workDates);
  }

  // 変更がなければ更新日時・ETag はそのまま
  if (JSON.stringify(job) !== before) {
    touchJob(job, nowIso());
    save();
  }

  return { status: 200, body: writeResult(job), headers: etagHeader(job) };
}

// DELETE /api/v1/dashboard/jobs/:jobId（対応中の応募が残っていると削除できない）
function deleteJob(url: URL, init?: RequestInit): MockResult {
  const job = findJob(idFromPath(url));

  if (job === undefined) {
    return notFound(JOB_NOT_FOUND);
  }

  if (isStale(init, etagOf(job))) {
    return preconditionFailed();
  }

  if (job.publishStatus === 'suspended') {
    return forbiddenSuspended();
  }

  if (applicationsOf(job.id).some((application) => ACTIVE_STATUSES.includes(application.status))) {
    return conflict('ACTIVE_APPLICATIONS_EXIST', '対応中の応募があるため削除できません。');
  }

  const current = getState();
  current.jobs = current.jobs.filter((item) => item.id !== job.id);
  delete current.etags[job.id];
  save();

  return { status: 204 };
}

// ---------------------------------------------------------------------------
// 応募者
// ---------------------------------------------------------------------------

const APPLICATION_STATUSES = ['applied', 'screening', 'hired', 'rejected', 'withdrawn', 'completed'];

// 生産者が変更できる状態の遷移
const TRANSITIONS: Record<string, string[]> = {
  applied: ['screening', 'hired', 'rejected'],
  screening: ['hired', 'rejected'],
};

// GET /api/v1/dashboard/jobs/:jobId/applications?status=&page=（応募の新しい順）
function listApplications(url: URL): MockResult {
  const job = findJob(idFromPath(url, 1));

  if (job === undefined) {
    return notFound(JOB_NOT_FOUND);
  }

  const status = url.searchParams.get('status');

  if (status !== null && !APPLICATION_STATUSES.includes(status)) {
    return validationError({ status: ['指定できない値です。'] });
  }

  const items = applicationsOf(job.id)
    .filter((application) => status === null || application.status === status)
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt) || b.id - a.id)
    .map((application) => ({
      ...application,
      workDates: [...application.workDates].sort(
        (a, b) => a.workDate.localeCompare(b.workDate) || a.id - b.id,
      ),
    }));
  const page = paginate(items, url);

  return page === null
    ? validationError({ page: ['正しい値を指定してください。'] })
    : { status: 200, body: page };
}

// PATCH /api/v1/dashboard/jobs/:jobId/applications/:applicationId（選考中・採用・不採用にする）
function updateApplication(url: URL, init?: RequestInit): MockResult {
  const job = findJob(idFromPath(url, 2));
  const application = getState().applications.find(
    (item) => item.id === idFromPath(url) && item.jobId === job?.id,
  );

  if (job === undefined || application === undefined) {
    return notFound(job === undefined ? JOB_NOT_FOUND : APPLICATION_NOT_FOUND);
  }

  if (isStale(init, application.etag)) {
    return {
      status: 412,
      body: {
        errorCode: 'PRECONDITION_FAILED',
        errorMsg: '応募が更新されています。再読み込みしてください。',
      },
    };
  }

  if (job.publishStatus === 'suspended') {
    return forbiddenSuspended();
  }

  const input = readJsonBody(init);

  if (
    !isObject(input) ||
    Object.keys(input).some((name) => name !== 'status') ||
    !['screening', 'hired', 'rejected'].includes(String(input.status))
  ) {
    return validationError({
      status: ['screening・hired・rejected のどれかを指定してください。'],
    });
  }

  const status = input.status as 'screening' | 'hired' | 'rejected';

  // 同じ状態の指定は何も変えずに返す
  if (status === application.status) {
    return { status: 200, body: application, headers: { ETag: application.etag } };
  }

  if (!(TRANSITIONS[application.status] ?? []).includes(status)) {
    return conflict('INVALID_TRANSITION', 'この応募の状態は変更できません。');
  }

  if (status === 'hired') {
    if (job.publishStatus !== 'public') {
      return conflict('CONFLICT', '公開中の求人の応募だけ採用できます。');
    }

    if (!application.applicant.isActive) {
      return conflict('CONFLICT', '退会した会員は採用できません。');
    }

    if (application.workDates.some((day) => day.workDate < todayInJapan())) {
      return conflict('CONFLICT', '希望日が過ぎているため採用できません。');
    }

    const isFull =
      hiredCountOf(job.id, application.id) >= job.slots ||
      application.workDates.some((day) => {
        const workDate = job.workDates.find((item) => item.id === day.id);

        return (
          workDate === undefined ||
          hiredCountOnDate(job.id, day.id, application.id) >= workDate.neededCount
        );
      });

    if (isFull) {
      return conflict('CAPACITY_CONFLICT', '募集人数に達しているため採用できません。');
    }
  }

  const now = nowIso();
  application.status = status;
  application.decidedAt = status === 'screening' ? null : now;
  application.updatedAt = now;
  application.etag = nextEtag('application', application.id, application.etag);
  touchJob(job, now);
  save();

  return { status: 200, body: application, headers: { ETag: application.etag } };
}

// ダッシュボード集計（GET /api/v1/dashboard/summary）用。公開中の求人数と、全状態の応募件数
function summarizeJobs(): { publishedCount: number; applicationCount: number } {
  const current = getState();
  const jobIds = current.jobs.map((job) => job.id);

  return {
    publishedCount: current.jobs.filter((job) => job.publishStatus === 'public').length,
    // 削除した求人の応募は求人管理から見えないため数えない
    applicationCount: current.applications.filter((application) =>
      jobIds.includes(application.jobId),
    ).length,
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
