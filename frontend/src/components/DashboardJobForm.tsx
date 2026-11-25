import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from 'react';

import ApiError from '../api/apiError';
import { uploadImage } from '../api/uploadApi';
import type {
  DashboardJob,
  JobInput,
  JobPayUnit,
  JobTermType,
  JobWritableStatus,
} from '../types/dashboardJob';
import {
  JOB_MAX_LIST_ITEMS,
  JOB_MAX_LIST_ITEM_LENGTH,
  JOB_MAX_WORK_DATES,
  formatDate,
  payUnitLabels,
  termTypeLabels,
  todayInJapan,
} from '../utils/jobFormat';
import { PREFECTURES } from '../utils/prefectures';
import DashboardButton from './DashboardButton';
import {
  CheckboxField,
  Field,
  FormSection,
  PublishStatusField,
  controlBorder,
  controlClassName,
  describedBy,
  type PublishStatusOption,
} from './DashboardFormParts';
import { PlusIcon } from './DashboardIcons';

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png'];
const MAX_INT = 2147483647;

// 入力欄の値（数値も入力中は文字列、リストは1行1項目の文字列で持つ）
type JobFormValues = {
  title: string;
  prefectureId: string;
  workPlace: string;
  description: string;
  termType: JobTermType;
  inexperiencedOk: boolean;
  payUnit: JobPayUnit;
  payAmount: string;
  workHours: string;
  slots: string;
  periodStart: string;
  periodEnd: string;
  requirements: string;
  belongings: string;
  notes: string;
};

// 勤務日1行分（id は登録済みの勤務日だけ持つ）
type WorkDateRow = {
  // 画面内だけで使うID
  localId: number;
  id?: number;
  workDate: string;
  // 登録済みの日付（変えたかどうかの判定に使う）
  originalDate?: string;
  neededCount: string;
  // 応募者が希望している勤務日（削除・日付の変更はできない。必要人数は変えられる）
  hasApplicants: boolean;
};

// カバー写真（1枚まで）
type CoverImage =
  | { kind: 'saved'; key: string; previewUrl: string | null }
  | { kind: 'new'; previewUrl: string; status: 'uploading' | 'done' | 'error'; key: string | null };

type FieldName = keyof JobFormValues | 'workDates' | 'coverImage';
type FieldErrors = Partial<Record<FieldName, string>>;

// 画面の並び順（入力エラーのとき、上にある項目からフォーカスする）
const FIELD_ORDER: FieldName[] = [
  'coverImage',
  'title',
  'prefectureId',
  'workPlace',
  'description',
  'payAmount',
  'workHours',
  'slots',
  'periodStart',
  'periodEnd',
  'workDates',
  'requirements',
  'belongings',
  'notes',
];

const publishStatusOptions: PublishStatusOption<JobWritableStatus>[] = [
  {
    value: 'public',
    label: '公開',
    description: 'お仕事を探している方の画面に表示し、応募を受け付けます。',
  },
  { value: 'private', label: '非公開', description: 'お仕事を探している方の画面には表示しません。' },
  { value: 'draft', label: '下書き', description: '作成中として保存します。' },
];

const termTypes: JobTermType[] = ['one_day', 'short', 'long'];
const payUnits: JobPayUnit[] = ['hourly', 'daily', 'monthly'];

const initialValues: JobFormValues = {
  title: '',
  prefectureId: '',
  workPlace: '',
  description: '',
  termType: 'short',
  inexperiencedOk: true,
  payUnit: 'hourly',
  payAmount: '',
  workHours: '',
  slots: '',
  periodStart: '',
  periodEnd: '',
  requirements: '',
  belongings: '',
  notes: '',
};

// 編集時：登録済みの求人から入力欄の値を作る
function toFormValues(job: DashboardJob): JobFormValues {
  const lines = (items: string[] | null) => (items ?? []).join('\n');

  return {
    title: job.title,
    prefectureId: String(job.prefectureId),
    workPlace: job.workPlace,
    description: job.description,
    termType: job.termType,
    inexperiencedOk: job.inexperiencedOk,
    payUnit: job.payUnit,
    payAmount: String(job.payAmount),
    workHours: job.workHours,
    slots: String(job.slots),
    periodStart: job.periodStart ?? '',
    periodEnd: job.periodEnd ?? '',
    requirements: lines(job.requirements),
    belongings: lines(job.belongings),
    notes: lines(job.notes),
  };
}

