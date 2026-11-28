export const controlClassName =
  'box-border block w-full rounded-lg border border-solid bg-white px-3 py-2.5 text-base text-marche-ink [font-family:inherit]';

export function controlBorder(error: string | undefined) {
  return error === undefined ? 'border-marche-line' : 'border-marche-red';
}

// aria-describedby（補足とエラーを読み上げる）
export function describedBy(
  id: string,
  hint: boolean,
  error: string | undefined,
) {
  const ids = [
    hint ? `${id}-hint` : '',
    error !== undefined ? `${id}-error` : '',
  ]
    .filter(Boolean)
    .join(' ');

  return ids === '' ? undefined : ids;
}
