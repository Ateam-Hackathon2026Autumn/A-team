import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react';
import { Link } from 'react-router';

import ApiError from '../../api/apiError';
import { uploadImage } from '../../api/uploadApi';
import {
  CheckboxField,
  Field,
  FormSection,
  controlBorder,
  controlClassName,
  describedBy,
} from '../DashboardFormParts';
import Button from '../ui/Button';
import { textLinkClass } from '../ui/ContentPage';
import type { ProducerGenre } from '../../types/dashboardProfile';
import type {
  MyProducerApplicationProducer,
  ProducerApplicationChanges,
  ProducerApplicationInput,
} from '../../types/producerApplication';
import { PREFECTURES } from '../../utils/prefectures';

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const IMAGE_TYPES = ['image/jpeg', 'image/png'];

export const PRODUCER_GENRE_LABELS: Record<ProducerGenre, string> = {
  agriculture: '農業',
  livestock: '畜産',
  fishery: '漁業',
};

type FormValues = {
  businessName: string;
  representativeName: string;
  genre: ProducerGenre;
  prefectureId: string;
  city: string;
  productionItems: string;
  intro: string;
  acceptsExperience: boolean;
  recruiting: boolean;
  careerStartYear: string;
  foundedYear: string;
  applicationReason: string;
};

type FieldName =
  | 'businessName'
  | 'representativeName'
  | 'genre'
  | 'prefectureId'
  | 'city'
  | 'productionItems'
  | 'intro'
  | 'acceptsExperience'
  | 'recruiting'
  | 'careerStartYear'
  | 'foundedYear'
  | 'profileImage'
  | 'coverImage'
  | 'applicationReason';

export type ProducerApplicationFormErrors = Partial<Record<FieldName, string>>;

type ImageItem = {
  localId: number;
  key: string | null;
  previewUrl: string;
  status: 'done' | 'uploading' | 'error';
};

let nextLocalId = 1;

function singleImage(key: string | null, url: string | null): ImageItem | null {
  if (key === null) return null;
  const fallbackUrl = `https://picsum.photos/seed/${encodeURIComponent(key)}/800/600`;
  return { localId: nextLocalId++, key, previewUrl: url ?? fallbackUrl, status: 'done' };
}

function releasePreview(item: ImageItem | null) {
  if (item !== null && item.previewUrl.startsWith('blob:')) {
    URL.revokeObjectURL(item.previewUrl);
  }
}

function toInitialFormValues(initialProducer?: MyProducerApplicationProducer): FormValues {
  if (!initialProducer) {
    return {
      businessName: '',
      representativeName: '',
      genre: 'agriculture',
      prefectureId: '',
      city: '',
      productionItems: '',
      intro: '',
      acceptsExperience: false,
      recruiting: false,
      careerStartYear: '',
      foundedYear: '',
      applicationReason: '',
    };
  }
  return {
    businessName: initialProducer.businessName,
    representativeName: initialProducer.representativeName,
    genre: initialProducer.genre,
    prefectureId: String(initialProducer.prefectureId),
    city: initialProducer.city,
    productionItems: initialProducer.productionItems,
    intro: initialProducer.intro,
    acceptsExperience: initialProducer.acceptsExperience,
    recruiting: initialProducer.recruiting,
    careerStartYear: initialProducer.careerStartYear === null ? '' : String(initialProducer.careerStartYear),
    foundedYear: initialProducer.foundedYear === null ? '' : String(initialProducer.foundedYear),
    applicationReason: initialProducer.applicationReason ?? '',
  };
}

const yearValue = (value: string) => (value.trim() === '' ? null : Number(value.trim()));

function yearError(value: string, label: string): string | undefined {
  const text = value.trim();
  if (text === '') return undefined;
  if (!/^\d{1,4}$/.test(text) || Number(text) < 1) return `${label}は西暦4桁までの数字で入力してください。`;
  if (Number(text) > new Date().getFullYear()) return `${label}は今年以前の年を入力してください。`;
  return undefined;
}