function toWorkDateRows(job: DashboardJob, lockedIds: ReadonlySet<number>): WorkDateRow[] {
  return job.workDates.map((day, index) => ({
    localId: index + 1,
    id: day.id,
    workDate: day.workDate,
    originalDate: day.workDate,
    neededCount: String(day.neededCount),
    hasApplicants: lockedIds.has(day.id),
  }));
}

// 選んだファイルのプレビュー（blob:）を解放する
function releasePreview(cover: CoverImage | null) {
  if (cover?.kind === 'new') {
    URL.revokeObjectURL(cover.previewUrl);
  }
}

// 1行1項目の入力を配列にする（空行は除く）
function toLines(value: string): string[] {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '');
}

function isWholeNumber(value: string) {
  return /^\d+$/.test(value) && Number(value) <= MAX_INT;
}

function isCount(value: string) {
  return isWholeNumber(value) && Number(value) >= 1;
}

function validateRequiredText(value: string, label: string, maxLength: number) {
  const text = value.trim();

  if (text === '') {
    return `${label}を入力してください。`;
  }

  return text.length > maxLength ? `${label}は${maxLength}文字以内で入力してください。` : undefined;
}

function validateLines(value: string, label: string) {
  const lines = toLines(value);

  if (lines.length > JOB_MAX_LIST_ITEMS) {
    return `${label}は${JOB_MAX_LIST_ITEMS}行までにしてください。`;
  }

  return lines.some((line) => line.length > JOB_MAX_LIST_ITEM_LENGTH)
    ? `${label}は1行${JOB_MAX_LIST_ITEM_LENGTH}文字以内で入力してください。`
    : undefined;
}

function validateWorkDates(rows: WorkDateRow[], values: JobFormValues): string | undefined {
  const today = todayInJapan();
  const { slots, periodStart, periodEnd } = values;

  // 長期のお仕事は勤務日を登録できない
  if (values.termType === 'long' && rows.length > 0) {
    return '長期のお仕事には勤務日を登録できません。勤務日を削除するか、期間を変えてください。';
  }

  if (rows.length > JOB_MAX_WORK_DATES) {
    return `勤務日は${JOB_MAX_WORK_DATES}日までにしてください。`;
  }

  if (rows.some((row) => row.workDate === '')) {
    return '勤務日の日付を選んでください。';
  }

  if (new Set(rows.map((row) => row.workDate)).size !== rows.length) {
    return '同じ日付の勤務日が重複しています。';
  }

  if (rows.some((row) => row.workDate !== row.originalDate && row.workDate < today)) {
    return '新しく追加・変更する勤務日は今日以降にしてください。';
  }

  if (rows.some((row) => !isCount(row.neededCount))) {
    return '勤務日ごとの必要人数を1以上の半角数字で入力してください。';
  }

  if (isCount(slots) && rows.some((row) => Number(row.neededCount) > Number(slots))) {
    return '勤務日ごとの必要人数は募集人数以下にしてください。';
  }

  // 勤務日は募集期間の中にする
  if (periodStart !== '' && rows.some((row) => row.workDate < periodStart)) {
    return '勤務日は募集開始日以降にしてください。';
  }

  if (periodEnd !== '' && rows.some((row) => row.workDate > periodEnd)) {
    return '勤務日は募集終了日以前にしてください。';
  }

  return undefined;
}

function validate(
  values: JobFormValues,
  rows: WorkDateRow[],
  status: JobWritableStatus | null,
): FieldErrors {
  const errors: FieldErrors = {
    title: validateRequiredText(values.title, 'タイトル', 100),
    workPlace: validateRequiredText(values.workPlace, '勤務地', 200),
    description: validateRequiredText(values.description, '仕事内容', 10000),
    workHours: validateRequiredText(values.workHours, '勤務時間', 50),
    requirements: validateLines(values.requirements, '応募条件'),
    belongings: validateLines(values.belongings, '持ち物'),
    notes: validateLines(values.notes, '注意事項'),
    workDates: validateWorkDates(rows, values),
  };

  if (values.prefectureId === '') {
    errors.prefectureId = '勤務地の都道府県を選んでください。';
  }

  if (!isWholeNumber(values.payAmount) || Number(values.payAmount) < 1) {
    errors.payAmount = '報酬を1以上の半角数字（円）で入力してください。';
  }

  if (!isCount(values.slots)) {
    errors.slots = '募集人数を1以上の半角数字で入力してください。';
  }

  if (values.periodStart !== '' && values.periodEnd !== '' && values.periodStart > values.periodEnd) {
    errors.periodEnd = '募集終了日は募集開始日以降にしてください。';
  }

  // 単発・短期のお仕事を公開するには、今日以降の勤務日が1日以上必要
  if (
    errors.workDates === undefined &&
    status === 'public' &&
    values.termType !== 'long' &&
    !rows.some((row) => row.workDate >= todayInJapan())
  ) {
    errors.workDates = '単発・短期のお仕事を公開するには、今日以降の勤務日を1日以上追加してください。';
  }

  return Object.fromEntries(
    Object.entries(errors).filter(([, message]) => message !== undefined),
  ) as FieldErrors;
}

