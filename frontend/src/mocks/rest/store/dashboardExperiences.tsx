import type {
  DashboardExperience,
  DashboardExperienceSummary,
  ExperienceApplication,
  ExperienceImage,
  ExperienceSlot,
  ExperienceSlotStatus,
} from '../../../types/dashboardExperience';
import type { MockResult } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';
import {
  EXPERIENCE_MAX_IMAGES,
  EXPERIENCE_MAX_LIST_ITEMS,
  EXPERIENCE_MAX_LIST_ITEM_LENGTH,
} from '../../../utils/experienceLimits';
import {
  conflict,
  idFromPath,
  imageUrlFor,
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

// ダッシュボード体験のモックストア
//
// 体験（一覧・詳細・登録・更新・削除）、予約枠（一覧・追加・変更・削除）、申込者一覧の各モックが、このデータを読み書きする
// - 体験の ETag はレスポンスヘッダー（ETag）で返す。予約枠を変えると体験の ETag も変わる
// - 予約枠の etag は本文に含める（"slot-{id}-v{版数}"）
// - 一覧の slotCount・applicationCount・nextStartAt、予約枠の reservedCount・remainingCapacity は申込データから毎回計算する
//
// 初期データ（ログイン中の生産者 = 山本農園）
//   体験1: 蜜入りりんごの収穫体験（公開中。枠1・枠2、申込7件）
//   体験2: 冬の剪定見学（公開中。枠3、申込2件）

const STORAGE_KEY = 'tsunagaru-marche.mock-dashboard-experiences.v1';
const PRODUCER_ID = 1;
const MAX_INT = 2147483647;
const EXPERIENCE_NOT_FOUND = '対象の体験が見つかりません。';
const SLOT_NOT_FOUND = '対象の予約枠が見つかりません。';

// 予約人数・削除可否に数える申込の状態
const ACTIVE_STATUSES = ['applied', 'confirmed', 'attended'];

// 予約があると変更できない体験の項目（参加者に案内済みの内容）
const LOCKED_FIELDS = [
  'title',
  'description',
  'prefectureId',
  'place',
  'priceAdult',
  'priceChild',
] as const;

type StoredSlot = Omit<ExperienceSlot, 'reservedCount' | 'remainingCapacity'> & {
  // 申込履歴がある枠は、申込者一覧に表示するため削除後も残す
  deleted: boolean;
};

type StoredApplication = Omit<ExperienceApplication, 'slot'> & {
  experienceId: number;
  slotId: number;
};

type State = {
  experiences: DashboardExperience[];
  // 体験ID → ETag
  etags: Record<string, string>;
  slots: StoredSlot[];
  applications: StoredApplication[];
  // Idempotency-Key → 送られた本文と作成したID（同じキーの再送には同じ結果を返す）
  idempotency: Record<string, { body: string; id: number }>;
};

function seedState(): State {
  const slotStart = (days: number) => `${daysFromNow(days)}T10:00:00+09:00`;
  const member = (id: number, lastName: string, firstName: string) => ({
    id,
    lastName,
    firstName,
    isActive: true,
  });
  const application = (
    fields: Omit<StoredApplication, 'reservationNo' | 'policyAgreedAt' | 'infantCount'>,
  ): StoredApplication => ({
    ...fields,
    infantCount: 0,
    reservationNo: `RSV-${String(fields.id).padStart(6, '0')}`,
    policyAgreedAt: fields.createdAt,
  });

  return {
    experiences: [
      {
        id: 1,
        producerId: PRODUCER_ID,
        title: '蜜入りりんごの収穫体験とアップルパイづくり',
        prefectureId: 20,
        description:
          '北アルプスのふもと、安曇野の山本農園で蜜入りりんご「サンふじ」の収穫を体験できます。\n収穫したりんごを使って、農園のキッチンでアップルパイづくりにも挑戦します。焼きたてのパイはその場で味わえるほか、お土産としてお持ち帰りいただけます。',
        place: '長野県 安曇野市（山本農園）',
        priceAdult: 3500,
        priceChild: 2000,
        ageCondition: '小学生以上',
        familyOk: true,
        beginnerOk: true,
        flow: [
          '10:00 集合・農園の紹介',
          '10:20 りんごの収穫体験',
          '11:30 アップルパイづくり',
          '12:30 試食・休憩',
          '13:00 解散',
        ],
        belongings: ['汚れてもよい服装', '軍手', '飲み物', 'エプロン'],
        notes: [
          '雨天の場合は収穫を中止し、アップルパイづくりのみ行います。',
          '駐車場は農園内に10台分あります。',
        ],
        cancelPolicy:
          '開催日の3日前まではキャンセル無料です。2日前〜前日は参加費の50%、当日は100%のキャンセル料がかかります。',
        publishStatus: 'public',
        images: [
          {
            id: 1,
            imageKey: 'experiences/1/apple-harvest.jpg',
            url: 'https://picsum.photos/seed/exp1-harvest/800/600',
            sortOrder: 0,
          },
          {
            id: 2,
            imageKey: 'experiences/1/apple-pie.jpg',
            url: 'https://picsum.photos/seed/exp1-pie/800/600',
            sortOrder: 1,
          },
          {
            id: 3,
            imageKey: 'experiences/1/orchard.jpg',
            url: 'https://picsum.photos/seed/exp1-orchard/800/600',
            sortOrder: 2,
          },
        ],
        createdAt: hoursFromNow(-24 * 30),
        updatedAt: hoursFromNow(-3),
      },
      {
        id: 2,
        producerId: PRODUCER_ID,
        title: '冬の剪定見学とりんご農家の昼ごはん',
        prefectureId: 20,
        description:
          '冬のりんご畑で、来年の実りを左右する剪定作業を見学します。\n見学のあとは、りんご農家の家庭料理を囲んで昼ごはんをいただきます。',
        place: '長野県 安曇野市（山本農園）',
        priceAdult: 2500,
        priceChild: null,
        ageCondition: '中学生以上',
        familyOk: false,
        beginnerOk: true,
        flow: ['10:00 集合', '10:15 剪定の見学・説明', '12:00 昼ごはん', '13:00 解散'],
        belongings: ['防寒着', '長靴'],
        notes: ['雪の状況により、見学場所を変更する場合があります。'],
        cancelPolicy:
          '開催日の3日前まではキャンセル無料です。それ以降は参加費の100%のキャンセル料がかかります。',
        publishStatus: 'public',
        images: [
          {
            id: 4,
            imageKey: 'experiences/2/pruning.jpg',
            url: 'https://picsum.photos/seed/exp2-pruning/800/600',
            sortOrder: 0,
          },
        ],
        createdAt: hoursFromNow(-24 * 7),
        updatedAt: hoursFromNow(-24 * 2),
      },
    ],
    etags: { 1: '"experience-1-v4"', 2: '"experience-2-v2"' },
    slots: [
      {
        id: 1,
        experienceId: 1,
        startAt: slotStart(10),
        durationMin: 180,
        capacity: 20,
        status: 'open',
        etag: '"slot-1-v8"',
        createdAt: hoursFromNow(-24 * 30),
        updatedAt: hoursFromNow(-3),
        deleted: false,
      },
      {
        id: 2,
        experienceId: 1,
        startAt: slotStart(17),
        durationMin: 180,
        capacity: 20,
        status: 'open',
        etag: '"slot-2-v2"',
        createdAt: hoursFromNow(-24 * 14),
        updatedAt: hoursFromNow(-24 * 2),
        deleted: false,
      },
      {
        id: 3,
        experienceId: 2,
        startAt: slotStart(90),
        durationMin: 180,
        capacity: 10,
        status: 'open',
        etag: '"slot-3-v1"',
        createdAt: hoursFromNow(-24 * 7),
        updatedAt: hoursFromNow(-24 * 7),
        deleted: false,
      },
    ],
    applications: [
      application({
        id: 59,
        experienceId: 2,
        slotId: 3,
        user: member(3, '田中', '一郎'),
        adultCount: 2,
        childCount: 0,
        representativeName: '田中 一郎',
        phone: '090-3333-6789',
        message: '剪定の様子を見られるのを楽しみにしています。',
        totalAmount: 5000,
        status: 'confirmed',
        createdAt: hoursFromNow(-24),
      }),
      application({
        id: 58,
        experienceId: 2,
        slotId: 3,
        // 退会済み会員の予約は氏名・連絡先が null
        user: { id: 9, lastName: null, firstName: null, isActive: false },
        adultCount: 1,
        childCount: 0,
        representativeName: null,
        phone: null,
        message: null,
        totalAmount: 2500,
        status: 'canceled',
        createdAt: hoursFromNow(-24 * 5),
      }),
      application({
        id: 57,
        experienceId: 1,
        slotId: 1,
        user: member(6, '松本', '隼'),
        adultCount: 3,
        childCount: 0,
        representativeName: '松本 隼',
        phone: '090-6666-1234',
        message: '友人3人で参加します。車で伺う予定です。',
        totalAmount: 10500,
        status: 'applied',
        createdAt: hoursFromNow(-3),
      }),
      application({
        id: 56,
        experienceId: 1,
        slotId: 1,
        user: member(5, '高橋', 'ゆい'),
        adultCount: 2,
        childCount: 1,
        representativeName: '高橋 ゆい',
        phone: '080-5555-2345',
        message: '子どもが小学2年生です。アップルパイづくりを楽しみにしています。',
        totalAmount: 9000,
        status: 'applied',
        createdAt: hoursFromNow(-20),
      }),
      application({
        id: 55,
        experienceId: 1,
        slotId: 2,
        user: member(8, '伊藤', '誠'),
        adultCount: 2,
        childCount: 1,
        representativeName: '伊藤 誠',
        phone: '090-8888-3456',
        message: null,
        totalAmount: 9000,
        status: 'confirmed',
        createdAt: hoursFromNow(-24 * 2),
      }),
      application({
        id: 54,
        experienceId: 1,
        slotId: 1,
        user: member(7, '森', 'さくら'),
        adultCount: 2,
        childCount: 0,
        representativeName: '森 さくら',
        phone: '070-7777-4567',
        message: null,
        totalAmount: 7000,
        status: 'canceled',
        createdAt: hoursFromNow(-24 * 4),
      }),
      application({
        id: 53,
        experienceId: 1,
        slotId: 1,
        user: member(4, '鈴木', '美咲'),
        adultCount: 2,
        childCount: 2,
        representativeName: '鈴木 美咲',
        phone: '080-4444-5678',
        message: 'りんごアレルギーはありません。よろしくお願いします。',
        totalAmount: 11000,
        status: 'confirmed',
        createdAt: hoursFromNow(-24 * 6),
      }),
      application({
        id: 52,
        experienceId: 1,
        slotId: 1,
        user: member(3, '田中', '一郎'),
        adultCount: 2,
        childCount: 0,
        representativeName: '田中 一郎',
        phone: '090-3333-6789',
        message: null,
        totalAmount: 7000,
        status: 'confirmed',
        createdAt: hoursFromNow(-24 * 9),
      }),
      application({
        id: 51,
        experienceId: 1,
        slotId: 1,
        // 予約代表者は会員本人と同一とは限らない（ここでは夫の名前で予約）
        user: member(2, '佐藤', '花子'),
        adultCount: 2,
        childCount: 2,
        representativeName: '佐藤 大輔',
        phone: '080-2222-7890',
        message: '家族4人で参加します。',
        totalAmount: 11000,
        status: 'confirmed',
        createdAt: hoursFromNow(-24 * 12),
      }),
    ],
    idempotency: {},
  };
}

function isState(value: unknown): value is State {
  return (
    isObject(value) &&
    Array.isArray(value.experiences) &&
    value.experiences.every(
      (item) => isObject(item) && typeof item.id === 'number' && Array.isArray(item.images),
    ) &&
    isObject(value.etags) &&
    Array.isArray(value.slots) &&
    value.slots.every(
      (slot) =>
        isObject(slot) &&
        typeof slot.id === 'number' &&
        typeof slot.experienceId === 'number' &&
        typeof slot.startAt === 'string' &&
        typeof slot.etag === 'string',
    ) &&
    Array.isArray(value.applications) &&
    value.applications.every(
      (item) =>
        isObject(item) && typeof item.slotId === 'number' && typeof item.experienceId === 'number',
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

function findExperience(id: number): DashboardExperience | undefined {
  return getState().experiences.find((experience) => experience.id === id);
}

function etagOf(experience: DashboardExperience): string {
  const { etags } = getState();
  etags[experience.id] ??= nextEtag('experience', experience.id);

  return etags[experience.id];
}

// 体験・予約枠を変更したときに、体験の更新日時と ETag を新しくする
function touchExperience(experience: DashboardExperience, now: string): void {
  experience.updatedAt = now;
  getState().etags[experience.id] = nextEtag('experience', experience.id, etagOf(experience));
}

function etagHeader(experience: DashboardExperience): Record<string, string> {
  return { ETag: etagOf(experience) };
}

function applicationsOf(filter: { experienceId?: number; slotId?: number }): StoredApplication[] {
  return getState().applications.filter(
    (application) =>
      (filter.experienceId === undefined || application.experienceId === filter.experienceId) &&
      (filter.slotId === undefined || application.slotId === filter.slotId),
  );
}

function isActive(application: StoredApplication): boolean {
  return ACTIVE_STATUSES.includes(application.status);
}

function liveSlotsOf(experienceId: number): StoredSlot[] {
  return getState().slots.filter((slot) => slot.experienceId === experienceId && !slot.deleted);
}

function toSlot(slot: StoredSlot): ExperienceSlot {
  const reservedCount = applicationsOf({ slotId: slot.id })
    .filter(isActive)
    .reduce((sum, item) => sum + item.adultCount + item.childCount + item.infantCount, 0);
  const { deleted: _deleted, ...fields } = slot;

  return {
    ...fields,
    reservedCount,
    remainingCapacity: Math.max(slot.capacity - reservedCount, 0),
  };
}

function toSummary(experience: DashboardExperience): DashboardExperienceSummary {
  const slots = liveSlotsOf(experience.id);
  const now = Date.now();
  const upcoming = slots
    .filter((slot) => slot.status !== 'canceled' && Date.parse(slot.startAt) > now)
    .sort((a, b) => Date.parse(a.startAt) - Date.parse(b.startAt));

  return {
    id: experience.id,
    title: experience.title,
    publishStatus: experience.publishStatus,
    prefectureId: experience.prefectureId,
    priceAdult: experience.priceAdult,
    priceChild: experience.priceChild,
    slotCount: slots.length,
    applicationCount: applicationsOf({ experienceId: experience.id }).length,
    nextStartAt: upcoming[0]?.startAt ?? null,
    createdAt: experience.createdAt,
    updatedAt: experience.updatedAt,
  };
}

function writeResult(experience: DashboardExperience) {
  return {
    id: experience.id,
    producerId: experience.producerId,
    publishStatus: experience.publishStatus,
    createdAt: experience.createdAt,
    updatedAt: experience.updatedAt,
  };
}

// images[].imageKey を画像の配列にする（すでにある画像は ID・URL をそのまま使う）
function toImages(keys: string[], current: ExperienceImage[]): ExperienceImage[] {
  let lastId = Math.max(
    0,
    ...getState().experiences.flatMap((experience) => experience.images.map((image) => image.id)),
  );

  return keys.map((imageKey, sortOrder) => {
    const existing = current.find((image) => image.imageKey === imageKey);

    if (existing !== undefined) {
      return { ...existing, sortOrder };
    }

    lastId += 1;

    return { id: lastId, imageKey, url: imageUrlFor(imageKey), sortOrder };
  });
}

// ---------------------------------------------------------------------------
// 入力チェック（画面側と同じ条件の最低限。本物の API の代わりに 400 を返す）
// ---------------------------------------------------------------------------

type ExperienceFields = Partial<
  Omit<DashboardExperience, 'id' | 'producerId' | 'images' | 'createdAt' | 'updatedAt'>
> & { images?: { imageKey: string }[] };

const isText = (value: unknown, max: number) =>
  typeof value === 'string' && value.trim() !== '' && value.length <= max;
const isPrice = (value: unknown) =>
  Number.isInteger(value) && Number(value) >= 0 && Number(value) <= MAX_INT;
const isLines = (value: unknown) =>
  value === null ||
  (Array.isArray(value) &&
    value.length <= EXPERIENCE_MAX_LIST_ITEMS &&
    value.every(
      (line) =>
        typeof line === 'string' && line !== '' && line.length <= EXPERIENCE_MAX_LIST_ITEM_LENGTH,
    ));

const experienceChecks: Record<keyof ExperienceFields, (value: unknown) => boolean> = {
  title: (value) => isText(value, 100),
  prefectureId: (value) => Number.isInteger(value) && Number(value) >= 1 && Number(value) <= 47,
  description: (value) => isText(value, 10000),
  place: (value) => isText(value, 200),
  priceAdult: isPrice,
  priceChild: (value) => value === null || isPrice(value),
  ageCondition: (value) => value === null || (typeof value === 'string' && value.length <= 50),
  familyOk: (value) => typeof value === 'boolean',
  beginnerOk: (value) => typeof value === 'boolean',
  flow: isLines,
  belongings: isLines,
  notes: isLines,
  cancelPolicy: (value) => isText(value, 10000),
  publishStatus: (value) => value === 'draft' || value === 'public' || value === 'private',
  images: (value) =>
    Array.isArray(value) &&
    value.length <= EXPERIENCE_MAX_IMAGES &&
    value.every(
      (image) => isObject(image) && typeof image.imageKey === 'string' && image.imageKey !== '',
    ) &&
    new Set(value.map((image) => (image as { imageKey: string }).imageKey)).size === value.length,
};

type ParseResult<T> = { ok: true; fields: T } | { ok: false; errors: Record<string, string[]> };

// 送られた項目だけチェックする（required の項目は、送られていなければエラー）
function parseFields<T>(
  input: unknown,
  checks: Record<string, (value: unknown) => boolean>,
  required: string[],
): ParseResult<T> {
  if (!isObject(input)) {
    return { ok: false, errors: { body: ['リクエストの形式が正しくありません。'] } };
  }

  const errors: Record<string, string[]> = {};
  const fields: Record<string, unknown> = {};

  for (const [name, check] of Object.entries(checks)) {
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

  return Object.keys(errors).length > 0 ? { ok: false, errors } : { ok: true, fields: fields as T };
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

// ---------------------------------------------------------------------------
// 体験
// ---------------------------------------------------------------------------

const PUBLISH_STATUSES = ['draft', 'public', 'private', 'suspended'];

// GET /api/v1/dashboard/experiences?publishStatus=&page=（作成の新しい順）
function listExperiences(url: URL): MockResult {
  const publishStatus = url.searchParams.get('publishStatus');

  if (publishStatus !== null && !PUBLISH_STATUSES.includes(publishStatus)) {
    return validationError({ publishStatus: ['指定できない値です。'] });
  }

  const items = getState()
    .experiences.filter(
      (experience) => publishStatus === null || experience.publishStatus === publishStatus,
    )
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt) || b.id - a.id)
    .map(toSummary);
  const page = paginate(items, url);

  return page === null
    ? validationError({ page: ['正しい値を指定してください。'] })
    : { status: 200, body: page };
}

// GET /api/v1/dashboard/experiences/:experienceId
function getExperience(url: URL): MockResult {
  const experience = findExperience(idFromPath(url));

  return experience === undefined
    ? notFound(EXPERIENCE_NOT_FOUND)
    : { status: 200, body: experience, headers: etagHeader(experience) };
}

// POST /api/v1/dashboard/experiences
function createExperience(init?: RequestInit): MockResult {
  const replay = replayed(init);

  if (typeof replay === 'number') {
    const created = findExperience(replay);

    if (created !== undefined) {
      return { status: 201, body: writeResult(created), headers: etagHeader(created) };
    }
  } else if (replay !== null) {
    return replay;
  }

  const parsed = parseFields<ExperienceFields>(readJsonBody(init), experienceChecks, [
    'title',
    'prefectureId',
    'description',
    'place',
    'priceAdult',
    'cancelPolicy',
    'publishStatus',
  ]);

  if (!parsed.ok) {
    return validationError(parsed.errors);
  }

  const { images = [], ...fields } = parsed.fields;
  const experiences = getState().experiences;
  const id = nextId(experiences);
  const now = nowIso();
  const experience: DashboardExperience = {
    id,
    producerId: PRODUCER_ID,
    title: '',
    prefectureId: 1,
    description: '',
    place: '',
    priceAdult: 0,
    priceChild: null,
    ageCondition: null,
    familyOk: false,
    beginnerOk: false,
    flow: null,
    belongings: null,
    notes: null,
    cancelPolicy: '',
    publishStatus: 'draft',
    ...fields,
    images: toImages(
      images.map((image) => image.imageKey),
      [],
    ),
    createdAt: now,
    updatedAt: now,
  };

  experiences.push(experience);
  getState().etags[id] = nextEtag('experience', id);
  remember(init, id);
  save();

  return { status: 201, body: writeResult(experience), headers: etagHeader(experience) };
}

// PATCH /api/v1/dashboard/experiences/:experienceId（送った項目だけ更新。images は送った内容で置き換え）
function updateExperience(url: URL, init?: RequestInit): MockResult {
  const experience = findExperience(idFromPath(url));

  if (experience === undefined) {
    return notFound(EXPERIENCE_NOT_FOUND);
  }

  if (isStale(init, etagOf(experience))) {
    return preconditionFailed();
  }

  if (experience.publishStatus === 'suspended') {
    return conflict('CONFLICT', '掲載停止中の体験は変更できません。');
  }

  const parsed = parseFields<ExperienceFields>(readJsonBody(init), experienceChecks, []);

  if (!parsed.ok) {
    return validationError(parsed.errors);
  }

  const { images, ...fields } = parsed.fields;
  const hasActiveReservations = applicationsOf({ experienceId: experience.id }).some(isActive);

  // 予約がある体験は、参加者に案内済みの内容（タイトル・説明・開催地・料金）を変えられない
  // （フォームは全項目を送るため、値が変わった場合だけ 409 にする）
  if (
    hasActiveReservations &&
    LOCKED_FIELDS.some((name) => name in fields && fields[name] !== experience[name])
  ) {
    return conflict('ACTIVE_RESERVATIONS_EXIST', '予約があるため、この項目は変更できません。');
  }

  Object.assign(experience, fields);

  if (images !== undefined) {
    experience.images = toImages(
      images.map((image) => image.imageKey),
      experience.images,
    );
  }

  touchExperience(experience, nowIso());
  save();

  return { status: 200, body: writeResult(experience), headers: etagHeader(experience) };
}

// DELETE /api/v1/dashboard/experiences/:experienceId（申込中・確定の予約が残っていると削除できない）
function deleteExperience(url: URL, init?: RequestInit): MockResult {
  const experience = findExperience(idFromPath(url));

  if (experience === undefined) {
    return notFound(EXPERIENCE_NOT_FOUND);
  }

  if (isStale(init, etagOf(experience))) {
    return preconditionFailed();
  }

  if (applicationsOf({ experienceId: experience.id }).some(isActive)) {
    return conflict('ACTIVE_RESERVATIONS_EXIST', '予約が残っているため削除できません。');
  }

  const current = getState();
  current.experiences = current.experiences.filter((item) => item.id !== experience.id);
  current.slots = current.slots.filter((slot) => slot.experienceId !== experience.id);
  current.applications = current.applications.filter(
    (application) => application.experienceId !== experience.id,
  );
  delete current.etags[experience.id];
  save();

  return { status: 204 };
}

// ---------------------------------------------------------------------------
// 予約枠
// ---------------------------------------------------------------------------

const SLOT_STATUSES: string[] = ['open', 'closed', 'canceled'];

const slotChecks: Record<string, (value: unknown) => boolean> = {
  startAt: (value) => typeof value === 'string' && !Number.isNaN(Date.parse(value)),
  durationMin: (value) =>
    Number.isInteger(value) && Number(value) >= 1 && Number(value) <= 24 * 60,
  capacity: (value) => Number.isInteger(value) && Number(value) >= 1 && Number(value) <= 10000,
  status: (value) => typeof value === 'string' && SLOT_STATUSES.includes(value),
};

type SlotFields = {
  startAt?: string;
  durationMin?: number;
  capacity?: number;
  status?: ExperienceSlotStatus;
};

// 同じ体験に、同じ開始日時の枠（削除済みを除く）があるか
function hasSameStart(experienceId: number, startAt: string, exceptSlotId?: number): boolean {
  const time = Date.parse(startAt);

  return liveSlotsOf(experienceId).some(
    (slot) => slot.id !== exceptSlotId && Date.parse(slot.startAt) === time,
  );
}

// /experiences/:experienceId/slots/:slotId の体験と枠
function findSlot(url: URL): { experience?: DashboardExperience; slot?: StoredSlot } {
  const experience = findExperience(idFromPath(url, 2));
  const slotId = idFromPath(url);
  const slot =
    experience === undefined
      ? undefined
      : liveSlotsOf(experience.id).find((item) => item.id === slotId);

  return { experience, slot };
}

// GET /api/v1/dashboard/experiences/:experienceId/slots（開始日時の早い順）
function listSlots(url: URL): MockResult {
  const experience = findExperience(idFromPath(url, 1));

  if (experience === undefined) {
    return notFound(EXPERIENCE_NOT_FOUND);
  }

  const items = liveSlotsOf(experience.id)
    .sort((a, b) => Date.parse(a.startAt) - Date.parse(b.startAt) || a.id - b.id)
    .map(toSlot);
  const page = paginate(items, url);

  return page === null
    ? validationError({ page: ['正しい値を指定してください。'] })
    : { status: 200, body: page };
}

// POST /api/v1/dashboard/experiences/:experienceId/slots
function createSlot(url: URL, init?: RequestInit): MockResult {
  const experience = findExperience(idFromPath(url, 1));

  if (experience === undefined) {
    return notFound(EXPERIENCE_NOT_FOUND);
  }

  const replay = replayed(init);

  if (typeof replay === 'number') {
    const created = getState().slots.find((item) => item.id === replay);

    if (created !== undefined) {
      return { status: 201, body: toSlot(created) };
    }
  } else if (replay !== null) {
    return replay;
  }

  const parsed = parseFields<Required<SlotFields>>(readJsonBody(init), slotChecks, [
    'startAt',
    'durationMin',
    'capacity',
    'status',
  ]);

  if (!parsed.ok) {
    return validationError(parsed.errors);
  }

  const fields = parsed.fields;

  if (fields.status === 'canceled') {
    return validationError({ status: ['指定できない値です。'] });
  }

  if (Date.parse(fields.startAt) <= Date.now()) {
    return validationError({ startAt: ['現在より後の日時を指定してください。'] });
  }

  if (hasSameStart(experience.id, fields.startAt)) {
    return conflict('DUPLICATE_SLOT', '同じ開始日時の予約枠がすでにあります。');
  }

  const id = nextId(getState().slots);
  const now = nowIso();
  const slot: StoredSlot = {
    id,
    experienceId: experience.id,
    ...fields,
    etag: nextEtag('slot', id),
    createdAt: now,
    updatedAt: now,
    deleted: false,
  };

  getState().slots.push(slot);
  touchExperience(experience, now);
  remember(init, id);
  save();

  return { status: 201, body: toSlot(slot) };
}

// PATCH /api/v1/dashboard/experiences/:experienceId/slots/:slotId（送った項目だけ更新）
function updateSlot(url: URL, init?: RequestInit): MockResult {
  const { experience, slot } = findSlot(url);

  if (experience === undefined || slot === undefined) {
    return notFound(SLOT_NOT_FOUND);
  }

  if (isStale(init, slot.etag)) {
    return preconditionFailed();
  }

  const parsed = parseFields<SlotFields>(readJsonBody(init), slotChecks, []);

  if (!parsed.ok) {
    return validationError(parsed.errors);
  }

  const fields = parsed.fields;
  const changesStart =
    fields.startAt !== undefined && Date.parse(fields.startAt) !== Date.parse(slot.startAt);
  const changesTime =
    changesStart || (fields.durationMin !== undefined && fields.durationMin !== slot.durationMin);

  // 申込履歴（キャンセル済みを含む）がある枠は、日時・所要時間を変えられない
  if (changesTime && applicationsOf({ slotId: slot.id }).length > 0) {
    return conflict('HAS_RESERVATION_HISTORY', '予約がある枠の日時は変更できません。');
  }

  if (changesStart && fields.startAt !== undefined) {
    if (Date.parse(fields.startAt) <= Date.now()) {
      return validationError({ startAt: ['現在より後の日時を指定してください。'] });
    }

    if (hasSameStart(experience.id, fields.startAt, slot.id)) {
      return conflict('DUPLICATE_SLOT', '同じ開始日時の予約枠がすでにあります。');
    }
  }

  if (fields.capacity !== undefined && fields.capacity < toSlot(slot).reservedCount) {
    return conflict('CAPACITY_CONFLICT', '定員は予約人数以上にしてください。');
  }

  const now = nowIso();
  Object.assign(slot, fields, { updatedAt: now, etag: nextEtag('slot', slot.id, slot.etag) });
  touchExperience(experience, now);
  save();

  return { status: 200, body: toSlot(slot) };
}

// DELETE /api/v1/dashboard/experiences/:experienceId/slots/:slotId（申込中・確定の予約がある枠は削除できない）
function deleteSlot(url: URL, init?: RequestInit): MockResult {
  const { experience, slot } = findSlot(url);

  if (experience === undefined || slot === undefined) {
    return notFound(SLOT_NOT_FOUND);
  }

  if (isStale(init, slot.etag)) {
    return preconditionFailed();
  }

  const applications = applicationsOf({ slotId: slot.id });

  if (applications.some(isActive)) {
    return conflict('ACTIVE_RESERVATIONS_EXIST', '予約が残っているため削除できません。');
  }

  const current = getState();

  // キャンセル済みの申込がある枠は、申込者一覧に表示するため削除済みとして残す
  if (applications.length > 0) {
    slot.deleted = true;
  } else {
    current.slots = current.slots.filter((item) => item.id !== slot.id);
  }

  touchExperience(experience, nowIso());
  save();

  return { status: 204 };
}

// ---------------------------------------------------------------------------
// 申込者
// ---------------------------------------------------------------------------

const APPLICATION_STATUSES = ['applied', 'confirmed', 'canceled', 'attended'];

// GET /api/v1/dashboard/experiences/:experienceId/applications?slotId=&status=&page=（申込の新しい順）
function listApplications(url: URL): MockResult {
  const experience = findExperience(idFromPath(url, 1));

  if (experience === undefined) {
    return notFound(EXPERIENCE_NOT_FOUND);
  }

  const slotParam = url.searchParams.get('slotId');
  const status = url.searchParams.get('status');

  if (slotParam !== null && !/^[1-9][0-9]*$/.test(slotParam)) {
    return validationError({ slotId: ['正しい値を指定してください。'] });
  }

  if (status !== null && !APPLICATION_STATUSES.includes(status)) {
    return validationError({ status: ['指定できない値です。'] });
  }

  const slots = getState().slots;
  const items = applicationsOf({
    experienceId: experience.id,
    slotId: slotParam === null ? undefined : Number(slotParam),
  })
    .filter((application) => status === null || application.status === status)
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt) || b.id - a.id)
    .flatMap((application): ExperienceApplication[] => {
      const slot = slots.find((item) => item.id === application.slotId);

      if (slot === undefined) {
        return [];
      }

      const { experienceId: _experienceId, slotId: _slotId, ...fields } = application;

      return [
        {
          ...fields,
          slot: {
            id: slot.id,
            startAt: slot.startAt,
            durationMin: slot.durationMin,
            status: slot.status,
          },
        },
      ];
    });
  const page = paginate(items, url);

  return page === null
    ? validationError({ page: ['正しい値を指定してください。'] })
    : { status: 200, body: page };
}

export {
  createExperience,
  createSlot,
  deleteExperience,
  deleteSlot,
  getExperience,
  listApplications,
  listExperiences,
  listSlots,
  updateExperience,
  updateSlot,
};
