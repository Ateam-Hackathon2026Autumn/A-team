import { useEffect, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from 'react';
import { Link } from 'react-router';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import { getDashboardProfile, updateDashboardProfile } from '../../api/dashboardProfileApi';
import { uploadImage } from '../../api/uploadApi';
import DashboardButton from '../../components/DashboardButton';
import {
  CheckboxField,
  Field,
  FormSection,
  PublishStatusField,
  controlBorder,
  controlClassName,
  describedBy,
  type PublishStatusOption,
} from '../../components/DashboardFormParts';
import { userInfoAtom } from '../../stores/userAtom';
import type {
  DashboardProfile,
  ProducerGenre,
  ProfileStoryStatus,
  ProfileUpdateInput,
} from '../../types/dashboardProfile';
import { PREFECTURES, prefectureName } from '../../utils/prefectures';

// 生産者プロフィールの編集（生産者ページに載る内容）
// 実API: GET・PATCH /api/v1/dashboard/profile（backend/api/views/dashboard/profile.py）
// 画面の流れ: Notion「生産者ダッシュボード・プロフィール編集」
//   取得 → 入力（画像はアップロードしてプレビュー）→ 入力チェック → 保存 → 完了表示／400 は項目ごとに表示
// レイアウト: 参考HTML（生産者管理のプロフィール編集。編集とプレビューを並べ、狭い画面では切り替え）

const MAX_GALLERY = 10;
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const IMAGE_TYPES = ['image/jpeg', 'image/png'];
// 新規就業バッジ（この仕事を始めた年が今年から5年以内）。実API: services/badges.py
const NEW_FARMER_YEARS = 5;

const GENRE_LABELS: Record<ProducerGenre, string> = {
  agriculture: '農業',
  livestock: '畜産',
  fishery: '漁業',
};

const NEW_FARMER_LABELS: Record<ProducerGenre, string> = {
  agriculture: '新規就農',
  livestock: '新規就業',
  fishery: '新規就漁',
};

const STORY_STATUS_LABELS: Record<ProfileStoryStatus, string> = {
  draft: '下書き',
  public: '公開中',
  private: '非公開',
  suspended: '掲載停止中',
};

type EditableStatus = 'public' | 'private';

const STATUS_OPTIONS: PublishStatusOption<EditableStatus>[] = [
  { value: 'public', label: '公開', description: 'お客さまが生産者ページを見られます。' },
  {
    value: 'private',
    label: '非公開',
    description: '生産者ページを表示しません。商品・体験・求人も表示されなくなります。',
  },
];

// ---------------------------------------------------------------------------
// フォームの値
// ---------------------------------------------------------------------------

type FormValues = {
  prefectureId: string;
  city: string;
  productionItems: string;
  intro: string;
  careerStartYear: string;
  foundedYear: string;
  acceptsExperience: boolean;
  recruiting: boolean;
  // 掲載停止中など、生産者が選べない状態のときは null（送らない）
  publishStatus: EditableStatus | null;
};

type FieldName =
  | 'prefectureId'
  | 'city'
  | 'productionItems'
  | 'intro'
  | 'careerStartYear'
  | 'foundedYear'
  | 'profileImage'
  | 'coverImage'
  | 'images'
  | 'publishStatus';

type FormErrors = Partial<Record<FieldName, string>>;

// 画像1枚分（プロフィール画像・カバー画像・農園画像で共通）
type ImageItem = {
  localId: number;
  key: string | null;
  previewUrl: string;
  status: 'done' | 'uploading' | 'error';
};

function toFormValues(profile: DashboardProfile): FormValues {
  return {
    prefectureId: String(profile.prefectureId),
    city: profile.city,
    productionItems: profile.productionItems,
    intro: profile.intro,
    careerStartYear: profile.careerStartYear === null ? '' : String(profile.careerStartYear),
    foundedYear: profile.foundedYear === null ? '' : String(profile.foundedYear),
    acceptsExperience: profile.acceptsExperience,
    recruiting: profile.recruiting,
    publishStatus:
      profile.publishStatus === 'public' || profile.publishStatus === 'private'
        ? profile.publishStatus
        : null,
  };
}

let nextLocalId = 1;

function singleImage(key: string | null, url: string | null): ImageItem | null {
  return key === null || url === null
    ? null
    : { localId: nextLocalId++, key, previewUrl: url, status: 'done' };
}

function toGallery(profile: DashboardProfile): ImageItem[] {
  return [...profile.images]
    .sort((a, b) => a.sortOrder - b.sortOrder)
    .map((image) => ({ localId: nextLocalId++, key: image.key, previewUrl: image.url, status: 'done' }));
}

function releasePreview(item: ImageItem | null) {
  if (item !== null && item.previewUrl.startsWith('blob:')) {
    URL.revokeObjectURL(item.previewUrl);
  }
}

const yearValue = (value: string) => (value.trim() === '' ? null : Number(value.trim()));

// 元のプロフィールから変わった項目だけを送る（PATCH）
function buildPatch(
  profile: DashboardProfile,
  values: FormValues,
  profileImage: ImageItem | null,
  coverImage: ImageItem | null,
  gallery: ImageItem[],
): ProfileUpdateInput {
  const patch: ProfileUpdateInput = {};

  if (Number(values.prefectureId) !== profile.prefectureId) patch.prefectureId = Number(values.prefectureId);
  if (values.city.trim() !== profile.city) patch.city = values.city.trim();
  if (values.productionItems.trim() !== profile.productionItems) {
    patch.productionItems = values.productionItems.trim();
  }
  if (values.intro.trim() !== profile.intro) patch.intro = values.intro.trim();
  if (yearValue(values.careerStartYear) !== profile.careerStartYear) {
    patch.careerStartYear = yearValue(values.careerStartYear);
  }
  if (yearValue(values.foundedYear) !== profile.foundedYear) patch.foundedYear = yearValue(values.foundedYear);
  if (values.acceptsExperience !== profile.acceptsExperience) patch.acceptsExperience = values.acceptsExperience;
  if (values.recruiting !== profile.recruiting) patch.recruiting = values.recruiting;

  const profileKey = profileImage?.key ?? null;
  if (profileKey !== profile.profileImage) patch.profileImage = profileKey;

  const coverKey = coverImage?.key ?? null;
  if (coverKey !== profile.coverImage) patch.coverImage = coverKey;

  const galleryKeys = gallery.flatMap(({ key }) => (key === null ? [] : [key]));
  const savedKeys = [...profile.images].sort((a, b) => a.sortOrder - b.sortOrder).map(({ key }) => key);
  if (JSON.stringify(galleryKeys) !== JSON.stringify(savedKeys)) patch.imageKeys = galleryKeys;

  if (values.publishStatus !== null && values.publishStatus !== profile.publishStatus) {
    patch.publishStatus = values.publishStatus;
  }

  return patch;
}

function yearError(value: string, label: string): string | undefined {
  const text = value.trim();

  if (text === '') return undefined;
  if (!/^\d{1,4}$/.test(text) || Number(text) < 1) return `${label}は西暦4桁の数字で入力してください。`;
  if (Number(text) > new Date().getFullYear()) return `${label}は今年以前の年を入力してください。`;
  return undefined;
}

function validate(values: FormValues): FormErrors {
  const errors: FormErrors = {};

  if (values.prefectureId === '') errors.prefectureId = '都道府県を選んでください。';
  if (values.city.trim() === '') errors.city = '市区町村を入力してください。';
  else if (values.city.trim().length > 50) errors.city = '市区町村は50文字以内で入力してください。';
  if (values.productionItems.trim() === '') errors.productionItems = '生産品目を入力してください。';
  else if (values.productionItems.trim().length > 100) {
    errors.productionItems = '生産品目は100文字以内で入力してください。';
  }
  if (values.intro.trim() === '') errors.intro = 'ひとこと紹介を入力してください。';

  const career = yearError(values.careerStartYear, 'この仕事を始めた年');
  if (career !== undefined) errors.careerStartYear = career;

  const founded = yearError(values.foundedYear, '創業年');
  if (founded !== undefined) errors.foundedYear = founded;

  return errors;
}

// 400 の details のキー（API の項目名）を入力欄に対応させる
const API_FIELD_TO_FORM: Record<string, FieldName> = {
  prefectureId: 'prefectureId',
  city: 'city',
  productionItems: 'productionItems',
  intro: 'intro',
  careerStartYear: 'careerStartYear',
  foundedYear: 'foundedYear',
  profileImage: 'profileImage',
  coverImage: 'coverImage',
  imageKeys: 'images',
  publishStatus: 'publishStatus',
};

function errorsFromDetails(details: Record<string, string[]>): FormErrors {
  const errors: FormErrors = {};

  Object.entries(details).forEach(([key, messages]) => {
    const field = API_FIELD_TO_FORM[key];

    if (field !== undefined && messages[0] !== undefined) {
      errors[field] = messages[0];
    }
  });

  return errors;
}

// JPEG・PNG・5MB 以下だけ受け付ける。だめならメッセージ
function fileError(file: File): string | null {
  if (!IMAGE_TYPES.includes(file.type)) return 'JPEG または PNG の画像を選んでください。';
  if (file.size > MAX_IMAGE_BYTES) return '画像は5MB以下にしてください。';
  return null;
}

function newFarmerBadge(profile: DashboardProfile, careerStartYear: string): string | null {
  const year = yearValue(careerStartYear);
  const thisYear = new Date().getFullYear();

  if (year === null || Number.isNaN(year) || year > thisYear || year < thisYear - NEW_FARMER_YEARS) {
    return null;
  }

  return `${NEW_FARMER_LABELS[profile.genre]} ${thisYear - year + 1}年目`;
}

function dateTimeLabel(value: string): string {
  return new Date(value).toLocaleString('ja-JP', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ---------------------------------------------------------------------------
// 部品
// ---------------------------------------------------------------------------

function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
      {children}
    </div>
  );
}

function ReadOnlyItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-bold text-marche-muted">{label}</dt>
      <dd className="m-0 mt-0.5 font-bold">{value}</dd>
    </div>
  );
}

