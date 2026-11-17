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
  Category,
  DashboardProduct,
  ProductCreateInput,
  ShippingSetting,
  TemperatureZone,
} from '../types/product';
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

// API の仕様に合わせた上限
const MAX_IMAGES = 10;
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png'];
const MAX_INT = 2147483647;

// 入力欄の値（数値も入力中は文字列で持つ）
type ProductFormValues = {
  name: string;
  volume: string;
  categoryId: string;
  shippingSettingId: string;
  price: string;
  taxRate: '8' | '10';
  discountRate: string;
  stock: string;
  description: string;
  method: string;
  isSubscription: boolean;
  isPreorder: boolean;
  acceptsDeliveryDate: boolean;
};

type FieldName = keyof ProductFormValues | 'images';
type FieldErrors = Partial<Record<FieldName, string>>;

// 画像1枚分（選んだ直後からアップロード完了まで）
type ImageItem = {
  // 画面内だけで使うID
  localId: number;
  previewUrl: string;
  status: 'uploading' | 'done' | 'error';
  key: string | null;
};

// 保存するときの公開状態
type SubmitStatus = 'draft' | 'public' | 'private';

const publishStatusOptions: PublishStatusOption<SubmitStatus>[] = [
  { value: 'public', label: '公開', description: 'お客さまの画面に表示し、購入できるようにします。' },
  { value: 'private', label: '非公開', description: 'お客さまの画面には表示しません。' },
  { value: 'draft', label: '下書き', description: '作成中として保存します。' },
];

const initialValues: ProductFormValues = {
  name: '',
  volume: '',
  categoryId: '',
  shippingSettingId: '',
  price: '',
  taxRate: '8',
  discountRate: '',
  stock: '',
  description: '',
  method: '',
  isSubscription: false,
  isPreorder: false,
  acceptsDeliveryDate: false,
};

// 編集時：登録済みの商品から入力欄の値を作る
function toFormValues(product: DashboardProduct): ProductFormValues {
  return {
    name: product.name,
    volume: product.volume,
    categoryId: String(product.categoryId),
    shippingSettingId: String(product.shippingSettingId),
    price: String(product.price),
    taxRate: product.taxRate === 10 ? '10' : '8',
    discountRate: product.discountRate === null ? '' : String(product.discountRate),
    stock: product.stock === null ? '' : String(product.stock),
    description: product.description ?? '',
    method: product.method ?? '',
    isSubscription: product.isSubscription,
    isPreorder: product.isPreorder,
    acceptsDeliveryDate: product.acceptsDeliveryDate,
  };
}

// 編集時：登録済みの画像（並び順どおり）
function toImageItems(product: DashboardProduct): ImageItem[] {
  return [...product.images]
    .sort((a, b) => a.sortOrder - b.sortOrder)
    .map((image, index) => ({
      localId: index + 1,
      previewUrl: image.url,
      status: 'done',
      key: image.key,
    }));
}

// 選んだファイルのプレビュー（blob:）だけ解放する。登録済みの画像の URL は対象外
function releasePreview(previewUrl: string) {
  if (previewUrl.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl);
  }
}

// API の項目名と入力欄の対応（400 の details を入力欄の下に出す）
const apiFieldToFormField: Record<string, FieldName> = {
  imageKeys: 'images',
};

const temperatureZoneLabels: Record<TemperatureZone, string> = {
  normal: '常温',
  chilled: '冷蔵',
  frozen: '冷凍',
};

const yenFormatter = new Intl.NumberFormat('ja-JP');

function formatYen(amount: number) {
  return `¥${yenFormatter.format(amount)}`;
}

function shippingLabel(setting: ShippingSetting) {
  const parts = [
    temperatureZoneLabels[setting.temperatureZone],
    `送料 ${formatYen(setting.shippingFee)}`,
    setting.leadTimeText,
  ];

  if (setting.freeShippingThreshold !== null) {
    parts.push(`${formatYen(setting.freeShippingThreshold)}以上で送料無料`);
  }

  return parts.join(' ・ ');
}

function isWholeNumber(value: string) {
  return /^\d+$/.test(value) && Number(value) <= MAX_INT;
}

// 割引後の販売価格（API の salePrice と同じ計算）
function calcSalePrice(values: ProductFormValues) {
  if (!isWholeNumber(values.price)) {
    return null;
  }

  const discount = isWholeNumber(values.discountRate)
    ? Number(values.discountRate)
    : 0;

  return Math.floor((Number(values.price) * (100 - discount)) / 100);
}

