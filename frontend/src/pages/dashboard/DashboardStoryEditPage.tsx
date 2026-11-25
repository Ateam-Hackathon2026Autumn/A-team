import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import { getDashboardStory, updateDashboardStory } from '../../api/dashboardStoryApi';
import DashboardButton from '../../components/DashboardButton';
import {
  Field,
  FormSection,
  PublishStatusField,
  controlBorder,
  controlClassName,
  describedBy,
  type PublishStatusOption,
} from '../../components/DashboardFormParts';
import { useSigninRedirect } from '../../hooks/useSigninRedirect';
import { userInfoAtom } from '../../stores/userAtom';
import type {
  DashboardStory,
  StoryEditableStatus,
  StoryInput,
  StoryPublishStatus,
  StoryTextField,
} from '../../types/dashboardStory';

// 生産者ストーリーの編集（学ぶページ・生産者プロフィールの応援ブロックに載る内容）
// 実API: GET・PUT /api/v1/dashboard/story（backend/api/views/dashboard/story.py）
// 画面の流れ: Notion「生産者のストーリー編集」（取得 → 入力 → 保存 → 完了トースト／400 は項目ごとに表示）
// レイアウト: 参考HTML（生産者管理のプロフィール編集。編集とプレビューを並べ、狭い画面では切り替え）

const MAX_TEXT = 2000;

type StoryFieldDefinition = {
  field: StoryTextField;
  label: string;
  hint: string;
  placeholder: string;
};

// 生産者ページの応援ブロックにも表示する3項目
const SUPPORT_FIELDS: StoryFieldDefinition[] = [
  {
    field: 'craft',
    label: '生産へのこだわり',
    hint: '生産者ページと商品詳細にも表示されます。',
    placeholder: '例）樹上でじっくり完熟させてから収穫しています。',
  },
  {
    field: 'reason',
    label: 'この仕事を始めた理由',
    hint: '生産者ページの「応援する」欄にも表示されます。',
    placeholder: '例）祖父の代から続く園地を、次の世代にも残したいと思い戻りました。',
  },
  {
    field: 'goal',
    label: 'これからの目標',
    hint: '生産者ページの「応援する」欄にも表示されます。',
    placeholder: '例）収穫体験を通じて、産地の担い手を増やしたい。',
  },
];

// 学ぶページだけに表示する3項目
const WORK_FIELDS: StoryFieldDefinition[] = [
  {
    field: 'method',
    label: '栽培・飼育・漁業の方法',
    hint: '育て方・獲り方の特徴を書きます。',
    placeholder: '例）草生栽培・減農薬（県基準の50%以下）で育てています。',
  },
  {
    field: 'process',
    label: '商品ができるまで',
    hint: '種まき・収穫から出荷までの流れを書きます。',
    placeholder: '例）春の摘花から秋の収穫まで、1本ずつ手作業で手入れしています。',
  },
  {
    field: 'environment',
    label: '環境への取り組み',
    hint: '土づくり・資源の循環など、環境のために続けていることを書きます。',
    placeholder: '例）刈り取った下草を土に戻し、化学肥料に頼らない土づくりを続けています。',
  },
];

const ALL_FIELDS = [...SUPPORT_FIELDS, ...WORK_FIELDS];

// プレビュー（お客さまに見える画面）での並び順
const PREVIEW_ORDER: StoryTextField[] = ['reason', 'craft', 'method', 'process', 'environment', 'goal'];

const STATUS_OPTIONS: PublishStatusOption<StoryEditableStatus>[] = [
  { value: 'draft', label: '下書き', description: 'お客さまには表示されません。書きかけのときに。' },
  {
    value: 'public',
    label: '公開',
    description: '学ぶページと生産者ページに表示されます（農園のプロフィールも公開中のとき）。',
  },
  { value: 'private', label: '非公開', description: '公開をやめて、お客さまに表示しないようにします。' },
];

const STATUS_LABELS: Record<StoryPublishStatus, string> = {
  draft: '下書き',
  public: '公開中',
  private: '非公開',
  suspended: '掲載停止中',
};

const STATUS_BADGE_CLASS: Record<StoryPublishStatus, string> = {
  draft: 'bg-marche-canvas text-marche-muted',
  public: 'bg-marche-sage text-marche-green',
  private: 'bg-marche-canvas text-marche-muted',
  suspended: 'bg-marche-red/10 text-marche-red',
};

