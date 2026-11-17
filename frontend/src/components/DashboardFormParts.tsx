import type { ReactNode } from 'react';

// 生産者管理画面の入力フォームで共通に使う部品（商品・体験など）

const controlClassName =
  'box-border block w-full rounded-lg border border-solid bg-white px-3 py-2.5 text-base text-marche-ink [font-family:inherit]';

function controlBorder(error: string | undefined) {
  return error === undefined ? 'border-marche-line' : 'border-marche-red';
}

type FieldProps = {
  id: string;
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: ReactNode;
};

function Field({ id, label, required = false, hint, error, children }: FieldProps) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-bold">
        {label}
        <span
          className={`ml-2 text-xs font-normal ${required ? 'text-marche-red' : 'text-marche-muted'}`}
        >
          {required ? '必須' : '任意'}
        </span>
      </label>
      {hint !== undefined && (
        <p id={`${id}-hint`} className="m-0 mt-1 text-xs text-marche-muted">
          {hint}
        </p>
      )}
      <div className="mt-2">{children}</div>
      {error !== undefined && (
        <p
          id={`${id}-error`}
          className="m-0 mt-1 text-xs font-bold text-marche-red"
        >
          {error}
        </p>
      )}
    </div>
  );
}

// aria-describedby（補足とエラーを読み上げる）
function describedBy(id: string, hint: boolean, error: string | undefined) {
  const ids = [hint ? `${id}-hint` : '', error !== undefined ? `${id}-error` : '']
    .filter(Boolean)
    .join(' ');

  return ids === '' ? undefined : ids;
}

function FormSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="box-border flex flex-col gap-5 rounded-2xl border border-solid border-marche-line bg-white p-5 md:p-6">
      <h2 className="m-0 font-serif text-lg font-bold">{title}</h2>
      {children}
    </section>
  );
}

function CheckboxField({
  id,
  label,
  description,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-start gap-3 rounded-xl bg-marche-canvas px-4 py-3"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="m-0 mt-1 size-4 shrink-0 accent-marche-green"
      />
      <span>
        <span className="block text-sm font-bold">{label}</span>
        <span className="block text-xs text-marche-muted">{description}</span>
      </span>
    </label>
  );
}

// 公開状態の選択肢（編集画面で使う）
type PublishStatusOption<T extends string> = {
  value: T;
  label: string;
  description: string;
};

function PublishStatusField<T extends string>({
  options,
  value,
  onChange,
}: {
  options: PublishStatusOption<T>[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <fieldset className="m-0 min-w-0 border-0 p-0">
      <legend className="sr-only">公開状態</legend>
      <div className="flex flex-col gap-2">
        {options.map((option) => (
          <label
            key={option.value}
            className={`box-border flex cursor-pointer items-start gap-3 rounded-xl border border-solid px-4 py-3 ${value === option.value ? 'border-marche-green bg-marche-sage' : 'border-marche-line bg-white'}`}
          >
            <input
              type="radio"
              name="publishStatus"
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="m-0 mt-1 size-4 shrink-0 accent-marche-green"
            />
            <span>
              <span className="block text-sm font-bold">{option.label}</span>
              <span className="block text-xs text-marche-muted">
                {option.description}
              </span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export {
  CheckboxField,
  Field,
  FormSection,
  PublishStatusField,
  controlBorder,
  controlClassName,
  describedBy,
};
export type { PublishStatusOption };
