// 生産者管理画面の体験（/api/v1/dashboard/experiences 以下）の型

type ExperiencePublishStatus = 'draft' | 'public' | 'private' | 'suspended';

// 登録・更新で指定できる公開状態（掲載停止は運営のみ）
type ExperienceWritableStatus = Exclude<ExperiencePublishStatus, 'suspended'>;

// 体験一覧の1件
type DashboardExperienceSummary = {
  id: number;
  title: string;
  publishStatus: ExperiencePublishStatus;
  prefectureId: number;
  priceAdult: number;
  // null は子ども料金なし（子どもは申し込めない）
  priceChild: number | null;
  // 削除されていない予約枠の数
  slotCount: number;
  // 全状態（キャンセル含む）の予約件数
  applicationCount: number;
  // これから開催する受付中の枠の最も早い開始日時。なければ null
  nextStartAt: string | null;
  createdAt: string;
  updatedAt: string;
};

type DashboardExperienceList = {
  items: DashboardExperienceSummary[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

type ExperienceImage = {
  id: number;
  imageKey: string;
  url: string;
  sortOrder: number;
};

// 体験詳細（編集画面用）
type DashboardExperience = {
  id: number;
  producerId: number;
  title: string;
  prefectureId: number;
  description: string;
  place: string;
  priceAdult: number;
  priceChild: number | null;
  ageCondition: string | null;
  // false の場合、子ども・未就学児は申し込めない
  familyOk: boolean;
  beginnerOk: boolean;
  flow: string[] | null;
  belongings: string[] | null;
  notes: string[] | null;
  cancelPolicy: string;
  publishStatus: ExperiencePublishStatus;
  images: ExperienceImage[];
  createdAt: string;
  updatedAt: string;
};

// 体験登録API（POST）のリクエスト。全項目必須（任意の情報は null）
type ExperienceInput = {
  title: string;
  prefectureId: number;
  description: string;
  place: string;
  priceAdult: number;
  priceChild: number | null;
  ageCondition: string | null;
  familyOk: boolean;
  beginnerOk: boolean;
  flow: string[] | null;
  belongings: string[] | null;
  notes: string[] | null;
  cancelPolicy: string;
  publishStatus: ExperienceWritableStatus;
  // 画像アップロードAPIで受け取ったキー（最大20件、先頭がメイン画像）
  images: { imageKey: string }[];
};

// 体験の登録・更新APIのレスポンス（詳細全体ではない）
type ExperienceWriteResult = {
  id: number;
  producerId: number;
  publishStatus: ExperiencePublishStatus;
  createdAt: string;
  updatedAt: string;
};

// 予約枠の状態（canceled は中止。他の状態には戻せない）
type ExperienceSlotStatus = 'open' | 'closed' | 'canceled';

type ExperienceSlot = {
  id: number;
  experienceId: number;
  // タイムゾーン付きの日時（例: 2026-11-15T10:00:00+09:00）
  startAt: string;
  durationMin: number;
  capacity: number;
  status: ExperienceSlotStatus;
  // 申込中・確定・参加済みの人数（大人＋子ども＋未就学児）
  reservedCount: number;
  remainingCapacity: number;
  // 予約枠ごとの ETag。更新・削除の If-Match に渡す（体験の ETag とは別）
  etag: string;
  createdAt: string;
  updatedAt: string;
};

type ExperienceSlotList = {
  items: ExperienceSlot[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

// 予約枠登録API（POST）のリクエスト
type ExperienceSlotInput = {
  startAt: string;
  durationMin: number;
  capacity: number;
  status: Exclude<ExperienceSlotStatus, 'canceled'>;
};

// 予約枠更新API（PATCH）のリクエスト（送った項目だけ更新）
type ExperienceSlotUpdateInput = Partial<{
  startAt: string;
  durationMin: number;
  capacity: number;
  status: ExperienceSlotStatus;
}>;

type ExperienceApplicationStatus =
  | 'applied'
  | 'confirmed'
  | 'canceled'
  | 'attended';

// 体験の予約（申込者一覧の1件）。退会済み会員は氏名・連絡先が null
type ExperienceApplication = {
  id: number;
  reservationNo: string;
  slot: {
    id: number;
    startAt: string;
    durationMin: number;
    status: ExperienceSlotStatus;
  };
  user: {
    id: number;
    lastName: string | null;
    firstName: string | null;
    isActive: boolean;
  };
  adultCount: number;
  childCount: number;
  infantCount: number;
  representativeName: string | null;
  phone: string | null;
  message: string | null;
  totalAmount: number;
  status: ExperienceApplicationStatus;
  policyAgreedAt: string;
  createdAt: string;
};

type ExperienceApplicationList = {
  items: ExperienceApplication[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type {
  DashboardExperience,
  DashboardExperienceList,
  DashboardExperienceSummary,
  ExperienceApplication,
  ExperienceApplicationList,
  ExperienceApplicationStatus,
  ExperienceImage,
  ExperienceInput,
  ExperiencePublishStatus,
  ExperienceSlot,
  ExperienceSlotInput,
  ExperienceSlotList,
  ExperienceSlotStatus,
  ExperienceSlotUpdateInput,
  ExperienceWritableStatus,
  ExperienceWriteResult,
};