type FormValues = Record<StoryTextField, string> & { publishStatus: StoryEditableStatus };
type FormErrors = Partial<Record<StoryTextField | 'publishStatus', string>>;

function toFormValues(story: DashboardStory): FormValues {
  return {
    craft: story.craft ?? '',
    method: story.method ?? '',
    process: story.process ?? '',
    environment: story.environment ?? '',
    reason: story.reason ?? '',
    goal: story.goal ?? '',
    // 掲載停止中は保存できないため、フォームの値としては使わない
    publishStatus: story.publishStatus === 'suspended' ? 'private' : story.publishStatus,
  };
}

// API に送る形（前後の空白を除き、空は null）
function toInput(values: FormValues): StoryInput {
  const text = (value: string) => (value.trim() === '' ? null : value.trim());

  return {
    craft: text(values.craft),
    method: text(values.method),
    process: text(values.process),
    environment: text(values.environment),
    reason: text(values.reason),
    goal: text(values.goal),
    publishStatus: values.publishStatus,
  };
}

function validate(values: FormValues): FormErrors {
  const errors: FormErrors = {};

  for (const { field, label } of ALL_FIELDS) {
    if (values[field].trim().length > MAX_TEXT) {
      errors[field] = `${label}は${MAX_TEXT.toLocaleString()}文字以内で入力してください。`;
    }
  }

  if (values.publishStatus === 'public' && ALL_FIELDS.every(({ field }) => values[field].trim() === '')) {
    errors.publishStatus = '公開するには本文を1項目以上入力してください。';
  }

  return errors;
}

// 400 の details（{ craft: ['...'] }）を項目ごとのメッセージにする
function errorsFromDetails(details: Record<string, string[]>): FormErrors {
  const errors: FormErrors = {};
  const keys: (StoryTextField | 'publishStatus')[] = [...ALL_FIELDS.map(({ field }) => field), 'publishStatus'];

  for (const key of keys) {
    const message = details[key]?.[0];

    if (message !== undefined) {
      errors[key] = message;
    }
  }

  return errors;
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

function labelOf(field: StoryTextField): string {
  return ALL_FIELDS.find((definition) => definition.field === field)?.label ?? field;
}

function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
      {children}
    </div>
  );
}

function StoryTextarea({
  definition,
  value,
  error,
  readOnly,
  onChange,
}: {
  definition: StoryFieldDefinition;
  value: string;
  error: string | undefined;
  readOnly: boolean;
  onChange: (value: string) => void;
}) {
  const id = `story-${definition.field}`;
  const length = value.trim().length;
  const isOver = length > MAX_TEXT;

  return (
    <Field id={id} label={definition.label} hint={definition.hint} error={error}>
      <textarea
        id={id}
        name={definition.field}
        rows={4}
        value={value}
        readOnly={readOnly}
        placeholder={definition.placeholder}
        aria-invalid={error !== undefined}
        aria-describedby={describedBy(id, true, error)}
        onChange={(event) => onChange(event.target.value)}
        className={`${controlClassName} ${controlBorder(error)} min-h-28 resize-y leading-relaxed read-only:bg-marche-canvas`}
      />
      <p
        className={`m-0 mt-1 text-right text-xs ${isOver ? 'font-bold text-marche-red' : 'text-marche-muted'}`}
      >
        {length.toLocaleString()} / {MAX_TEXT.toLocaleString()}文字
      </p>
    </Field>
  );
}