function validate(
  values: ProductFormValues,
  imageCount: number,
  status: SubmitStatus,
): FieldErrors {
  const errors: FieldErrors = {};
  const name = values.name.trim();
  const volume = values.volume.trim();

  if (name === '') {
    errors.name = '商品名を入力してください。';
  } else if (name.length > 100) {
    errors.name = '商品名は100文字以内で入力してください。';
  }

  if (volume === '') {
    errors.volume = '内容量を入力してください。';
  } else if (volume.length > 50) {
    errors.volume = '内容量は50文字以内で入力してください。';
  }

  if (values.categoryId === '') {
    errors.categoryId = 'カテゴリーを選んでください。';
  }

  if (values.shippingSettingId === '') {
    errors.shippingSettingId = '配送方法を選んでください。';
  }

  if (!isWholeNumber(values.price)) {
    errors.price = '価格を半角数字（円）で入力してください。';
  }

  if (
    values.discountRate !== '' &&
    (!isWholeNumber(values.discountRate) ||
      Number(values.discountRate) < 1 ||
      Number(values.discountRate) > 99)
  ) {
    errors.discountRate = '割引率は1〜99の半角数字で入力してください。';
  }

  if (values.stock !== '' && !isWholeNumber(values.stock)) {
    errors.stock = '在庫数は半角数字で入力してください。';
  }

  // 公開する場合の条件（API の仕様）
  if (status === 'public') {
    if (imageCount === 0) {
      errors.images = '公開するには写真が1枚以上必要です。';
    }

    if (values.description.trim() === '') {
      errors.description = '公開するには商品説明が必要です。';
    }

    if (values.stock === '') {
      errors.stock = '公開するには在庫数が必要です。';
    }

    const salePrice = calcSalePrice(values);

    if (errors.price === undefined && salePrice !== null && salePrice <= 0) {
      errors.price = '公開するには販売価格を1円以上にしてください。';
    }
  }

  return errors;
}

function toCreateInput(
  values: ProductFormValues,
  imageKeys: string[],
  status: SubmitStatus,
): ProductCreateInput {
  const optionalText = (value: string) =>
    value.trim() === '' ? null : value.trim();

  return {
    name: values.name.trim(),
    volume: values.volume.trim(),
    categoryId: Number(values.categoryId),
    shippingSettingId: Number(values.shippingSettingId),
    price: Number(values.price),
    taxRate: values.taxRate === '10' ? 10 : 8,
    discountRate: values.discountRate === '' ? null : Number(values.discountRate),
    description: optionalText(values.description),
    method: optionalText(values.method),
    isSubscription: values.isSubscription,
    isPreorder: values.isPreorder,
    acceptsDeliveryDate: values.acceptsDeliveryDate,
    publishStatus: status,
    // 同じキーは送らない（API で重複不可）
    imageKeys: [...new Set(imageKeys)],
    stock: values.stock === '' ? null : Number(values.stock),
  };
}

// ---------------------------------------------------------------------------
// フォーム本体
// ---------------------------------------------------------------------------

type DashboardProductFormProps = {
  // 編集する商品（渡さない場合は新規登録）
  product?: DashboardProduct;
  categories: Category[];
  shippingSettings: ShippingSetting[];
  // 登録処理（失敗時は ApiError を投げる）
  onSubmit: (input: ProductCreateInput) => Promise<void>;
  cancelTo: string;
};

