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
  DashboardExperience,
  ExperienceInput,
  ExperienceWritableStatus,
} from '../types/dashboardExperience';
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
import {
  EXPERIENCE_MAX_IMAGES,
  EXPERIENCE_MAX_LIST_ITEMS,
  EXPERIENCE_MAX_LIST_ITEM_LENGTH,
} from '../utils/experienceLimits';

// API の仕様に合わせた上限（画像・案内の行数はモックAPIと共通の定数を使う）
const MAX_IMAGES = EXPERIENCE_MAX_IMAGES;
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png'];
const MAX_INT = 2147483647;
const MAX_LIST_ITEMS = EXPERIENCE_MAX_LIST_ITEMS;
const MAX_LIST_ITEM_LENGTH = EXPERIENCE_MAX_LIST_ITEM_LENGTH;

// 入力欄の値（数値も入力中は文字列、リストは1行1項目の文字列で持つ）
type ExperienceFormValues = {
  title: string;
  prefectureId: string;
  place: string;
  description: string;
  priceAdult: string;
  priceChild: string;
  ageCondition: string;
  familyOk: boolean;
  beginnerOk: boolean;
  flow: string;
  belongings: string;
  notes: string;
  cancelPolicy: string;
};

type FieldName = keyof ExperienceFormValues | 'images';
type FieldErrors = Partial<Record<FieldName, string>>;

// 画像1枚分（選んだ直後からアップロード完了まで）
type ImageItem = {
  // 画面内だけで使うID
  localId: number;
  previewUrl: string;
  status: 'uploading' | 'done' | 'error';
  key: string | null;
};

const publishStatusOptions: PublishStatusOption<ExperienceWritableStatus>[] = [
  {
    value: 'public',
    label: '公開',
    description: 'お客さまの画面に表示し、予約枠から申し込めるようにします。',
  },
  { value: 'private', label: '非公開', description: 'お客さまの画面には表示しません。' },
  { value: 'draft', label: '下書き', description: '作成中として保存します。' },
];

const initialValues: ExperienceFormValues = {
  title: '',
  prefectureId: '',
  place: '',
  description: '',
  priceAdult: '',
  priceChild: '',
  ageCondition: '',
  familyOk: false,
  beginnerOk: true,
  flow: '',
  belongings: '',
  notes: '',
  cancelPolicy: '',
};

// 編集時：登録済みの体験から入力欄の値を作る
function toFormValues(experience: DashboardExperience): ExperienceFormValues {
  const lines = (items: string[] | null) => (items ?? []).join('\n');

  return {
    title: experience.title,
    prefectureId: String(experience.prefectureId),
    place: experience.place,
    description: experience.description,
    priceAdult: String(experience.priceAdult),
    priceChild: experience.priceChild === null ? '' : String(experience.priceChild),
    ageCondition: experience.ageCondition ?? '',
    familyOk: experience.familyOk,
    beginnerOk: experience.beginnerOk,
    flow: lines(experience.flow),
    belongings: lines(experience.belongings),
    notes: lines(experience.notes),
    cancelPolicy: experience.cancelPolicy,
  };
}

// 編集時：登録済みの画像（並び順どおり）
function toImageItems(experience: DashboardExperience): ImageItem[] {
  return [...experience.images]
    .sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id)
    .map((image, index) => ({
      localId: index + 1,
      previewUrl: image.url,
      status: 'done',
      key: image.imageKey,
    }));
}