function ImageStatusLabel({ item }: { item: ImageItem }) {
  if (item.status === 'done') {
    return null;
  }

  return (
    <span className="absolute inset-x-1.5 bottom-1.5 rounded-lg bg-white/90 px-1 py-0.5 text-center text-xs font-bold">
      {item.status === 'uploading' ? 'アップロード中…' : <span className="text-marche-red">失敗しました</span>}
    </span>
  );
}

// プロフィール画像・カバー画像（1枚）
function SingleImageField({
  id,
  label,
  hint,
  item,
  error,
  shape,
  onSelect,
  onRemove,
}: {
  id: string;
  label: string;
  hint: string;
  item: ImageItem | null;
  error: string | undefined;
  shape: 'round' | 'wide';
  onSelect: (file: File) => void;
  onRemove: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';

    if (file !== undefined) {
      onSelect(file);
    }
  };

  return (
    <Field id={id} label={label} hint={hint} error={error}>
      <div className="flex flex-wrap items-center gap-4">
        <div
          className={`relative shrink-0 overflow-hidden bg-marche-sage ${shape === 'round' ? 'size-24 rounded-full' : 'aspect-[2/1] w-full max-w-72 rounded-xl'}`}
        >
          {item !== null ? (
            <>
              <img
                src={item.previewUrl}
                alt={`${label}のプレビュー`}
                className={`block size-full object-cover ${item.status === 'done' ? '' : 'opacity-50'}`}
              />
              <ImageStatusLabel item={item} />
            </>
          ) : (
            <span className="grid size-full place-items-center text-xs text-marche-muted">未設定</span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            ref={inputRef}
            id={id}
            type="file"
            accept="image/jpeg,image/png"
            onChange={handleChange}
            aria-describedby={describedBy(id, true, error)}
            className="sr-only"
          />
          <DashboardButton
            variant="secondary"
            size="sm"
            disabled={item?.status === 'uploading'}
            onClick={() => inputRef.current?.click()}
            className="min-h-11"
          >
            {item === null ? '画像を選ぶ' : '変更する'}
          </DashboardButton>
          {item !== null && (
            <DashboardButton
              variant="danger"
              size="sm"
              disabled={item.status === 'uploading'}
              onClick={onRemove}
              className="min-h-11"
            >
              外す
            </DashboardButton>
          )}
        </div>
      </div>
    </Field>
  );
}

// 農園画像（10枚まで。並び順が表示順）
function GalleryField({
  items,
  error,
  onAdd,
  onRemove,
  onMove,
}: {
  items: ImageItem[];
  error: string | undefined;
  onAdd: (files: File[]) => void;
  onRemove: (item: ImageItem) => void;
  onMove: (index: number, offset: -1 | 1) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const id = 'profile-images';

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = [...(event.target.files ?? [])];
    event.target.value = '';
    onAdd(files);
  };

  return (
    <Field
      id={id}
      label="農園の写真"
      hint={`${MAX_GALLERY}枚まで。生産者ページに並ぶ順番で表示されます（JPEG・PNG、1枚5MBまで）。`}
      error={error}
    >
      <ul className="m-0 grid list-none grid-cols-2 gap-3 p-0 sm:grid-cols-4">
        {items.map((item, index) => (
          <li key={item.localId} className="relative">
            <img
              src={item.previewUrl}
              alt={`農園の写真${index + 1}`}
              className={`block aspect-[4/3] w-full rounded-xl bg-marche-sage object-cover ${item.status === 'done' ? '' : 'opacity-50'}`}
            />
            <ImageStatusLabel item={item} />
            <button
              type="button"
              aria-label={`農園の写真${index + 1}を削除`}
              disabled={item.status === 'uploading'}
              onClick={() => onRemove(item)}
              className="absolute top-1.5 right-1.5 box-border grid size-8 cursor-pointer place-items-center rounded-full border-0 bg-white/90 p-0 text-sm font-bold text-marche-ink [font-family:inherit] disabled:cursor-not-allowed disabled:opacity-50"
            >
              ×
            </button>
            <div className="mt-1 flex justify-center gap-1">
              <button
                type="button"
                aria-label={`農園の写真${index + 1}を前へ`}
                disabled={index === 0}
                onClick={() => onMove(index, -1)}
                className="box-border min-h-9 min-w-11 cursor-pointer rounded-full border border-solid border-marche-line bg-white text-sm [font-family:inherit] disabled:cursor-not-allowed disabled:opacity-40"
              >
                ←
              </button>
              <button
                type="button"
                aria-label={`農園の写真${index + 1}を後ろへ`}
                disabled={index === items.length - 1}
                onClick={() => onMove(index, 1)}
                className="box-border min-h-9 min-w-11 cursor-pointer rounded-full border border-solid border-marche-line bg-white text-sm [font-family:inherit] disabled:cursor-not-allowed disabled:opacity-40"
              >
                →
              </button>
            </div>
          </li>
        ))}
        {items.length < MAX_GALLERY && (
          <li>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="box-border grid aspect-[4/3] w-full cursor-pointer place-items-center rounded-xl border-2 border-dashed border-marche-green/50 bg-white text-sm font-bold text-marche-green [font-family:inherit] hover:bg-marche-canvas"
            >
              ＋ 写真を追加
            </button>
          </li>
        )}
      </ul>
      <input
        ref={inputRef}
        id={id}
        type="file"
        multiple
        accept="image/jpeg,image/png"
        onChange={handleChange}
        aria-describedby={describedBy(id, true, error)}
        className="sr-only"
      />
      <p className="m-0 mt-1 text-right text-xs text-marche-muted">
        {items.length} / {MAX_GALLERY}枚
      </p>
    </Field>
  );
}

function ProfilePreview({
  profile,
  values,
  profileImage,
  coverImage,
  gallery,
}: {
  profile: DashboardProfile;
  values: FormValues;
  profileImage: ImageItem | null;
  coverImage: ImageItem | null;
  gallery: ImageItem[];
}) {
  const badges = [
    newFarmerBadge(profile, values.careerStartYear),
    values.acceptsExperience ? '体験受け入れ中' : null,
    values.recruiting ? '担い手募集中' : null,
  ].filter((badge): badge is string => badge !== null);
  const place = `${prefectureName(Number(values.prefectureId))} ${values.city.trim()}`.trim();
  const showStory = profile.storyPublishStatus === 'public';
  const founded = yearValue(values.foundedYear);

  return (
    <section
      aria-label="プレビュー"
      className="box-border overflow-hidden rounded-2xl border border-solid border-marche-line bg-marche-ivory xl:sticky xl:top-6"
    >
      <p className="m-0 bg-marche-ink px-4 py-2 text-xs font-bold text-white">
        プレビュー（お客さまに見える画面）
      </p>
      <div className="aspect-[2/1] bg-marche-sage">
        {coverImage !== null && (
          <img src={coverImage.previewUrl} alt="" className="block size-full object-cover" />
        )}
      </div>
      <div className="px-5 pb-5">
        <div className="relative -mt-9 size-18 overflow-hidden rounded-full border-3 border-solid border-marche-ivory bg-marche-sage">
          {profileImage !== null && (
            <img src={profileImage.previewUrl} alt="" className="block size-full object-cover" />
          )}
        </div>
        {badges.length > 0 && (
          <ul className="m-0 mt-2 flex list-none flex-wrap gap-1.5 p-0">
            {badges.map((badge) => (
              <li
                key={badge}
                className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${badge.startsWith('新規') ? 'bg-marche-orange/25 text-marche-ink' : 'bg-marche-sage text-marche-green'}`}
              >
                {badge}
              </li>
            ))}
          </ul>
        )}
        <p className="m-0 mt-2 font-serif text-xl font-bold">{profile.businessName}</p>
        <p className="m-0 text-xs text-marche-muted">
          {profile.representativeName}
          {place !== '' && ` ・ ${place}`}
          {founded !== null && !Number.isNaN(founded) && ` ・ 創業 ${founded}年`}
        </p>
        {values.productionItems.trim() !== '' && (
          <p className="m-0 mt-1 text-xs font-bold text-marche-green">{values.productionItems.trim()}</p>
        )}
        <p className="m-0 mt-3 text-sm leading-loose whitespace-pre-wrap [overflow-wrap:anywhere]">
          {values.intro.trim() === '' ? (
            <span className="text-marche-muted">（ひとこと紹介が入ります）</span>
          ) : (
            values.intro.trim()
          )}
        </p>
        {showStory &&
          (
            [
              ['この仕事を始めた理由', profile.reason],
              ['これからの目標', profile.goal],
            ] as const
          ).map(([label, text]) =>
            text === null || text === '' ? null : (
              <div
                key={label}
                className="mt-3 rounded-xl border border-solid border-marche-line bg-white px-3.5 py-3"
              >
                <p className="m-0 text-xs font-bold text-marche-green">{label}</p>
                <p className="m-0 mt-1 text-sm leading-relaxed [overflow-wrap:anywhere]">{text}</p>
              </div>
            ),
          )}
        {gallery.length > 0 && (
          <ul className="m-0 mt-4 grid list-none grid-cols-3 gap-1.5 p-0">
            {gallery.slice(0, 6).map((item) => (
              <li key={item.localId}>
                <img src={item.previewUrl} alt="" className="block aspect-square w-full rounded-lg object-cover" />
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 画面
// ---------------------------------------------------------------------------

function DashboardProfileEditPage() {
  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、プロフィールのAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const [profile, setProfile] = useState<DashboardProfile | null>(null);
  const [values, setValues] = useState<FormValues | null>(null);
  const [profileImage, setProfileImage] = useState<ImageItem | null>(null);
  const [coverImage, setCoverImage] = useState<ImageItem | null>(null);
  const [gallery, setGallery] = useState<ImageItem[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [reloadCount, setReloadCount] = useState(0);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [mobileView, setMobileView] = useState<'edit' | 'preview'>('edit');
  const errorSummaryRef = useRef<HTMLDivElement>(null);
  // 最新の入力。保存の応答を待つ間に変わった項目を見分けるために使う
  const latestRef = useRef({ values, profileImage, coverImage, gallery });

  useEffect(() => {
    latestRef.current = { values, profileImage, coverImage, gallery };
  });

  const resetForm = (next: DashboardProfile) => {
    setProfile(next);
    setValues(toFormValues(next));
    setProfileImage(singleImage(next.profileImage, next.profileImageUrl));
    setCoverImage(singleImage(next.coverImage, next.coverImageUrl));
    setGallery(toGallery(next));
    setErrors({});
  };

  useEffect(() => {
    if (!canManage) {
      return;
    }

    const controller = new AbortController();

    getDashboardProfile(controller.signal)
      .then((result) => {
        setProfile(result);
        setValues(toFormValues(result));
        setProfileImage(singleImage(result.profileImage, result.profileImageUrl));
        setCoverImage(singleImage(result.coverImage, result.coverImageUrl));
        setGallery(toGallery(result));
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        if (error instanceof ApiError && error.status === 401) {
          window.location.replace('/signin');
          return;
        }

        setLoadError(true);
      });

    return () => controller.abort();
  }, [canManage, reloadCount]);

  useEffect(() => {
    if (toast === null) {
      return;
    }

    const timer = window.setTimeout(() => setToast(null), 3000);

    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (submitError !== null) {
      errorSummaryRef.current?.focus();
    }
  }, [submitError]);

  const isUploading = [profileImage, coverImage, ...gallery].some((item) => item?.status === 'uploading');
  const patch =
    profile !== null && values !== null
      ? buildPatch(profile, values, profileImage, coverImage, gallery)
      : {};
  const isDirty = Object.keys(patch).length > 0 || isUploading;

  // 保存していない変更があるときは、タブを閉じる前に確認する
  useEffect(() => {
    if (!isDirty) {
      return;
    }

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  const clearError = (field: FieldName) => {
    setErrors((current) => {
      if (current[field] === undefined) {
        return current;
      }

      const next = { ...current };
      delete next[field];

      return next;
    });
  };

  const updateValue = <K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    setValues((current) => (current === null ? current : { ...current, [key]: value }));

    if (key !== 'acceptsExperience' && key !== 'recruiting') {
      clearError(key as FieldName);
    }
  };

  // プロフィール画像・カバー画像を選んだら、すぐアップロードする
  const selectSingle = (
    field: 'profileImage' | 'coverImage',
    setItem: (update: (current: ImageItem | null) => ImageItem | null) => void,
    file: File,
  ) => {
    const message = fileError(file);

    if (message !== null) {
      setErrors((current) => ({ ...current, [field]: message }));
      return;
    }

    clearError(field);
    const item: ImageItem = {
      localId: nextLocalId++,
      key: null,
      previewUrl: URL.createObjectURL(file),
      status: 'uploading',
    };

    setItem((current) => {
      releasePreview(current);
      return item;
    });

    uploadImage(file)
      .then(({ key }) =>
        setItem((current) =>
          current?.localId === item.localId ? { ...current, key, status: 'done' } : current,
        ),
      )
      .catch(() =>
        setItem((current) =>
          current?.localId === item.localId ? { ...current, status: 'error' } : current,
        ),
      );
  };

  const removeSingle = (
    field: 'profileImage' | 'coverImage',
    setItem: (update: (current: ImageItem | null) => ImageItem | null) => void,
  ) => {
    clearError(field);
    setItem((current) => {
      releasePreview(current);
      return null;
    });
  };

  const addGallery = (files: File[]) => {
    const remaining = MAX_GALLERY - gallery.length;
    const accepted = files.filter((file) => fileError(file) === null);
    let message: string | undefined;

    if (accepted.length < files.length) message = 'JPEG・PNG で 5MB 以下の写真だけ追加できます。';
    if (accepted.length > remaining) message = `農園の写真は${MAX_GALLERY}枚まで登録できます。`;

    setErrors((current) => ({ ...current, images: message }));

    accepted.slice(0, remaining).forEach((file) => {
      const item: ImageItem = {
        localId: nextLocalId++,
        key: null,
        previewUrl: URL.createObjectURL(file),
        status: 'uploading',
      };
      const update = (change: Partial<ImageItem>) =>
        setGallery((current) =>
          current.map((target) => (target.localId === item.localId ? { ...target, ...change } : target)),
        );

      setGallery((current) => [...current, item]);
      uploadImage(file)
        .then(({ key }) => update({ key, status: 'done' }))
        .catch(() => update({ status: 'error' }));
    });
  };

  const removeGallery = (target: ImageItem) => {
    releasePreview(target);
    clearError('images');
    setGallery((current) => current.filter(({ localId }) => localId !== target.localId));
  };

  const moveGallery = (index: number, offset: -1 | 1) => {
    setGallery((current) => {
      const next = [...current];
      const [item] = next.splice(index, 1);
      next.splice(index + offset, 0, item);
      return next;
    });
  };

  const showErrors = (nextErrors: FormErrors, message: string) => {
    setErrors(nextErrors);
    // 同じメッセージが続いてもフォーカスを移せるよう、一度空にしてから入れる
    setSubmitError(null);
    window.setTimeout(() => setSubmitError(message), 0);
    setMobileView('edit');
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (profile === null || values === null || isSaving) {
      return;
    }

    if (isUploading) {
      showErrors({}, '画像のアップロードが終わるまでお待ちください。');
      return;
    }

    const failedErrors: FormErrors = {};
    const failed = 'アップロードに失敗しました。もう一度選び直すか、外してください。';
    if (profileImage?.status === 'error') failedErrors.profileImage = failed;
    if (coverImage?.status === 'error') failedErrors.coverImage = failed;
    if (gallery.some(({ status }) => status === 'error')) {
      failedErrors.images = 'アップロードに失敗した写真があります。削除してから、もう一度追加してください。';
    }

    const clientErrors = { ...validate(values), ...failedErrors };

    if (Object.keys(clientErrors).length > 0) {
      showErrors(clientErrors, '入力内容を確認してください。');
      return;
    }

    if (Object.keys(patch).length === 0) {
      setToast('変更はありません。');
      return;
    }

    setIsSaving(true);
    setErrors({});
    setSubmitError(null);

    // 送信した時点の入力。保存中も入力や画像の操作ができるので、応答までの変更を消さないために使う
    const submitted = { values, profileImage, coverImage, gallery };

    try {
      const saved = await updateDashboardProfile(patch);
      const latest = latestRef.current;

      // 送信後に変わっていない項目だけ、サーバーの値にそろえる。
      // 保存中に変えた項目はそのまま残し、「保存していない変更があります」と表示する
      setProfile(saved);
      setErrors({});

      if (latest.values === submitted.values) {
        setValues(toFormValues(saved));
      }

      if (latest.profileImage === submitted.profileImage) {
        releasePreview(submitted.profileImage);
        setProfileImage(singleImage(saved.profileImage, saved.profileImageUrl));
      }

      if (latest.coverImage === submitted.coverImage) {
        releasePreview(submitted.coverImage);
        setCoverImage(singleImage(saved.coverImage, saved.coverImageUrl));
      }

      if (latest.gallery === submitted.gallery) {
        submitted.gallery.forEach(releasePreview);
        setGallery(toGallery(saved));
      }

      setToast('プロフィールを保存しました。');
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        window.location.replace('/signin');
        return;
      }

      if (error instanceof ApiError && error.status === 400) {
        const fieldErrors = errorsFromDetails(error.details);
        const other = error.details.nonFieldErrors?.[0];

        showErrors(
          fieldErrors,
          Object.keys(fieldErrors).length > 0 ? '入力内容を確認してください。' : (other ?? error.message),
        );
      } else if (error instanceof ApiError && error.errorCode === 'PRODUCER_SUSPENDED') {
        // 運営が掲載を止めた。最新の状態を読み込み直して、公開状態を選べないようにする
        showErrors({}, error.message);
        getDashboardProfile()
          .then((latest) => {
            setProfile(latest);
            setValues((current) => (current === null ? current : { ...current, publishStatus: null }));
          })
          .catch(() => {
            // 読み込めなくても、エラーメッセージで状況は伝わる
          });
      } else if (error instanceof ApiError) {
        showErrors({}, error.message);
      } else {
        showErrors({}, '通信に失敗しました。時間をおいて、もう一度お試しください。');
      }
    } finally {
      setIsSaving(false);
    }
  };

  const renderBody = () => {
    if (!canManage) {
      return <Notice>プロフィールの編集は、生産者登録が承認されると使えるようになります。</Notice>;
    }

    if (loadError) {
      return (
        <div
          role="alert"
          className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
        >
          <p className="m-0 font-bold text-marche-red">プロフィールを読み込めませんでした。</p>
          <p className="m-0 mt-1 text-marche-muted">時間をおいて、もう一度お試しください。</p>
          <DashboardButton
            variant="secondary"
            onClick={() => {
              setLoadError(false);
              setReloadCount((count) => count + 1);
            }}
            className="mt-4"
          >
            再読み込み
          </DashboardButton>
        </div>
      );
    }

    if (profile === null || values === null) {
      return (
        <div aria-busy="true" aria-label="読み込み中" className="flex flex-col gap-6">
          {Array.from({ length: 3 }, (_, i) => (
            <div
              key={i}
              className="box-border h-48 animate-pulse rounded-2xl border border-solid border-marche-line bg-white"
            />
          ))}
        </div>
      );
    }

    const isSuspended = profile.publishStatus === 'suspended';
    const errorEntries = Object.entries(errors).filter(([, message]) => message !== undefined);
    const control = (error: string | undefined) => `${controlClassName} ${controlBorder(error)}`;

    return (
      <>
        <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <span
            className={`rounded-full px-3 py-0.5 text-xs font-bold ${
              profile.publishStatus === 'public'
                ? 'bg-marche-sage text-marche-green'
                : isSuspended
                  ? 'bg-marche-red/10 text-marche-red'
                  : 'bg-marche-canvas text-marche-muted'
            }`}
          >
            {profile.publishStatus === 'public' ? '公開中' : isSuspended ? '掲載停止中' : '非公開'}
          </span>
          <span className="text-marche-muted">最終保存：{dateTimeLabel(profile.updatedAt)}</span>
          {isDirty && <span className="font-bold text-marche-orange">保存していない変更があります</span>}
        </div>

        {isSuspended && (
          <div
            role="alert"
            className="mb-5 box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
          >
            <p className="m-0 font-bold text-marche-red">現在、運営により掲載を停止しています。</p>
            <p className="m-0 mt-1 text-marche-muted">
              プロフィールの内容は編集できますが、公開状態は変更できません。くわしくは運営にお問い合わせください。
            </p>
          </div>
        )}

        <div
          role="group"
          aria-label="表示の切り替え"
          className="mb-4 inline-flex rounded-full bg-marche-line/60 p-1 xl:hidden"
        >
          {(
            [
              ['edit', '編集'],
              ['preview', 'プレビュー'],
            ] as const
          ).map(([view, label]) => (
            <button
              key={view}
              type="button"
              aria-pressed={mobileView === view}
              onClick={() => setMobileView(view)}
              className={`box-border min-h-11 cursor-pointer rounded-full border-0 px-5 text-sm font-bold text-marche-ink [font-family:inherit] ${mobileView === view ? 'bg-white shadow-sm' : 'bg-transparent'}`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,24rem)]">
          <form
            noValidate
            onSubmit={handleSubmit}
            className={`min-w-0 flex-col gap-6 ${mobileView === 'edit' ? 'flex' : 'hidden xl:flex'}`}
          >
            {submitError !== null && (
              <div
                ref={errorSummaryRef}
                tabIndex={-1}
                role="alert"
                className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm outline-none"
              >
                <p className="m-0 font-bold text-marche-red">{submitError}</p>
                {errorEntries.length > 0 && (
                  <ul className="m-0 mt-2 pl-5 text-marche-red">
                    {errorEntries.map(([key, message]) => (
                      <li key={key}>
                        <a href={`#profile-${key}`} className="text-marche-red">
                          {message}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <FormSection title="写真">
              <SingleImageField
                id="profile-coverImage"
                label="カバー画像"
                hint="生産者ページのいちばん上に大きく表示されます。横長の写真がおすすめです。"
                item={coverImage}
                error={errors.coverImage}
                shape="wide"
                onSelect={(file) => selectSingle('coverImage', setCoverImage, file)}
                onRemove={() => removeSingle('coverImage', setCoverImage)}
              />
              <SingleImageField
                id="profile-profileImage"
                label="プロフィール画像"
                hint="丸く切り抜いて表示されます。お顔や農園のロゴがおすすめです。"
                item={profileImage}
                error={errors.profileImage}
                shape="round"
                onSelect={(file) => selectSingle('profileImage', setProfileImage, file)}
                onRemove={() => removeSingle('profileImage', setProfileImage)}
              />
              <GalleryField
                items={gallery}
                error={errors.images}
                onAdd={addGallery}
                onRemove={removeGallery}
                onMove={moveGallery}
              />
            </FormSection>

            <FormSection title="基本情報">
              <dl className="m-0 grid grid-cols-1 gap-3 rounded-xl bg-marche-canvas p-4 sm:grid-cols-3">
                <ReadOnlyItem label="事業者名" value={profile.businessName} />
                <ReadOnlyItem label="代表者名" value={profile.representativeName} />
                <ReadOnlyItem label="ジャンル" value={GENRE_LABELS[profile.genre]} />
                <p className="m-0 text-xs text-marche-muted sm:col-span-3">
                  事業者名・代表者名・ジャンルを変更したい場合は、運営にお問い合わせください。
                </p>
              </dl>

              <div className="grid gap-5 sm:grid-cols-2">
                <Field id="profile-prefectureId" label="都道府県" required error={errors.prefectureId}>
                  <select
                    id="profile-prefectureId"
                    aria-invalid={errors.prefectureId !== undefined}
                    aria-describedby={describedBy('profile-prefectureId', false, errors.prefectureId)}
                    className={control(errors.prefectureId)}
                    value={values.prefectureId}
                    onChange={(event) => updateValue('prefectureId', event.target.value)}
                  >
                    <option value="">選んでください</option>
                    {PREFECTURES.map((prefecture) => (
                      <option key={prefecture.id} value={String(prefecture.id)}>
                        {prefecture.name}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field
                  id="profile-city"
                  label="市区町村"
                  required
                  hint="公開されるのは市区町村までです（番地は表示しません）。"
                  error={errors.city}
                >
                  <input
                    id="profile-city"
                    type="text"
                    maxLength={50}
                    autoComplete="address-level2"
                    aria-invalid={errors.city !== undefined}
                    aria-describedby={describedBy('profile-city', true, errors.city)}
                    className={control(errors.city)}
                    value={values.city}
                    onChange={(event) => updateValue('city', event.target.value)}
                  />
                </Field>
              </div>

              <Field
                id="profile-productionItems"
                label="生産品目"
                required
                hint="例）りんご・ぶどう（100文字まで）"
                error={errors.productionItems}
              >
                <input
                  id="profile-productionItems"
                  type="text"
                  maxLength={100}
                  aria-invalid={errors.productionItems !== undefined}
                  aria-describedby={describedBy('profile-productionItems', true, errors.productionItems)}
                  className={control(errors.productionItems)}
                  value={values.productionItems}
                  onChange={(event) => updateValue('productionItems', event.target.value)}
                />
              </Field>

              <Field
                id="profile-intro"
                label="ひとこと紹介"
                required
                hint="生産者ページの名前の下に表示されます。"
                error={errors.intro}
              >
                <textarea
                  id="profile-intro"
                  rows={4}
                  aria-invalid={errors.intro !== undefined}
                  aria-describedby={describedBy('profile-intro', true, errors.intro)}
                  className={`${control(errors.intro)} min-h-28 resize-y leading-relaxed`}
                  value={values.intro}
                  onChange={(event) => updateValue('intro', event.target.value)}
                />
              </Field>

              <div className="grid gap-5 sm:grid-cols-2">
                <Field
                  id="profile-careerStartYear"
                  label="この仕事を始めた年"
                  hint={`西暦。${NEW_FARMER_YEARS}年以内なら「${NEW_FARMER_LABELS[profile.genre]}」のバッジが付きます。`}
                  error={errors.careerStartYear}
                >
                  <input
                    id="profile-careerStartYear"
                    type="text"
                    inputMode="numeric"
                    maxLength={4}
                    placeholder="例）2022"
                    aria-invalid={errors.careerStartYear !== undefined}
                    aria-describedby={describedBy('profile-careerStartYear', true, errors.careerStartYear)}
                    className={control(errors.careerStartYear)}
                    value={values.careerStartYear}
                    onChange={(event) => updateValue('careerStartYear', event.target.value)}
                  />
                </Field>
                <Field
                  id="profile-foundedYear"
                  label="創業年"
                  hint="西暦。代々続く農園なら、事業を始めた年です。"
                  error={errors.foundedYear}
                >
                  <input
                    id="profile-foundedYear"
                    type="text"
                    inputMode="numeric"
                    maxLength={4}
                    placeholder="例）1962"
                    aria-invalid={errors.foundedYear !== undefined}
                    aria-describedby={describedBy('profile-foundedYear', true, errors.foundedYear)}
                    className={control(errors.foundedYear)}
                    value={values.foundedYear}
                    onChange={(event) => updateValue('foundedYear', event.target.value)}
                  />
                </Field>
              </div>
            </FormSection>

            <FormSection title="受け入れ・募集">
              <CheckboxField
                id="profile-acceptsExperience"
                label="体験の受け入れ"
                description="生産者ページに「体験受け入れ中」と表示されます。"
                checked={values.acceptsExperience}
                onChange={(checked) => updateValue('acceptsExperience', checked)}
              />
              <CheckboxField
                id="profile-recruiting"
                label="担い手の募集"
                description="生産者ページに「担い手募集中」と表示されます。"
                checked={values.recruiting}
                onChange={(checked) => updateValue('recruiting', checked)}
              />
            </FormSection>

            <FormSection title="ストーリー">
              <p className="m-0 text-sm text-marche-muted">
                「この仕事を始めた理由」「これからの目標」は、ストーリーが公開中のとき生産者ページに表示されます。
                {profile.storyPublishStatus !== null &&
                  `（ストーリー：${STORY_STATUS_LABELS[profile.storyPublishStatus]}）`}
              </p>
              <dl className="m-0 flex flex-col gap-3">
                {(
                  [
                    ['この仕事を始めた理由', profile.reason],
                    ['これからの目標', profile.goal],
                  ] as const
                ).map(([label, text]) => (
                  <div key={label} className="rounded-xl bg-marche-canvas px-4 py-3">
                    <dt className="text-xs font-bold text-marche-muted">{label}</dt>
                    <dd className="m-0 mt-1 text-sm [overflow-wrap:anywhere]">
                      {text === null || text === '' ? <span className="text-marche-muted">未入力</span> : text}
                    </dd>
                  </div>
                ))}
              </dl>
              <Link to="/dashboard/story" className="self-start text-sm font-bold text-marche-green">
                ストーリー編集で変更する →
              </Link>
            </FormSection>

            {!isSuspended && (
              <FormSection title="公開設定">
                <div id="profile-publishStatus" tabIndex={-1} className="outline-none">
                  <PublishStatusField
                    options={STATUS_OPTIONS}
                    value={values.publishStatus as EditableStatus}
                    onChange={(value) => updateValue('publishStatus', value)}
                  />
                  {errors.publishStatus !== undefined && (
                    <p className="m-0 mt-2 text-xs font-bold text-marche-red">{errors.publishStatus}</p>
                  )}
                </div>
              </FormSection>
            )}

            <div className="flex flex-wrap items-center gap-3">
              <DashboardButton type="submit" disabled={isSaving} className="min-h-11 px-8">
                {isSaving ? '保存中…' : '保存する'}
              </DashboardButton>
              {isDirty && (
                <DashboardButton
                  variant="secondary"
                  disabled={isSaving}
                  onClick={() => {
                    [profileImage, coverImage, ...gallery].forEach(releasePreview);
                    resetForm(profile);
                    setSubmitError(null);
                  }}
                  className="min-h-11"
                >
                  変更を取り消す
                </DashboardButton>
              )}
            </div>
          </form>

          <div className={`min-w-0 ${mobileView === 'preview' ? 'block' : 'hidden xl:block'}`}>
            <ProfilePreview
              profile={profile}
              values={values}
              profileImage={profileImage}
              coverImage={coverImage}
              gallery={gallery}
            />
          </div>
        </div>
      </>
    );
  };

  return (
    <div>
      <h1 className="m-0 font-serif text-2xl font-bold">プロフィール編集</h1>
      <p className="m-0 mt-1 mb-6 text-sm text-marche-muted">
        生産者ページでお客さまに表示される内容です。
      </p>
      {renderBody()}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-4 bottom-6 z-50 flex justify-center">
        {toast !== null && (
          <p className="m-0 max-w-full rounded-xl bg-marche-ink px-5 py-3 text-sm font-bold text-white shadow-lg">
            {toast}
          </p>
        )}
      </div>
    </div>
  );
}

export default DashboardProfileEditPage;