function StoryPreview({ values }: { values: FormValues }) {
  const sections = PREVIEW_ORDER.filter((field) => values[field].trim() !== '');
  const hasSupport = (['craft', 'reason', 'goal'] as const).some((field) => values[field].trim() !== '');

  return (
    <section
      aria-label="プレビュー"
      className="box-border overflow-hidden rounded-2xl border border-solid border-marche-line bg-marche-ivory xl:sticky xl:top-6"
    >
      <p className="m-0 bg-marche-ink px-4 py-2 text-xs font-bold text-white">
        プレビュー（お客さまに見える画面）
      </p>
      <div className="p-5">
        <p className="m-0 text-xs font-bold tracking-widest text-marche-green">STORY</p>
        {sections.length === 0 ? (
          <p className="m-0 mt-3 rounded-xl border border-dashed border-marche-line p-4 text-sm text-marche-muted">
            まだ何も書かれていません。入力した項目がここに表示されます。
          </p>
        ) : (
          sections.map((field) => (
            <div key={field} className="mt-4">
              <h3 className="m-0 font-serif text-base font-bold">{labelOf(field)}</h3>
              <p className="m-0 mt-1 text-sm leading-loose whitespace-pre-wrap [overflow-wrap:anywhere]">
                {values[field].trim()}
              </p>
            </div>
          ))
        )}
        {hasSupport && (
          <p className="m-0 mt-5 border-0 border-t border-solid border-marche-line pt-3 text-xs text-marche-muted">
            「生産へのこだわり」「この仕事を始めた理由」「これからの目標」は、公開すると生産者ページにも表示されます。
          </p>
        )}
      </div>
    </section>
  );
}