// 選んだファイルのプレビュー（blob:）だけ解放する。登録済みの画像の URL は対象外
function releasePreview(previewUrl: string) {
  if (previewUrl.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl);
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

function validateRequiredText(
  value: string,
  label: string,
  maxLength: number,
): string | undefined {
  const text = value.trim();

  if (text === '') {
    return `${label}を入力してください。`;
  }

  if (text.length > maxLength) {
    return `${label}は${maxLength}文字以内で入力してください。`;
  }

  return undefined;
}

function validateLines(value: string, label: string): string | undefined {
  const lines = toLines(value);

  if (lines.length > MAX_LIST_ITEMS) {
    return `${label}は${MAX_LIST_ITEMS}行までにしてください。`;
  }

  if (lines.some((line) => line.length > MAX_LIST_ITEM_LENGTH)) {
    return `${label}は1行${MAX_LIST_ITEM_LENGTH}文字以内で入力してください。`;
  }

  return undefined;
}

function validate(values: ExperienceFormValues): FieldErrors {
  const errors: FieldErrors = {
    title: validateRequiredText(values.title, 'タイトル', 100),
    place: validateRequiredText(values.place, '開催場所', 200),
    description: validateRequiredText(values.description, '体験の説明', 10000),
    cancelPolicy: validateRequiredText(values.cancelPolicy, 'キャンセルポリシー', 10000),
    flow: validateLines(values.flow, '当日の流れ'),
    belongings: validateLines(values.belongings, '持ち物'),
    notes: validateLines(values.notes, '注意事項'),
  };

  if (values.prefectureId === '') {
    errors.prefectureId = '開催地の都道府県を選んでください。';
  }

  if (!isWholeNumber(values.priceAdult)) {
    errors.priceAdult = '大人料金を半角数字（円）で入力してください。';
  }

  if (values.priceChild !== '' && !isWholeNumber(values.priceChild)) {
    errors.priceChild = '子ども料金は半角数字（円）で入力してください。';
  }

  if (values.ageCondition.trim().length > 50) {
    errors.ageCondition = '参加条件は50文字以内で入力してください。';
  }

  // undefined の項目は除く（エラーのある項目だけ残す）
  return Object.fromEntries(
    Object.entries(errors).filter(([, message]) => message !== undefined),
  ) as FieldErrors;
}

function toInput(
  values: ExperienceFormValues,
  imageKeys: string[],
  status: ExperienceWritableStatus,
): ExperienceInput {
  const optionalText = (value: string) =>
    value.trim() === '' ? null : value.trim();
  const optionalLines = (value: string) => {
    const lines = toLines(value);

    return lines.length === 0 ? null : lines;
  };

  return {
    title: values.title.trim(),
    prefectureId: Number(values.prefectureId),
    description: values.description.trim(),
    place: values.place.trim(),
    priceAdult: Number(values.priceAdult),
    priceChild: values.priceChild === '' ? null : Number(values.priceChild),
    ageCondition: optionalText(values.ageCondition),
    familyOk: values.familyOk,
    beginnerOk: values.beginnerOk,
    flow: optionalLines(values.flow),
    belongings: optionalLines(values.belongings),
    notes: optionalLines(values.notes),
    cancelPolicy: values.cancelPolicy.trim(),
    publishStatus: status,
    // 同じキーは送らない（API で重複不可）
    images: [...new Set(imageKeys)].map((imageKey) => ({ imageKey })),
  };
}

// API の項目名（images.0.imageKey など）を入力欄の名前にする
function toFormField(apiField: string): FieldName | null {
  const name = apiField.split(/[.[]/)[0];

  if (name === 'images' || name in initialValues) {
    return name as FieldName;
  }

  return null;
}

type DashboardExperienceFormProps = {
  // 編集する体験（渡さない場合は新規登録）
  experience?: DashboardExperience;
  // 保存処理（失敗時は ApiError を投げる）
  onSubmit: (input: ExperienceInput) => Promise<void>;
  cancelTo: string;
};

// 体験の入力フォーム（写真・基本情報・料金と参加条件・当日の案内）
// 新規登録は「下書きとして保存」「公開する」、編集は公開状態を選んで「変更を保存」
function DashboardExperienceForm({
  experience,
  onSubmit,
  cancelTo,
}: DashboardExperienceFormProps) {
  const isEdit = experience !== undefined;

  const [values, setValues] = useState<ExperienceFormValues>(() =>
    isEdit ? toFormValues(experience) : initialValues,
  );
  const [images, setImages] = useState<ImageItem[]>(() =>
    isEdit ? toImageItems(experience) : [],
  );
  // 編集時の公開状態（掲載停止中の体験は編集画面でフォームを出さない）
  const [publishStatus, setPublishStatus] = useState<ExperienceWritableStatus>(
    experience !== undefined && experience.publishStatus !== 'suspended'
      ? experience.publishStatus
      : 'draft',
  );
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<ExperienceWritableStatus | null>(
    null,
  );

  // 登録済みの画像と重ならないID から振る
  const nextImageId = useRef((experience?.images.length ?? 0) + 1);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // 画面を離れるときにプレビュー用URLを解放する
  const imagesRef = useRef(images);

  useEffect(() => {
    imagesRef.current = images;
  }, [images]);

  useEffect(
    () => () => {
      imagesRef.current.forEach(({ previewUrl }) => releasePreview(previewUrl));
    },
    [],
  );

  const setValue = <K extends keyof ExperienceFormValues>(
    name: K,
    value: ExperienceFormValues[K],
  ) => {
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
  };

  const updateImage = (localId: number, change: Partial<ImageItem>) => {
    setImages((current) =>
      current.map((image) =>
        image.localId === localId ? { ...image, ...change } : image,
      ),
    );
  };

  const handleFilesSelected = (event: ChangeEvent<HTMLInputElement>) => {
    const files = [...(event.target.files ?? [])];
    // 同じファイルを続けて選べるように空にする
    event.target.value = '';

    const remaining = MAX_IMAGES - images.length;
    const accepted = files.filter(
      (file) =>
        ACCEPTED_IMAGE_TYPES.includes(file.type) && file.size <= MAX_IMAGE_BYTES,
    );

    let message: string | undefined;

    if (accepted.length < files.length) {
      message = 'JPEG・PNG で 5MB 以下の写真だけ追加できます。';
    }

    if (accepted.length > remaining) {
      message = `写真は${MAX_IMAGES}枚まで登録できます。`;
    }

    setErrors((current) => ({ ...current, images: message }));

    accepted.slice(0, remaining).forEach((file) => {
      const localId = nextImageId.current++;

      setImages((current) => [
        ...current,
        {
          localId,
          previewUrl: URL.createObjectURL(file),
          status: 'uploading',
          key: null,
        },
      ]);

      uploadImage(file)
        .then(({ key }) => updateImage(localId, { status: 'done', key }))
        .catch(() => updateImage(localId, { status: 'error' }));
    });
  };

  const removeImage = (target: ImageItem) => {
    releasePreview(target.previewUrl);
    setImages((current) =>
      current.filter(({ localId }) => localId !== target.localId),
    );
  };

  const isUploading = images.some(({ status }) => status === 'uploading');
  const uploadedKeys = images.flatMap(({ status, key }) =>
    status === 'done' && key !== null ? [key] : [],
  );

  const submit = async (status: ExperienceWritableStatus) => {
    setFormError(null);

    if (images.some(({ status: s }) => s === 'error')) {
      setErrors((current) => ({
        ...current,
        images: 'アップロードに失敗した写真があります。削除してから、もう一度追加してください。',
      }));
      document.getElementById('experience-images')?.focus();
      return;
    }

    const nextErrors = validate(values);
    setErrors(nextErrors);

    const firstError = Object.keys(nextErrors)[0];

    if (firstError !== undefined) {
      setFormError('入力内容を確認してください。');
      document.getElementById(`experience-${firstError}`)?.focus();
      return;
    }

    setSubmitting(status);

    try {
      await onSubmit(toInput(values, uploadedKeys, status));
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

  // 1行1項目の入力欄（当日の流れ・持ち物・注意事項）
  const renderLinesField = (
    name: 'flow' | 'belongings' | 'notes',
    label: string,
    hint: string,
    placeholder: string,
  ) => {
    const id = `experience-${name}`;

    return (
      <Field id={id} label={label} hint={hint} error={errors[name]}>
        <textarea
          id={id}
          rows={5}
          placeholder={placeholder}
          value={values[name]}
          onChange={(event) => setValue(name, event.target.value)}
          aria-invalid={errors[name] !== undefined}
          aria-describedby={describedBy(id, true, errors[name])}
          className={`${controlClassName} ${controlBorder(errors[name])} resize-y`}
        />
      </Field>
    );
  };

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

      {isEdit && (
        <p className="m-0 box-border rounded-2xl border border-solid border-marche-line bg-marche-canvas p-4 text-xs leading-relaxed text-marche-muted">
          申込中・確定の予約がある体験は、トラブルを防ぐため、タイトル・説明・開催地・参加条件・当日の案内を変更できません。
          料金・キャンセルポリシーの変更は、これから申し込まれる予約にだけ適用されます。
        </p>
      )}

      <FormSection title="写真">
        <div>
          <p className="m-0 text-sm">
            {MAX_IMAGES}枚まで登録できます。1枚目が一覧に表示されるメインの写真になります。
          </p>
          <p className="m-0 text-xs text-marche-muted">JPEG・PNG、1枚 5MB まで。</p>
        </div>

        <ul className="m-0 grid list-none grid-cols-3 gap-3 p-0 sm:grid-cols-5">
          {images.map((image, index) => (
            <li key={image.localId} className="relative">
              <img
                src={image.previewUrl}
                alt={`写真${index + 1}`}
                className={`block aspect-square w-full rounded-xl bg-marche-sage object-cover ${image.status === 'done' ? '' : 'opacity-50'}`}
              />
              {index === 0 && (
                <span className="absolute top-1.5 left-1.5 rounded-full bg-marche-green px-2 py-0.5 text-xs font-bold text-white">
                  メイン
                </span>
              )}
              {image.status !== 'done' && (
                <span className="absolute inset-x-1.5 bottom-1.5 rounded-lg bg-white/90 px-1 py-0.5 text-center text-xs font-bold">
                  {image.status === 'uploading' ? 'アップロード中…' : (
                    <span className="text-marche-red">失敗しました</span>
                  )}
                </span>
              )}
              <button
                type="button"
                aria-label={`写真${index + 1}を削除`}
                disabled={image.status === 'uploading'}
                onClick={() => removeImage(image)}
                className="absolute top-1.5 right-1.5 box-border grid size-7 cursor-pointer place-items-center rounded-full border-0 bg-white/90 p-0 text-sm font-bold text-marche-ink font-[inherit] disabled:cursor-not-allowed disabled:opacity-50"
              >
                ×
              </button>
            </li>
          ))}

          {images.length < MAX_IMAGES && (
            <li>
              <button
                id="experience-images"
                type="button"
                onClick={() => fileInputRef.current?.click()}
                aria-describedby={errors.images === undefined ? undefined : 'experience-images-error'}
                className={`box-border flex aspect-square w-full cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed bg-marche-canvas p-0 text-sm font-bold text-marche-green font-[inherit] hover:bg-marche-sage ${errors.images === undefined ? 'border-marche-green/40' : 'border-marche-red'}`}
              >
                <PlusIcon />
                写真を追加
              </button>
            </li>
          )}
        </ul>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_IMAGE_TYPES.join(',')}
          multiple
          hidden
          onChange={handleFilesSelected}
        />
        {errors.images !== undefined && (
          <p
            id="experience-images-error"
            className="m-0 text-xs font-bold text-marche-red"
          >
            {errors.images}
          </p>
        )}
      </FormSection>

      <FormSection title="体験の情報">
        <Field id="experience-title" label="タイトル" required error={errors.title}>
          <input
            id="experience-title"
            type="text"
            maxLength={100}
            placeholder="例）蜜入りりんごの収穫体験とアップルパイづくり"
            value={values.title}
            onChange={(event) => setValue('title', event.target.value)}
            aria-invalid={errors.title !== undefined}
            aria-describedby={describedBy('experience-title', false, errors.title)}
            className={`${controlClassName} ${controlBorder(errors.title)}`}
          />
        </Field>

        <div className="grid gap-5 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)]">
          <Field
            id="experience-prefectureId"
            label="開催地（都道府県）"
            required
            error={errors.prefectureId}
          >
            <select
              id="experience-prefectureId"
              value={values.prefectureId}
              onChange={(event) => setValue('prefectureId', event.target.value)}
              aria-invalid={errors.prefectureId !== undefined}
              aria-describedby={describedBy('experience-prefectureId', false, errors.prefectureId)}
              className={`${controlClassName} ${controlBorder(errors.prefectureId)}`}
            >
              <option value="">選んでください</option>
              {PREFECTURES.map(({ id, name }) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </Field>

          <Field id="experience-place" label="開催場所" required error={errors.place}>
            <input
              id="experience-place"
              type="text"
              maxLength={200}
              placeholder="例）長野県 安曇野市（山本農園）"
              value={values.place}
              onChange={(event) => setValue('place', event.target.value)}
              aria-invalid={errors.place !== undefined}
              aria-describedby={describedBy('experience-place', false, errors.place)}
              className={`${controlClassName} ${controlBorder(errors.place)}`}
            />
          </Field>
        </div>

        <Field
          id="experience-description"
          label="体験の説明"
          required
          hint="どんな体験ができるか、見どころや魅力を書いてください。"
          error={errors.description}
        >
          <textarea
            id="experience-description"
            rows={6}
            maxLength={10000}
            value={values.description}
            onChange={(event) => setValue('description', event.target.value)}
            aria-invalid={errors.description !== undefined}
            aria-describedby={describedBy('experience-description', true, errors.description)}
            className={`${controlClassName} ${controlBorder(errors.description)} resize-y`}
          />
        </Field>
      </FormSection>

      <FormSection title="料金と参加条件">
        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            id="experience-priceAdult"
            label="大人料金（1人・税込）"
            required
            error={errors.priceAdult}
          >
            <div className="flex items-center gap-2">
              <input
                id="experience-priceAdult"
                type="text"
                inputMode="numeric"
                placeholder="3500"
                value={values.priceAdult}
                onChange={(event) => setValue('priceAdult', event.target.value)}
                aria-invalid={errors.priceAdult !== undefined}
                aria-describedby={describedBy('experience-priceAdult', false, errors.priceAdult)}
                className={`${controlClassName} ${controlBorder(errors.priceAdult)}`}
              />
              <span className="shrink-0 text-sm">円</span>
            </div>
          </Field>

          <Field
            id="experience-priceChild"
            label="子ども料金（1人・税込）"
            hint="空欄にすると、子どもは申し込めません。"
            error={errors.priceChild}
          >
            <div className="flex items-center gap-2">
              <input
                id="experience-priceChild"
                type="text"
                inputMode="numeric"
                placeholder="2000"
                value={values.priceChild}
                onChange={(event) => setValue('priceChild', event.target.value)}
                aria-invalid={errors.priceChild !== undefined}
                aria-describedby={describedBy('experience-priceChild', true, errors.priceChild)}
                className={`${controlClassName} ${controlBorder(errors.priceChild)}`}
              />
              <span className="shrink-0 text-sm">円</span>
            </div>
          </Field>
        </div>

        <Field
          id="experience-ageCondition"
          label="参加条件"
          hint="年齢などの条件があれば書いてください。"
          error={errors.ageCondition}
        >
          <input
            id="experience-ageCondition"
            type="text"
            maxLength={50}
            placeholder="例）小学生以上"
            value={values.ageCondition}
            onChange={(event) => setValue('ageCondition', event.target.value)}
            aria-invalid={errors.ageCondition !== undefined}
            aria-describedby={describedBy('experience-ageCondition', true, errors.ageCondition)}
            className={`${controlClassName} ${controlBorder(errors.ageCondition)}`}
          />
        </Field>

        <div className="flex flex-col gap-2">
          <CheckboxField
            id="experience-familyOk"
            label="家族で参加できる"
            description="チェックしない場合、子ども・未就学児は申し込めません。"
            checked={values.familyOk}
            onChange={(checked) => setValue('familyOk', checked)}
          />
          <CheckboxField
            id="experience-beginnerOk"
            label="初心者歓迎"
            description="はじめての方でも参加しやすい体験として表示します。"
            checked={values.beginnerOk}
            onChange={(checked) => setValue('beginnerOk', checked)}
          />
        </div>
      </FormSection>

      <FormSection title="当日の案内">
        {renderLinesField(
          'flow',
          '当日の流れ',
          `1行に1つずつ書いてください（${MAX_LIST_ITEMS}行まで）。`,
          '10:00 集合・農園の紹介\n10:20 りんごの収穫体験\n12:30 試食・解散',
        )}
        {renderLinesField(
          'belongings',
          '持ち物',
          '1行に1つずつ書いてください。',
          '汚れてもよい服装\n軍手\n飲み物',
        )}
        {renderLinesField(
          'notes',
          '注意事項',
          '雨天時の対応や駐車場など。1行に1つずつ書いてください。',
          '雨天の場合は収穫を中止します。\n駐車場は10台分あります。',
        )}

        <Field
          id="experience-cancelPolicy"
          label="キャンセルポリシー"
          required
          hint="キャンセル料がかかる時期と金額を書いてください。申込時にお客さまが同意します。"
          error={errors.cancelPolicy}
        >
          <textarea
            id="experience-cancelPolicy"
            rows={4}
            maxLength={10000}
            placeholder="例）開催日の3日前まではキャンセル無料です。2日前〜前日は参加費の50%、当日は100%のキャンセル料がかかります。"
            value={values.cancelPolicy}
            onChange={(event) => setValue('cancelPolicy', event.target.value)}
            aria-invalid={errors.cancelPolicy !== undefined}
            aria-describedby={describedBy('experience-cancelPolicy', true, errors.cancelPolicy)}
            className={`${controlClassName} ${controlBorder(errors.cancelPolicy)} resize-y`}
          />
        </Field>
      </FormSection>

      {isEdit && (
        <FormSection title="公開設定">
          <PublishStatusField
            options={publishStatusOptions}
            value={publishStatus}
            onChange={setPublishStatus}
          />
          <p className="m-0 text-xs text-marche-muted">
            公開しても、受付中の予約枠がないとお客さまは申し込めません。
          </p>
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

export default DashboardExperienceForm;
