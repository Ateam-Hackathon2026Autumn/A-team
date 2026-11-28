export const fieldClass =
  'box-border min-h-12 w-full rounded-xl border border-marche-line bg-white px-3 py-2 font-sans text-base text-marche-ink';
export const panelClass =
  'rounded-2xl border border-marche-line bg-white p-5 sm:p-8';
export const linkClass =
  'inline-flex min-h-11 items-center justify-center rounded-full border border-marche-green bg-marche-green px-6 py-2 text-center text-sm font-bold text-white no-underline hover:bg-marche-green-dark';
export const textLinkClass =
  'inline-flex min-h-11 items-center font-bold text-marche-green underline underline-offset-4';
export const areas = [
  'すべての地域',
  '北海道',
  '東北',
  '関東',
  '中部',
  '近畿',
  '中国・四国',
  '九州・沖縄',
];
export const yen = (value: number) => `¥${value.toLocaleString('ja-JP')}`;
export const dateLabel = (value: string) =>
  new Intl.DateTimeFormat('ja-JP', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(new Date(value));
export const timeLabel = (value: string) =>
  new Intl.DateTimeFormat('ja-JP', {
    timeZone: 'Asia/Tokyo',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