function DashboardStoryEditPage() {
  const redirectToSignin = useSigninRedirect();
  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、ストーリーのAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const [story, setStory] = useState<DashboardStory | null>(null);
  const [values, setValues] = useState<FormValues | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [reloadCount, setReloadCount] = useState(0);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  // 狭い画面での表示切り替え（広い画面では両方並べる）
  const [mobileView, setMobileView] = useState<'edit' | 'preview'>('edit');
  const errorSummaryRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!canManage) {
      return;
    }

    const controller = new AbortController();

    getDashboardStory(controller.signal)
      .then((result) => {
        setStory(result);
        setValues(toFormValues(result));
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        if (error instanceof ApiError && error.status === 401) {
          redirectToSignin();
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

  // エラーを出したら、その一覧へフォーカスを移す（読み上げにも伝わる）
  useEffect(() => {
    if (submitError !== null) {
      errorSummaryRef.current?.focus();
    }
  }, [submitError]);

  const isSuspended = story?.publishStatus === 'suspended';
  const isDirty =
    story !== null &&
    values !== null &&
    JSON.stringify(toInput(values)) !== JSON.stringify(toInput(toFormValues(story)));

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

  const reload = () => {
    setLoadError(false);
    setStory(null);
    setValues(null);
    setErrors({});
    setSubmitError(null);
    setReloadCount((count) => count + 1);
  };

  const updateValue = <K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    setValues((current) => (current === null ? current : { ...current, [key]: value }));
    setErrors((current) => {
      if (current[key] === undefined) {
        return current;
      }

      const next = { ...current };
      delete next[key];

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

    if (values === null || isSaving || isSuspended) {
      return;
    }

    const clientErrors = validate(values);

    if (Object.keys(clientErrors).length > 0) {
      showErrors(clientErrors, '入力内容を確認してください。');
      return;
    }

    setIsSaving(true);
    setErrors({});
    setSubmitError(null);

    // 送信した時点の入力。保存中も入力できるので、応答までに書き足された内容を消さないために使う
    const submittedValues = values;

    try {
      const saved = await updateDashboardStory(toInput(submittedValues));

      setStory(saved);
      // 送信後に入力が変わっていなければ、サーバーの値（前後の空白を除いたもの）にそろえる。
      // 変わっていれば入力をそのまま残し、「保存していない変更があります」と表示する
      setValues((current) => (current === submittedValues ? toFormValues(saved) : current));
      setToast(
        saved.publishStatus === 'public' ? 'ストーリーを保存して公開しました。' : 'ストーリーを保存しました。',
      );
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        redirectToSignin();
        return;
      }

      if (error instanceof ApiError && error.status === 400) {
        const fieldErrors = errorsFromDetails(error.details);

        showErrors(
          fieldErrors,
          Object.keys(fieldErrors).length > 0 ? '入力内容を確認してください。' : error.message,
        );
      } else if (error instanceof ApiError && error.errorCode === 'STORY_SUSPENDED') {
        // 運営が掲載を止めた。最新の状態（掲載停止中）を読み込み直して入力を止める
        showErrors({}, error.message);
        getDashboardStory()
          .then(setStory)
          .catch(() => {
            // 読み込めなくても、エラーメッセージで状況は伝わる
          });
      } else if (error instanceof ApiError) {
        // 409 PRODUCER_SUSPENDED などは、サーバーのメッセージをそのまま出す
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
      return <Notice>ストーリーの編集は、生産者登録が承認されると使えるようになります。</Notice>;
    }

    if (loadError) {
      return (
        <div
          role="alert"
          className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
        >
          <p className="m-0 font-bold text-marche-red">ストーリーを読み込めませんでした。</p>
          <p className="m-0 mt-1 text-marche-muted">時間をおいて、もう一度お試しください。</p>
          <DashboardButton variant="secondary" onClick={reload} className="mt-4">
            再読み込み
          </DashboardButton>
        </div>
      );
    }

    if (story === null || values === null) {
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

    const errorEntries = Object.entries(errors);

    return (
      <>
        <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <span
            className={`rounded-full px-3 py-0.5 text-xs font-bold ${STATUS_BADGE_CLASS[story.publishStatus]}`}
          >
            {STATUS_LABELS[story.publishStatus]}
          </span>
          <span className="text-marche-muted">
            {story.updatedAt === null ? 'まだ保存していません' : `最終保存：${dateTimeLabel(story.updatedAt)}`}
          </span>
          {isDirty && <span className="font-bold text-marche-orange">保存していない変更があります</span>}
        </div>

        {isSuspended && (
          <div
            role="alert"
            className="mb-5 box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
          >
            <p className="m-0 font-bold text-marche-red">このストーリーは運営により掲載停止中です。</p>
            <p className="m-0 mt-1 text-marche-muted">
              掲載停止中は内容を変更できません。くわしくは運営にお問い合わせください。
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
                        <a href={`#story-${key}`} className="text-marche-red">
                          {message}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <FormSection title="あなたについて">
              <p className="m-0 -mt-2 text-sm text-marche-muted">
                書ける項目からで大丈夫です。空の項目はお客さまに表示されません。
              </p>
              {SUPPORT_FIELDS.map((definition) => (
                <StoryTextarea
                  key={definition.field}
                  definition={definition}
                  value={values[definition.field]}
                  error={errors[definition.field]}
                  readOnly={isSuspended}
                  onChange={(value) => updateValue(definition.field, value)}
                />
              ))}
            </FormSection>

            <FormSection title="生産のこと">
              {WORK_FIELDS.map((definition) => (
                <StoryTextarea
                  key={definition.field}
                  definition={definition}
                  value={values[definition.field]}
                  error={errors[definition.field]}
                  readOnly={isSuspended}
                  onChange={(value) => updateValue(definition.field, value)}
                />
              ))}
            </FormSection>

            {!isSuspended && (
              <FormSection title="公開設定">
                <div id="story-publishStatus" tabIndex={-1} className="outline-none">
                  <PublishStatusField
                    options={STATUS_OPTIONS}
                    value={values.publishStatus}
                    onChange={(value) => updateValue('publishStatus', value)}
                  />
                  {errors.publishStatus !== undefined && (
                    <p className="m-0 mt-2 text-xs font-bold text-marche-red">{errors.publishStatus}</p>
                  )}
                </div>
              </FormSection>
            )}

            {!isSuspended && (
              <div className="flex flex-wrap items-center gap-3">
                <DashboardButton type="submit" disabled={isSaving} className="min-h-11 px-8">
                  {isSaving ? '保存中…' : values.publishStatus === 'public' ? '保存して公開' : '保存する'}
                </DashboardButton>
                {isDirty && (
                  <DashboardButton
                    variant="secondary"
                    disabled={isSaving}
                    onClick={() => {
                      setValues(toFormValues(story));
                      setErrors({});
                      setSubmitError(null);
                    }}
                    className="min-h-11"
                  >
                    変更を取り消す
                  </DashboardButton>
                )}
              </div>
            )}
          </form>

          <div className={`min-w-0 ${mobileView === 'preview' ? 'block' : 'hidden xl:block'}`}>
            <StoryPreview values={values} />
          </div>
        </div>
      </>
    );
  };

  return (
    <div>
      <h1 className="m-0 font-serif text-2xl font-bold">ストーリー編集</h1>
      <p className="m-0 mt-1 mb-6 text-sm text-marche-muted">
        学ぶページでお客さまに伝える、あなたと農園の物語です。
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

export default DashboardStoryEditPage;