// 商品の入力フォーム（写真・基本情報・価格と在庫・配送）
// 新規登録は「下書きとして保存」「公開する」、編集は公開状態を選んで「変更を保存」
function DashboardProductForm({
  product,
  categories,
  shippingSettings,
  onSubmit,
  cancelTo,
}: DashboardProductFormProps) {
  const isEdit = product !== undefined;

  const [values, setValues] = useState<ProductFormValues>(() =>
    isEdit ? toFormValues(product) : initialValues,
  );
  const [images, setImages] = useState<ImageItem[]>(() =>
    isEdit ? toImageItems(product) : [],
  );
  // 編集時の公開状態（掲載停止中の商品は編集画面でフォームを出さない）
  const [publishStatus, setPublishStatus] = useState<SubmitStatus>(
    product !== undefined && product.publishStatus !== 'suspended'
      ? product.publishStatus
      : 'draft',
  );
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<SubmitStatus | null>(null);

  // 登録済みの画像と重ならないID から振る
  const nextImageId = useRef((product?.images.length ?? 0) + 1);
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

  const setValue = <K extends keyof ProductFormValues>(
    name: K,
    value: ProductFormValues[K],
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
  const salePrice = calcSalePrice(values);

  const submit = async (status: SubmitStatus) => {
    setFormError(null);

    if (images.some(({ status: s }) => s === 'error')) {
      setErrors((current) => ({
        ...current,
        images: 'アップロードに失敗した写真があります。削除してから、もう一度追加してください。',
      }));
      document.getElementById('product-images')?.focus();
      return;
    }

    const nextErrors = validate(values, uploadedKeys.length, status);
    setErrors(nextErrors);

    const firstError = Object.keys(nextErrors)[0];

    if (firstError !== undefined) {
      setFormError('入力内容を確認してください。');
      document.getElementById(`product-${firstError}`)?.focus();
      return;
    }

    setSubmitting(status);

    try {
      await onSubmit(toCreateInput(values, uploadedKeys, status));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        window.location.replace('/signin');
        return;
      }

      if (error instanceof ApiError) {
        // 項目ごとのエラーは入力欄の下に出す
        const serverErrors: FieldErrors = {};

        Object.entries(error.details).forEach(([field, messages]) => {
          const formField = apiFieldToFormField[field] ?? field;

          if (formField in initialValues || formField === 'images') {
            serverErrors[formField as FieldName] = messages[0];
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

      <FormSection title="写真">
        <div>
          <p className="m-0 text-sm">
            {MAX_IMAGES}枚まで登録できます。1枚目が一覧に表示されるメインの写真になります。
          </p>
          <p className="m-0 text-xs text-marche-muted">
            JPEG・PNG、1枚 5MB まで。公開するには1枚以上必要です。
          </p>
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
                id="product-images"
                type="button"
                onClick={() => fileInputRef.current?.click()}
                aria-describedby={errors.images === undefined ? undefined : 'product-images-error'}
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
            id="product-images-error"
            className="m-0 text-xs font-bold text-marche-red"
          >
            {errors.images}
          </p>
        )}
      </FormSection>

      <FormSection title="商品の情報">
        <Field id="product-name" label="商品名" required error={errors.name}>
          <input
            id="product-name"
            type="text"
            maxLength={100}
            placeholder="例）安曇野ふじ 家庭用"
            value={values.name}
            onChange={(event) => setValue('name', event.target.value)}
            aria-invalid={errors.name !== undefined}
            aria-describedby={describedBy('product-name', false, errors.name)}
            className={`${controlClassName} ${controlBorder(errors.name)}`}
          />
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field id="product-volume" label="内容量" required error={errors.volume}>
            <input
              id="product-volume"
              type="text"
              maxLength={50}
              placeholder="例）5kg、10枚、2房"
              value={values.volume}
              onChange={(event) => setValue('volume', event.target.value)}
              aria-invalid={errors.volume !== undefined}
              aria-describedby={describedBy('product-volume', false, errors.volume)}
              className={`${controlClassName} ${controlBorder(errors.volume)}`}
            />
          </Field>

          <Field
            id="product-categoryId"
            label="カテゴリー"
            required
            error={errors.categoryId}
          >
            <select
              id="product-categoryId"
              value={values.categoryId}
              onChange={(event) => setValue('categoryId', event.target.value)}
              aria-invalid={errors.categoryId !== undefined}
              aria-describedby={describedBy('product-categoryId', false, errors.categoryId)}
              className={`${controlClassName} ${controlBorder(errors.categoryId)}`}
            >
              <option value="">選んでください</option>
              {categories.map(({ id, name }) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field
          id="product-description"
          label="商品説明"
          hint="味の特徴やおすすめの食べ方など。公開するには必要です。"
          error={errors.description}
        >
          <textarea
            id="product-description"
            rows={5}
            value={values.description}
            onChange={(event) => setValue('description', event.target.value)}
            aria-invalid={errors.description !== undefined}
            aria-describedby={describedBy('product-description', true, errors.description)}
            className={`${controlClassName} ${controlBorder(errors.description)} resize-y`}
          />
        </Field>

        <Field
          id="product-method"
          label="栽培・生産方法"
          hint="例）草生栽培・減農薬（県基準の50%以下）"
          error={errors.method}
        >
          <textarea
            id="product-method"
            rows={2}
            value={values.method}
            onChange={(event) => setValue('method', event.target.value)}
            aria-describedby={describedBy('product-method', true, errors.method)}
            className={`${controlClassName} ${controlBorder(errors.method)} resize-y`}
          />
        </Field>
      </FormSection>

      <FormSection title="価格・在庫">
        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            id="product-price"
            label="価格（税込・円）"
            required
            error={errors.price}
          >
            <input
              id="product-price"
              type="text"
              inputMode="numeric"
              placeholder="例）4800"
              value={values.price}
              onChange={(event) => setValue('price', event.target.value)}
              aria-invalid={errors.price !== undefined}
              aria-describedby={describedBy('product-price', false, errors.price)}
              className={`${controlClassName} ${controlBorder(errors.price)}`}
            />
          </Field>

          <fieldset className="m-0 min-w-0 border-0 p-0">
            <legend className="p-0 text-sm font-bold">
              税率
              <span className="ml-2 text-xs font-normal text-marche-red">
                必須
              </span>
            </legend>
            <div className="mt-2 flex gap-4 py-2.5">
              {(['8', '10'] as const).map((rate) => (
                <label
                  key={rate}
                  className="flex cursor-pointer items-center gap-2 text-sm"
                >
                  <input
                    type="radio"
                    name="taxRate"
                    value={rate}
                    checked={values.taxRate === rate}
                    onChange={() => setValue('taxRate', rate)}
                    className="m-0 size-4 accent-marche-green"
                  />
                  {rate}%{rate === '8' && '（食品）'}
                </label>
              ))}
            </div>
          </fieldset>

          <Field
            id="product-discountRate"
            label="割引率（%）"
            hint="割引しない場合は空欄"
            error={errors.discountRate}
          >
            <input
              id="product-discountRate"
              type="text"
              inputMode="numeric"
              placeholder="例）10"
              value={values.discountRate}
              onChange={(event) => setValue('discountRate', event.target.value)}
              aria-invalid={errors.discountRate !== undefined}
              aria-describedby={describedBy('product-discountRate', true, errors.discountRate)}
              className={`${controlClassName} ${controlBorder(errors.discountRate)}`}
            />
          </Field>

          <Field
            id="product-stock"
            label="在庫数"
            hint="公開するには必要です。0 は売り切れ。"
            error={errors.stock}
          >
            <input
              id="product-stock"
              type="text"
              inputMode="numeric"
              placeholder="例）40"
              value={values.stock}
              onChange={(event) => setValue('stock', event.target.value)}
              aria-invalid={errors.stock !== undefined}
              aria-describedby={describedBy('product-stock', true, errors.stock)}
              className={`${controlClassName} ${controlBorder(errors.stock)}`}
            />
          </Field>
        </div>

        {salePrice !== null && values.discountRate !== '' && errors.discountRate === undefined && (
          <p className="m-0 text-sm">
            販売価格（割引後）：
            <span className="font-bold">{formatYen(salePrice)}</span>
          </p>
        )}
      </FormSection>

      <FormSection title="配送">
        <Field
          id="product-shippingSettingId"
          label="配送方法"
          required
          error={errors.shippingSettingId}
        >
          <select
            id="product-shippingSettingId"
            value={values.shippingSettingId}
            onChange={(event) => setValue('shippingSettingId', event.target.value)}
            aria-invalid={errors.shippingSettingId !== undefined}
            aria-describedby={describedBy('product-shippingSettingId', false, errors.shippingSettingId)}
            className={`${controlClassName} ${controlBorder(errors.shippingSettingId)}`}
          >
            <option value="">選んでください</option>
            {shippingSettings.map((setting) => (
              <option key={setting.id} value={setting.id}>
                {shippingLabel(setting)}
              </option>
            ))}
          </select>
        </Field>

        <div className="flex flex-col gap-2">
          <CheckboxField
            id="product-acceptsDeliveryDate"
            label="お届け日の指定を受け付ける"
            description="購入するときに、お客さまがお届け日を選べるようになります。"
            checked={values.acceptsDeliveryDate}
            onChange={(checked) => setValue('acceptsDeliveryDate', checked)}
          />
          <CheckboxField
            id="product-isPreorder"
            label="予約商品"
            description="収穫前などで、発送が先になる商品です。"
            checked={values.isPreorder}
            onChange={(checked) => setValue('isPreorder', checked)}
          />
          <CheckboxField
            id="product-isSubscription"
            label="定期便"
            description="定期的にお届けする商品として表示します。"
            checked={values.isSubscription}
            onChange={(checked) => setValue('isSubscription', checked)}
          />
        </div>
      </FormSection>

      {isEdit && (
        <FormSection title="公開設定">
          <PublishStatusField
            options={publishStatusOptions}
            value={publishStatus}
            onChange={setPublishStatus}
          />
        </FormSection>
      )}

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-end">
        <DashboardButton to={cancelTo} variant="secondary">
          キャンセル
        </DashboardButton>
        {isEdit ? (
          <DashboardButton
            type="submit"
            disabled={submitting !== null || isUploading}
          >
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

export default DashboardProductForm;