function toInput(
  values: JobFormValues,
  rows: WorkDateRow[],
  coverImage: string | null,
  status: JobWritableStatus,
): JobInput {
  const optionalLines = (value: string) => {
    const lines = toLines(value);

    return lines.length === 0 ? null : lines;
  };

  return {
    title: values.title.trim(),
    prefectureId: Number(values.prefectureId),
    termType: values.termType,
    payUnit: values.payUnit,
    payAmount: Number(values.payAmount),
    periodStart: values.periodStart === '' ? null : values.periodStart,
    periodEnd: values.periodEnd === '' ? null : values.periodEnd,
    workHours: values.workHours.trim(),
    workPlace: values.workPlace.trim(),
    slots: Number(values.slots),
    description: values.description.trim(),
    requirements: optionalLines(values.requirements),
    belongings: optionalLines(values.belongings),
    notes: optionalLines(values.notes),
    inexperiencedOk: values.inexperiencedOk,
    coverImage,
    publishStatus: status,
    workDates: [...rows]
      .sort((a, b) => a.workDate.localeCompare(b.workDate))
      .map((row) => ({
        ...(row.id === undefined ? {} : { id: row.id }),
        workDate: row.workDate,
        neededCount: Number(row.neededCount),
      })),
  };
}

// API の項目名（workDates.0.workDate など）を入力欄の名前にする
function toFormField(apiField: string): FieldName | null {
  const name = apiField.split(/[.[]/)[0];

  if (name === 'workDates') {
    return 'workDates';
  }

  if (name === 'coverImage') {
    return 'coverImage';
  }

  return name in initialValues ? (name as FieldName) : null;
}

const NO_LOCKED_DATES: ReadonlySet<number> = new Set();

type DashboardJobFormProps = {
  // 編集する求人（渡さない場合は新規登録）
  job?: DashboardJob;
  // 応募者が希望している勤務日の ID（削除・日付の変更ができない）
  lockedWorkDateIds?: ReadonlySet<number>;
  // 保存処理（失敗時は ApiError を投げる）。
  // 掲載停止中の求人は公開状態を変えられないため、呼び出し側で publishStatus を外して送る
  onSubmit: (input: JobInput) => Promise<void>;
  cancelTo: string;
};

// 求人の入力フォーム（写真・求人の情報・勤務条件・勤務日・応募条件と案内）
// 新規登録は「下書きとして保存」「公開する」、編集は公開状態を選んで「変更を保存」
function DashboardJobForm({
  job,
  lockedWorkDateIds = NO_LOCKED_DATES,
  onSubmit,
  cancelTo,
}: DashboardJobFormProps) {
  const isEdit = job !== undefined;
  // 運営による掲載停止中は、内容は編集できるが公開状態は変えられない
  const isSuspended = job?.publishStatus === 'suspended';

  const [values, setValues] = useState<JobFormValues>(() =>
    isEdit ? toFormValues(job) : initialValues,
  );
  const [rows, setRows] = useState<WorkDateRow[]>(() =>
    isEdit ? toWorkDateRows(job, lockedWorkDateIds) : [],
  );
  const [cover, setCover] = useState<CoverImage | null>(() =>
    job?.coverImage ? { kind: 'saved', key: job.coverImage, previewUrl: job.coverImageUrl ?? null } : null,
  );
  const [publishStatus, setPublishStatus] = useState<JobWritableStatus>(
    job !== undefined && job.publishStatus !== 'suspended' ? job.publishStatus : 'draft',
  );
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<JobWritableStatus | null>(null);

  const nextRowId = useRef((job?.workDates.length ?? 0) + 1);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // 画面を離れるときにプレビュー用URLを解放する
  const coverRef = useRef(cover);

  useEffect(() => {
    coverRef.current = cover;
  }, [cover]);

  useEffect(() => () => releasePreview(coverRef.current), []);

  const setValue = <K extends keyof JobFormValues>(name: K, value: JobFormValues[K]) => {
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
  };

  const updateRow = (localId: number, change: Partial<WorkDateRow>) => {
    setRows((current) => current.map((row) => (row.localId === localId ? { ...row, ...change } : row)));
    setErrors((current) => ({ ...current, workDates: undefined }));
  };

  const addRow = () => {
    const localId = nextRowId.current++;

    setRows((current) => [
      ...current,
      {
        localId,
        workDate: '',
        // 1日の必要人数は、まず募集人数と同じにしておく
        neededCount: isCount(values.slots) ? values.slots : '1',
        hasApplicants: false,
      },
    ]);
    setErrors((current) => ({ ...current, workDates: undefined }));
    // 追加した行の日付欄へ移動する
    window.setTimeout(() => document.getElementById(`job-workDate-${localId}`)?.focus(), 0);
  };

  const removeRow = (localId: number) => {
    setRows((current) => current.filter((row) => row.localId !== localId));
    setErrors((current) => ({ ...current, workDates: undefined }));
  };

  const handleFileSelected = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    // 同じファイルを続けて選べるように空にする
    event.target.value = '';

    if (file === undefined) {
      return;
    }

    if (!ACCEPTED_IMAGE_TYPES.includes(file.type) || file.size > MAX_IMAGE_BYTES) {
      setErrors((current) => ({
        ...current,
        coverImage: 'JPEG・PNG で 5MB 以下の写真を選んでください。',
      }));
      return;
    }

    releasePreview(cover);
    const previewUrl = URL.createObjectURL(file);
    setCover({ kind: 'new', previewUrl, status: 'uploading', key: null });
    setErrors((current) => ({ ...current, coverImage: undefined }));

    uploadImage(file)
      .then(({ key }) =>
        setCover((current) =>
          current?.kind === 'new' && current.previewUrl === previewUrl
            ? { ...current, status: 'done', key }
            : current,
        ),
      )
      .catch(() =>
        setCover((current) =>
          current?.kind === 'new' && current.previewUrl === previewUrl
            ? { ...current, status: 'error' }
            : current,
        ),
      );
  };

  const removeCover = () => {
    releasePreview(cover);
    setCover(null);
    setErrors((current) => ({ ...current, coverImage: undefined }));
  };

  const isUploading = cover?.kind === 'new' && cover.status === 'uploading';
  const coverImage = cover === null ? null : cover.key;

  const submit = async (status: JobWritableStatus) => {
    setFormError(null);

    if (cover?.kind === 'new' && cover.status === 'error') {
      setErrors((current) => ({
        ...current,
        coverImage: 'アップロードに失敗しました。写真を削除するか、選び直してください。',
      }));
      document.getElementById('job-coverImage')?.focus();
      return;
    }

    // 掲載停止中は公開状態を送らないため、公開の条件は確認しない
    const nextErrors = validate(values, rows, isSuspended ? null : status);
    setErrors(nextErrors);

    const firstError = FIELD_ORDER.find((name) => nextErrors[name] !== undefined);

    if (firstError !== undefined) {
      setFormError('入力内容を確認してください。');
      // 勤務日のエラーは、追加ボタンではなく最初の（変更できる）日付欄へ移動する
      const target =
        (firstError === 'workDates'
          ? document.querySelector<HTMLElement>('input[id^="job-workDate-"]:not(:disabled)')
          : null) ?? document.getElementById(`job-${firstError}`);
      target?.focus();
      return;
    }

    setSubmitting(status);

    try {
      await onSubmit(toInput(values, rows, coverImage, status));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        window.location.replace('/signin');
        return;
      }

      if (error instanceof ApiError) {
        // 項目ごとのエラーは入力欄の下に出す
        const serverErrors: FieldErrors = {};

        Object.entries(error.details).forEach(([field, messages]) => {
          const formField = toFormField(field);

          if (formField !== null && serverErrors[formField] === undefined) {
            serverErrors[formField] = messages[0];
          }
        });

        setErrors(serverErrors);
        setFormError(error.message);
      } else {
        setFormError('通信に失敗しました。時間をおいて、もう一度お試しください。');
      }

      setSubmitting(null);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    // Enter キーでの送信は、新規登録では下書き保存、編集では選んだ公開状態で保存
    event.preventDefault();
    submit(isEdit ? publishStatus : 'draft');
  };

  // テキスト入力欄（1行）
  const renderText = (
    name: 'title' | 'workPlace' | 'workHours',
    label: string,
    maxLength: number,
    placeholder: string,
    hint?: string,
  ) => {
    const id = `job-${name}`;

    return (
      <Field id={id} label={label} required hint={hint} error={errors[name]}>
        <input
          id={id}
          type="text"
          maxLength={maxLength}
          placeholder={placeholder}
          value={values[name]}
          onChange={(event) => setValue(name, event.target.value)}
          aria-invalid={errors[name] !== undefined}
          aria-describedby={describedBy(id, hint !== undefined, errors[name])}
          className={`${controlClassName} ${controlBorder(errors[name])} disabled:bg-marche-canvas disabled:text-marche-muted`}
        />
      </Field>
    );
  };

  // 1行1項目の入力欄（応募条件・持ち物・注意事項）
  const renderLinesField = (
    name: 'requirements' | 'belongings' | 'notes',
    label: string,
    hint: string,
    placeholder: string,
  ) => {
    const id = `job-${name}`;

    return (
      <Field id={id} label={label} hint={hint} error={errors[name]}>
        <textarea
          id={id}
          rows={4}
          placeholder={placeholder}
          value={values[name]}
          onChange={(event) => setValue(name, event.target.value)}
          aria-invalid={errors[name] !== undefined}
          aria-describedby={describedBy(id, true, errors[name])}
          className={`${controlClassName} ${controlBorder(errors[name])} resize-y disabled:bg-marche-canvas disabled:text-marche-muted`}
        />
      </Field>
    );
  };

  const today = todayInJapan();

  return (
    <form noValidate onSubmit={handleSubmit} className="flex flex-col gap-6">
      {formError !== null && (
        <p
          role="alert"
          className="m-0 box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-4 text-sm font-bold text-marche-red"
        >
          {formError}
        </p>
      )}

      {lockedWorkDateIds.size > 0 && (
        <p className="m-0 box-border rounded-2xl border border-solid border-marche-orange/40 bg-marche-orange/15 p-4 text-sm leading-relaxed">
          <span className="font-bold">応募者が希望している勤務日があります。</span>
          その勤務日は、削除や日付の変更ができません（必要人数は変えられます）。
          報酬や勤務時間などを変える場合は、応募者にも連絡してください。
        </p>
      )}

      <FormSection title="写真">
        <div>
          <p className="m-0 text-sm">求人一覧・詳細に表示する写真を1枚登録できます。</p>
          <p className="m-0 text-xs text-marche-muted">JPEG・PNG、5MB まで。なくても登録できます。</p>
        </div>

        {cover === null ? (
          <button
            id="job-coverImage"
            type="button"
            onClick={() => fileInputRef.current?.click()}
            aria-describedby={errors.coverImage === undefined ? undefined : 'job-coverImage-error'}
            className={`box-border flex aspect-[4/3] w-full max-w-xs cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed bg-marche-canvas p-0 text-sm font-bold text-marche-green font-[inherit] hover:bg-marche-sage disabled:cursor-not-allowed disabled:opacity-50 ${errors.coverImage === undefined ? 'border-marche-green/40' : 'border-marche-red'}`}
          >
            <PlusIcon />
            写真を追加
          </button>
        ) : (
          <div className="flex flex-wrap items-end gap-3">
            {cover.kind === 'new' ? (
              <div className="relative w-full max-w-xs">
                <img
                  src={cover.previewUrl}
                  alt="カバー写真"
                  className={`block aspect-[4/3] w-full rounded-xl bg-marche-sage object-cover ${cover.status === 'done' ? '' : 'opacity-50'}`}
                />
                {cover.status !== 'done' && (
                  <span className="absolute inset-x-1.5 bottom-1.5 rounded-lg bg-white/90 px-1 py-0.5 text-center text-xs font-bold">
                    {cover.status === 'uploading' ? (
                      'アップロード中…'
                    ) : (
                      <span className="text-marche-red">失敗しました</span>
                    )}
                  </span>
                )}
              </div>
            ) : cover.previewUrl ? (
              <img
                src={cover.previewUrl}
                alt="カバー写真"
                className="block aspect-[4/3] w-full max-w-xs rounded-xl bg-marche-sage object-cover"
              />
            ) : (
              <p className="m-0 box-border w-full max-w-xs rounded-xl bg-marche-sage p-4 text-sm">
                登録済みの写真があります。写真を変更する場合は下のボタンを押してください。
              </p>
            )}
            <div className="flex gap-2">
              <DashboardButton
                id="job-coverImage"
                variant="secondary"
                size="sm"
                disabled={isUploading}
                onClick={() => fileInputRef.current?.click()}
              >
                写真を変更
              </DashboardButton>
              <DashboardButton variant="danger" size="sm" disabled={isUploading} onClick={removeCover}>
                削除
              </DashboardButton>
            </div>
          </div>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_IMAGE_TYPES.join(',')}
          hidden
          onChange={handleFileSelected}
        />
        {errors.coverImage !== undefined && (
          <p id="job-coverImage-error" className="m-0 text-xs font-bold text-marche-red">
            {errors.coverImage}
          </p>
        )}
      </FormSection>

      <FormSection title="求人の情報">
        {renderText('title', 'タイトル', 100, '例）りんごの収穫・選果スタッフ')}

        <div className="grid gap-5 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)]">
          <Field id="job-prefectureId" label="勤務地（都道府県）" required error={errors.prefectureId}>
            <select
              id="job-prefectureId"
              value={values.prefectureId}
              onChange={(event) => setValue('prefectureId', event.target.value)}
              aria-invalid={errors.prefectureId !== undefined}
              aria-describedby={describedBy('job-prefectureId', false, errors.prefectureId)}
              className={`${controlClassName} ${controlBorder(errors.prefectureId)} disabled:bg-marche-canvas disabled:text-marche-muted`}
            >
              <option value="">選んでください</option>
              {PREFECTURES.map(({ id, name }) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </Field>

          {renderText('workPlace', '勤務地', 200, '例）長野県安曇野市 山本農園 りんご園')}
        </div>

        <Field
          id="job-description"
          label="仕事内容"
          required
          hint="どんな作業をお願いするか、未経験の方へのサポートなどを書いてください。"
          error={errors.description}
        >
          <textarea
            id="job-description"
            rows={6}
            maxLength={10000}
            value={values.description}
            onChange={(event) => setValue('description', event.target.value)}
            aria-invalid={errors.description !== undefined}
            aria-describedby={describedBy('job-description', true, errors.description)}
            className={`${controlClassName} ${controlBorder(errors.description)} resize-y disabled:bg-marche-canvas disabled:text-marche-muted`}
          />
        </Field>

        <fieldset className="m-0 min-w-0 border-0 p-0">
          <legend className="text-sm font-bold">
            期間<span className="ml-2 text-xs font-normal text-marche-red">必須</span>
          </legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {termTypes.map((termType) => (
              <label
                key={termType}
                className={`box-border flex cursor-pointer items-center gap-2 rounded-full border border-solid px-4 py-2 text-sm ${values.termType === termType ? 'border-marche-green bg-marche-sage font-bold' : 'border-marche-line bg-white'}`}
              >
                <input
                  type="radio"
                  name="termType"
                  value={termType}
                  checked={values.termType === termType}
                  onChange={() => setValue('termType', termType)}
                  className="m-0 size-4 accent-marche-green"
                />
                {termTypeLabels[termType]}
              </label>
            ))}
          </div>
        </fieldset>

        <CheckboxField
          id="job-inexperiencedOk"
          label="未経験OK"
          description="はじめての方でも応募しやすいお仕事として表示します。"
          checked={values.inexperiencedOk}
          onChange={(checked) => setValue('inexperiencedOk', checked)}
        />
      </FormSection>

      <FormSection title="勤務条件">
        <div className="grid gap-5 sm:grid-cols-[minmax(0,9rem)_minmax(0,1fr)]">
          <Field id="job-payUnit" label="報酬の種類" required>
            <select
              id="job-payUnit"
              value={values.payUnit}
              onChange={(event) => setValue('payUnit', event.target.value as JobPayUnit)}
              className={`${controlClassName} border-marche-line disabled:bg-marche-canvas disabled:text-marche-muted`}
            >
              {payUnits.map((payUnit) => (
                <option key={payUnit} value={payUnit}>
                  {payUnitLabels[payUnit]}
                </option>
              ))}
            </select>
          </Field>

          <Field id="job-payAmount" label="報酬額" required error={errors.payAmount}>
            <div className="flex items-center gap-2">
              <input
                id="job-payAmount"
                type="text"
                inputMode="numeric"
                placeholder="1200"
                value={values.payAmount}
                onChange={(event) => setValue('payAmount', event.target.value)}
                aria-invalid={errors.payAmount !== undefined}
                aria-describedby={describedBy('job-payAmount', false, errors.payAmount)}
                className={`${controlClassName} ${controlBorder(errors.payAmount)} disabled:bg-marche-canvas disabled:text-marche-muted`}
              />
              <span className="shrink-0 text-sm">円</span>
            </div>
          </Field>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          {renderText('workHours', '勤務時間', 50, '例）8:00〜15:00（休憩1時間）')}

          <Field
            id="job-slots"
            label="募集人数"
            required
            hint="求人全体で採用する人数です。"
            error={errors.slots}
          >
            <div className="flex items-center gap-2">
              <input
                id="job-slots"
                type="text"
                inputMode="numeric"
                placeholder="5"
                value={values.slots}
                onChange={(event) => setValue('slots', event.target.value)}
                aria-invalid={errors.slots !== undefined}
                aria-describedby={describedBy('job-slots', true, errors.slots)}
                className={`${controlClassName} ${controlBorder(errors.slots)}`}
              />
              <span className="shrink-0 text-sm">人</span>
            </div>
          </Field>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            id="job-periodStart"
            label="募集開始日"
            hint="空欄にすると、公開した日から募集します。"
            error={errors.periodStart}
          >
            <input
              id="job-periodStart"
              type="date"
              value={values.periodStart}
              onChange={(event) => setValue('periodStart', event.target.value)}
              aria-invalid={errors.periodStart !== undefined}
              aria-describedby={describedBy('job-periodStart', true, errors.periodStart)}
              className={`${controlClassName} ${controlBorder(errors.periodStart)} disabled:bg-marche-canvas disabled:text-marche-muted`}
            />
          </Field>
          <Field
            id="job-periodEnd"
            label="募集終了日"
            hint="空欄にすると、期限なしで募集します。"
            error={errors.periodEnd}
          >
            <input
              id="job-periodEnd"
              type="date"
              value={values.periodEnd}
              onChange={(event) => setValue('periodEnd', event.target.value)}
              aria-invalid={errors.periodEnd !== undefined}
              aria-describedby={describedBy('job-periodEnd', true, errors.periodEnd)}
              className={`${controlClassName} ${controlBorder(errors.periodEnd)} disabled:bg-marche-canvas disabled:text-marche-muted`}
            />
          </Field>
        </div>
      </FormSection>

      <FormSection title="勤務日">
        <p id="job-workDates-hint" className="m-0 text-sm">
          応募者が希望日を選べるよう、勤務日と1日に必要な人数を登録します（{JOB_MAX_WORK_DATES}日まで）。
          <span className="block text-xs text-marche-muted">
            {values.termType === 'long'
              ? '長期のお仕事は勤務日を登録しません。'
              : '単発・短期のお仕事を公開するには、今日以降の勤務日が1日以上必要です。'}
          </span>
        </p>

        {rows.length > 0 && (
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {rows.map((row, index) => {
              const isPast = row.originalDate !== undefined && row.originalDate < today;
              const dateId = `job-workDate-${row.localId}`;
              const countId = `job-neededCount-${row.localId}`;

              return (
                <li
                  key={row.localId}
                  className="box-border flex flex-wrap items-end gap-3 rounded-xl bg-marche-canvas p-3"
                >
                  <label htmlFor={dateId} className="flex min-w-0 flex-col gap-1 text-xs font-bold">
                    勤務日{index + 1}
                    <input
                      id={dateId}
                      type="date"
                      min={row.originalDate === undefined ? today : undefined}
                      disabled={row.hasApplicants || isPast}
                      value={row.workDate}
                      onChange={(event) => updateRow(row.localId, { workDate: event.target.value })}
                      aria-invalid={errors.workDates !== undefined}
                      aria-describedby={errors.workDates === undefined ? undefined : 'job-workDates-error'}
                      className={`${controlClassName} ${controlBorder(errors.workDates)} w-auto text-sm font-normal disabled:bg-white disabled:text-marche-muted`}
                    />
                  </label>
                  <label htmlFor={countId} className="flex min-w-0 flex-col gap-1 text-xs font-bold">
                    必要人数
                    <span className="flex items-center gap-2">
                      <input
                        id={countId}
                        type="text"
                        inputMode="numeric"
                        value={row.neededCount}
                        onChange={(event) =>
                          updateRow(row.localId, { neededCount: event.target.value })
                        }
                        aria-invalid={errors.workDates !== undefined}
                        aria-describedby={errors.workDates === undefined ? undefined : 'job-workDates-error'}
                        className={`${controlClassName} ${controlBorder(errors.workDates)} w-20 text-sm font-normal disabled:bg-white disabled:text-marche-muted`}
                      />
                      <span className="text-sm font-normal">人</span>
                    </span>
                  </label>
                  <p className="m-0 pb-2.5 text-xs text-marche-muted">
                    {row.workDate !== '' && formatDate(row.workDate)}
                    {isPast && '（終了）'}
                    {row.hasApplicants && ' ・ 希望者あり'}
                  </p>
                  {!row.hasApplicants && (
                    <DashboardButton
                      variant="secondary"
                      size="sm"
                      className="ml-auto"
                      aria-label={`勤務日${index + 1}を削除`}
                      onClick={() => removeRow(row.localId)}
                    >
                      削除
                    </DashboardButton>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {values.termType !== 'long' && rows.length < JOB_MAX_WORK_DATES && (
          <DashboardButton
            id="job-workDates"
            variant="secondary"
            className="self-start"
            aria-describedby={['job-workDates-hint', errors.workDates === undefined ? '' : 'job-workDates-error'].filter(Boolean).join(' ')}
            onClick={addRow}
          >
            <PlusIcon className="size-4" />
            勤務日を追加
          </DashboardButton>
        )}
        {errors.workDates !== undefined && (
          <p id="job-workDates-error" className="m-0 text-xs font-bold text-marche-red">
            {errors.workDates}
          </p>
        )}
      </FormSection>

      <FormSection title="応募条件と当日の案内">
        {renderLinesField(
          'requirements',
          '応募条件',
          `1行に1つずつ書いてください（${JOB_MAX_LIST_ITEMS}行まで）。`,
          '18歳以上の方\n3日以上勤務できる方',
        )}
        {renderLinesField('belongings', '持ち物', '1行に1つずつ書いてください。', '汚れてもよい服装\n長靴\n飲み物')}
        {renderLinesField(
          'notes',
          '注意事項',
          '雨天時の対応や住み込みの有無など。1行に1つずつ書いてください。',
          '雨天時は選果場での作業になります。',
        )}
      </FormSection>

      {isEdit && (
        <FormSection title="公開設定">
          {isSuspended ? (
            <p className="m-0 text-sm">
              運営により掲載停止中のため、公開状態は変更できません。内容の修正は保存できます。くわしくは運営にお問い合わせください。
            </p>
          ) : (
            <>
              <PublishStatusField
                options={publishStatusOptions}
                value={publishStatus}
                onChange={setPublishStatus}
              />
              <p className="m-0 text-xs text-marche-muted">
                非公開・下書きにしても、届いている応募の選考は続けられます。
              </p>
            </>
          )}
        </FormSection>
      )}

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-end">
        <DashboardButton to={cancelTo} variant="secondary">
          キャンセル
        </DashboardButton>
        {isEdit ? (
          <DashboardButton type="submit" disabled={submitting !== null || isUploading}>
            {submitting !== null ? '保存中…' : '変更を保存'}
          </DashboardButton>
        ) : (
          <>
            <DashboardButton
              type="submit"
              variant="secondary"
              disabled={submitting !== null || isUploading}
            >
              {submitting === 'draft' ? '保存中…' : '下書きとして保存'}
            </DashboardButton>
            <DashboardButton
              disabled={submitting !== null || isUploading}
              onClick={() => submit('public')}
            >
              {submitting === 'public' ? '公開中…' : '公開する'}
            </DashboardButton>
          </>
        )}
      </div>
      {isUploading && (
        <p className="m-0 text-right text-xs text-marche-muted">
          写真のアップロードが終わると保存できます。
        </p>
      )}
    </form>
  );
}

export default DashboardJobForm;