function validate(values: FormValues): ProducerApplicationFormErrors {
  const errors: ProducerApplicationFormErrors = {};
  if (values.businessName.trim() === '') errors.businessName = '事業者名を入力してください。';
  else if (values.businessName.trim().length > 100) errors.businessName = '事業者名は100文字以内で入力してください。';

  if (values.representativeName.trim() === '') errors.representativeName = '代表者名を入力してください。';
  else if (values.representativeName.trim().length > 100) {
    errors.representativeName = '代表者名は100文字以内で入力してください。';
  }

  if (!['agriculture', 'livestock', 'fishery'].includes(values.genre)) {
    errors.genre = '業種を選んでください。';
  }

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

const API_FIELD_TO_FORM: Record<string, FieldName> = {
  businessName: 'businessName',
  representativeName: 'representativeName',
  genre: 'genre',
  prefectureId: 'prefectureId',
  city: 'city',
  productionItems: 'productionItems',
  intro: 'intro',
  acceptsExperience: 'acceptsExperience',
  recruiting: 'recruiting',
  careerStartYear: 'careerStartYear',
  foundedYear: 'foundedYear',
  profileImage: 'profileImage',
  coverImage: 'coverImage',
  applicationReason: 'applicationReason',
};

function errorsFromDetails(details: Record<string, string[]>): ProducerApplicationFormErrors {
  const errors: ProducerApplicationFormErrors = {};
  Object.entries(details).forEach(([key, messages]) => {
    const field = API_FIELD_TO_FORM[key];
    if (field !== undefined && messages[0] !== undefined) {
      errors[field] = messages[0];
    }
  });
  return errors;
}

function fileError(file: File): string | null {
  if (!IMAGE_TYPES.includes(file.type)) return 'JPEG または PNG の画像を選んでください。';
  if (file.size > MAX_IMAGE_BYTES) return '画像は5MB以下にしてください。';
  return null;
}

function toInput(
  values: FormValues,
  profileImage: ImageItem | null,
  coverImage: ImageItem | null,
): ProducerApplicationInput {
  return {
    businessName: values.businessName.trim(),
    representativeName: values.representativeName.trim(),
    genre: values.genre,
    prefectureId: Number(values.prefectureId),
    city: values.city.trim(),
    productionItems: values.productionItems.trim(),
    intro: values.intro.trim(),
    acceptsExperience: values.acceptsExperience,
    recruiting: values.recruiting,
    careerStartYear: yearValue(values.careerStartYear),
    foundedYear: yearValue(values.foundedYear),
    profileImage: profileImage?.key ?? null,
    coverImage: coverImage?.key ?? null,
    applicationReason: values.applicationReason.trim() === '' ? null : values.applicationReason.trim(),
  };
}

function buildChanges(
  initial: MyProducerApplicationProducer,
  full: ProducerApplicationInput,
): ProducerApplicationChanges {
  const changes: ProducerApplicationChanges = {};
  if (full.businessName !== initial.businessName) changes.businessName = full.businessName;
  if (full.representativeName !== initial.representativeName) changes.representativeName = full.representativeName;
  if (full.genre !== initial.genre) changes.genre = full.genre;
  if (full.prefectureId !== initial.prefectureId) changes.prefectureId = full.prefectureId;
  if (full.city !== initial.city) changes.city = full.city;
  if (full.productionItems !== initial.productionItems) changes.productionItems = full.productionItems;
  if (full.intro !== initial.intro) changes.intro = full.intro;
  if (full.acceptsExperience !== initial.acceptsExperience) changes.acceptsExperience = full.acceptsExperience;
  if (full.recruiting !== initial.recruiting) changes.recruiting = full.recruiting;
  if ((full.careerStartYear ?? null) !== initial.careerStartYear) changes.careerStartYear = full.careerStartYear ?? null;
  if ((full.foundedYear ?? null) !== initial.foundedYear) changes.foundedYear = full.foundedYear ?? null;
  if ((full.profileImage ?? null) !== initial.profileImage) changes.profileImage = full.profileImage ?? null;
  if ((full.coverImage ?? null) !== initial.coverImage) changes.coverImage = full.coverImage ?? null;
  const reason = full.applicationReason ?? null;
  const initReason = initial.applicationReason ?? null;
  if (reason !== initReason) changes.applicationReason = reason;

  // 何も変更がない場合でも再申請できるよう、最低1項目（businessName）を含める
  if (Object.keys(changes).length === 0) {
    changes.businessName = full.businessName;
  }
  return changes;
}

function SingleImageUploadField({
  id,
  label,
  hint,
  item,
  error,
  shape,
  disabled,
  onSelect,
  onRemove,
}: {
  id: string;
  label: string;
  hint: string;
  item: ImageItem | null;
  error: string | undefined;
  shape: 'round' | 'wide';
  disabled: boolean;
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
          className={`relative shrink-0 overflow-hidden bg-marche-sage ${
            shape === 'round' ? 'size-24 rounded-full' : 'aspect-[2/1] w-full max-w-72 rounded-xl'
          }`}
        >
          {item !== null ? (
            <>
              <img
                src={item.previewUrl}
                alt={`${label}のプレビュー`}
                className={`block size-full object-cover ${item.status === 'done' ? '' : 'opacity-50'}`}
              />
              {item.status !== 'done' && (
                <span className="absolute inset-x-1.5 bottom-1.5 rounded-lg bg-white/90 px-1 py-0.5 text-center text-xs font-bold">
                  {item.status === 'uploading' ? (
                    'アップロード中…'
                  ) : (
                    <span className="text-marche-red">失敗しました</span>
                  )}
                </span>
              )}
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
          <Button
            variant="outline"
            disabled={disabled || item?.status === 'uploading'}
            onClick={() => inputRef.current?.click()}
          >
            {item === null ? '画像を選ぶ' : '変更する'}
          </Button>
          {item !== null && (
            <Button
              variant="outline"
              disabled={disabled || item.status === 'uploading'}
              onClick={onRemove}
            >
              外す
            </Button>
          )}
        </div>
      </div>
    </Field>
  );
}

type Props = {
  mode: 'create' | 'edit';
  initialProducer?: MyProducerApplicationProducer;
  reviewComment?: string | null;
  submitLabel: string;
  submittingLabel: string;
  cancelTo?: string;
  onSubmit: (
    fullInput: ProducerApplicationInput,
    changes: ProducerApplicationChanges,
  ) => Promise<void>;
};

export default function ProducerApplicationForm({
  mode,
  initialProducer,
  reviewComment,
  submitLabel,
  submittingLabel,
  cancelTo,
  onSubmit,
}: Props) {
  const [values, setValues] = useState<FormValues>(() => toInitialFormValues(initialProducer));
  const [profileImage, setProfileImage] = useState<ImageItem | null>(() =>
    singleImage(initialProducer?.profileImage ?? null, initialProducer?.profileImageUrl ?? null),
  );
  const [coverImage, setCoverImage] = useState<ImageItem | null>(() =>
    singleImage(initialProducer?.coverImage ?? null, initialProducer?.coverImageUrl ?? null),
  );
  const [errors, setErrors] = useState<ProducerApplicationFormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const errorSummaryRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (submitError !== null) {
      errorSummaryRef.current?.focus();
    }
  }, [submitError]);

  const isUploading = profileImage?.status === 'uploading' || coverImage?.status === 'uploading';

  const clearError = (field: FieldName) => {
    setErrors((current) => {
      if (current[field] === undefined) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

  const updateValue = <K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    setValues((current) => ({ ...current, [key]: value }));
    clearError(key as FieldName);
  };

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

  const showErrors = (nextErrors: ProducerApplicationFormErrors, message: string) => {
    setErrors(nextErrors);
    setSubmitError(null);
    window.setTimeout(() => setSubmitError(message), 0);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) return;

    if (isUploading) {
      showErrors({}, '画像のアップロードが終わるまでお待ちください。');
      return;
    }

    const failedErrors: ProducerApplicationFormErrors = {};
    const failedMsg = 'アップロードに失敗しました。もう一度選び直すか、外してください。';
    if (profileImage?.status === 'error') failedErrors.profileImage = failedMsg;
    if (coverImage?.status === 'error') failedErrors.coverImage = failedMsg;

    const clientErrors = { ...validate(values), ...failedErrors };
    if (Object.keys(clientErrors).length > 0) {
      showErrors(clientErrors, '入力内容を確認してください。');
      return;
    }

    setIsSubmitting(true);
    setErrors({});
    setSubmitError(null);

    const fullInput = toInput(values, profileImage, coverImage);
    const changes =
      mode === 'edit' && initialProducer
        ? buildChanges(initialProducer, fullInput)
        : fullInput;

    try {
      await onSubmit(fullInput, changes);
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        const fieldErrors = errorsFromDetails(error.details);
        const other = error.details.nonFieldErrors?.[0];
        showErrors(
          fieldErrors,
          Object.keys(fieldErrors).length > 0 ? '入力内容を確認してください。' : (other ?? error.message),
        );
      } else if (error instanceof ApiError) {
        showErrors({}, error.message);
      } else {
        showErrors({}, '通信に失敗しました。時間をおいて、もう一度お試しください。');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const errorEntries = Object.entries(errors).filter(([, message]) => message !== undefined);
  const control = (error: string | undefined) => `${controlClassName} ${controlBorder(error)}`;

  return (
    <form
      noValidate
      onSubmit={handleSubmit}
      aria-busy={isSubmitting}
      className="mt-6 flex max-w-3xl flex-col gap-6"
    >
      {reviewComment && (
        <div
          role="region"
          aria-label="運営からの確認コメント"
          className="box-border rounded-2xl border border-solid border-marche-orange bg-marche-orange/15 p-5 text-sm"
        >
          <p className="m-0 font-bold text-marche-ink">運営からのメッセージ（修正理由）</p>
          <p className="m-0 mt-2 whitespace-pre-line text-marche-ink">{reviewComment}</p>
        </div>
      )}

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
                  <a href={`#app-${key}`} className="text-marche-red">
                    {message}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <FormSection title="基本情報">
        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            id="app-businessName"
            label="事業者名（屋号・農園名）"
            required
            hint="例）山本農園（100文字まで）"
            error={errors.businessName}
          >
            <input
              id="app-businessName"
              type="text"
              maxLength={100}
              disabled={isSubmitting}
              aria-invalid={errors.businessName !== undefined}
              aria-describedby={describedBy('app-businessName', true, errors.businessName)}
              className={control(errors.businessName)}
              value={values.businessName}
              onChange={(event) => updateValue('businessName', event.target.value)}
            />
          </Field>

          <Field
            id="app-representativeName"
            label="代表者名"
            required
            hint="例）山本 健太（100文字まで）"
            error={errors.representativeName}
          >
            <input
              id="app-representativeName"
              type="text"
              maxLength={100}
              disabled={isSubmitting}
              aria-invalid={errors.representativeName !== undefined}
              aria-describedby={describedBy('app-representativeName', true, errors.representativeName)}
              className={control(errors.representativeName)}
              value={values.representativeName}
              onChange={(event) => updateValue('representativeName', event.target.value)}
            />
          </Field>
        </div>

        <Field id="app-genre" label="業種" required error={errors.genre}>
          <select
            id="app-genre"
            disabled={isSubmitting}
            aria-invalid={errors.genre !== undefined}
            aria-describedby={describedBy('app-genre', false, errors.genre)}
            className={control(errors.genre)}
            value={values.genre}
            onChange={(event) => updateValue('genre', event.target.value as ProducerGenre)}
          >
            {(Object.entries(PRODUCER_GENRE_LABELS) as [ProducerGenre, string][]).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field id="app-prefectureId" label="所在地の都道府県" required error={errors.prefectureId}>
            <select
              id="app-prefectureId"
              disabled={isSubmitting}
              aria-invalid={errors.prefectureId !== undefined}
              aria-describedby={describedBy('app-prefectureId', false, errors.prefectureId)}
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
            id="app-city"
            label="市区町村"
            required
            hint="公開されるのは市区町村までです（50文字まで）。"
            error={errors.city}
          >
            <input
              id="app-city"
              type="text"
              maxLength={50}
              disabled={isSubmitting}
              autoComplete="address-level2"
              aria-invalid={errors.city !== undefined}
              aria-describedby={describedBy('app-city', true, errors.city)}
              className={control(errors.city)}
              value={values.city}
              onChange={(event) => updateValue('city', event.target.value)}
            />
          </Field>
        </div>

        <Field
          id="app-productionItems"
          label="生産品目"
          required
          hint="例）りんご・ぶどう（100文字まで）"
          error={errors.productionItems}
        >
          <input
            id="app-productionItems"
            type="text"
            maxLength={100}
            disabled={isSubmitting}
            aria-invalid={errors.productionItems !== undefined}
            aria-describedby={describedBy('app-productionItems', true, errors.productionItems)}
            className={control(errors.productionItems)}
            value={values.productionItems}
            onChange={(event) => updateValue('productionItems', event.target.value)}
          />
        </Field>

        <Field
          id="app-intro"
          label="ひとこと紹介"
          required
          hint="生産者ページの名前の下に表示されます。"
          error={errors.intro}
        >
          <textarea
            id="app-intro"
            rows={4}
            disabled={isSubmitting}
            aria-invalid={errors.intro !== undefined}
            aria-describedby={describedBy('app-intro', true, errors.intro)}
            className={`${control(errors.intro)} min-h-28 resize-y leading-relaxed`}
            value={values.intro}
            onChange={(event) => updateValue('intro', event.target.value)}
          />
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            id="app-careerStartYear"
            label="この仕事を始めた年"
            hint="西暦（例：2022）。5年以内なら新規就農などの応援バッジが付きます。"
            error={errors.careerStartYear}
          >
            <input
              id="app-careerStartYear"
              type="text"
              inputMode="numeric"
              maxLength={4}
              disabled={isSubmitting}
              placeholder="例）2022"
              aria-invalid={errors.careerStartYear !== undefined}
              aria-describedby={describedBy('app-careerStartYear', true, errors.careerStartYear)}
              className={control(errors.careerStartYear)}
              value={values.careerStartYear}
              onChange={(event) => updateValue('careerStartYear', event.target.value)}
            />
          </Field>

          <Field
            id="app-foundedYear"
            label="創業年"
            hint="西暦（例：1962）。代々続く農園なら、事業を始めた年です。"
            error={errors.foundedYear}
          >
            <input
              id="app-foundedYear"
              type="text"
              inputMode="numeric"
              maxLength={4}
              disabled={isSubmitting}
              placeholder="例）1962"
              aria-invalid={errors.foundedYear !== undefined}
              aria-describedby={describedBy('app-foundedYear', true, errors.foundedYear)}
              className={control(errors.foundedYear)}
              value={values.foundedYear}
              onChange={(event) => updateValue('foundedYear', event.target.value)}
            />
          </Field>
        </div>
      </FormSection>

      <FormSection title="受け入れ・募集">
        <CheckboxField
          id="app-acceptsExperience"
          label="体験の受け入れ"
          description="生産者ページに「体験受け入れ中」のバッジが表示されます。"
          checked={values.acceptsExperience}
          onChange={(checked) => updateValue('acceptsExperience', checked)}
        />
        <CheckboxField
          id="app-recruiting"
          label="担い手の募集"
          description="生産者ページに「担い手募集中」のバッジが表示されます。"
          checked={values.recruiting}
          onChange={(checked) => updateValue('recruiting', checked)}
        />
      </FormSection>

      <FormSection title="写真（任意）">
        <SingleImageUploadField
          id="app-coverImage"
          label="カバー画像"
          hint="生産者ページのいちばん上に大きく表示されます（JPEG・PNG、5MBまで）。"
          item={coverImage}
          error={errors.coverImage}
          shape="wide"
          disabled={isSubmitting}
          onSelect={(file) => selectSingle('coverImage', setCoverImage, file)}
          onRemove={() => removeSingle('coverImage', setCoverImage)}
        />
        <SingleImageUploadField
          id="app-profileImage"
          label="プロフィール画像"
          hint="丸く切り抜いて表示されます（JPEG・PNG、5MBまで）。"
          item={profileImage}
          error={errors.profileImage}
          shape="round"
          disabled={isSubmitting}
          onSelect={(file) => selectSingle('profileImage', setProfileImage, file)}
          onRemove={() => removeSingle('profileImage', setProfileImage)}
        />
      </FormSection>

      <FormSection title="申請理由・自己紹介">
        <Field
          id="app-applicationReason"
          label="申請理由・自己紹介"
          hint="運営スタッフへの審査用メッセージです（公開されません）。"
          error={errors.applicationReason}
        >
          <textarea
            id="app-applicationReason"
            rows={4}
            disabled={isSubmitting}
            aria-invalid={errors.applicationReason !== undefined}
            aria-describedby={describedBy('app-applicationReason', true, errors.applicationReason)}
            className={`${control(errors.applicationReason)} min-h-28 resize-y leading-relaxed`}
            value={values.applicationReason}
            onChange={(event) => updateValue('applicationReason', event.target.value)}
          />
        </Field>
      </FormSection>

      <div className="flex flex-wrap items-center gap-4">
        <Button type="submit" disabled={isSubmitting || isUploading}>
          {isSubmitting ? submittingLabel : submitLabel}
        </Button>
        {cancelTo && (
          <Link to={cancelTo} className={textLinkClass}>
            キャンセルして戻る
          </Link>
        )}
      </div>
    </form>
  );
}
