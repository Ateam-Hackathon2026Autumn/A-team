import { useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';
import Button from './Button';
import { USE_MOCK } from '../../config/env';

export const fieldClass = 'box-border min-h-12 w-full rounded-xl border border-marche-line bg-white px-3 py-2 font-sans text-base text-marche-ink';
export const panelClass = 'rounded-2xl border border-marche-line bg-white p-5 sm:p-8';
export const linkClass = 'inline-flex min-h-11 items-center justify-center rounded-full border border-marche-green bg-marche-green px-6 py-2 text-center text-sm font-bold text-white no-underline hover:bg-marche-green-dark';
export const textLinkClass = 'inline-flex min-h-11 items-center font-bold text-marche-green underline underline-offset-4';
export const areas = ['すべての地域', '北海道', '東北', '関東', '中部', '近畿', '中国・四国', '九州・沖縄'];
export const yen = (value: number) => `¥${value.toLocaleString('ja-JP')}`;
export const dateLabel = (value: string) => new Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo', year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' }).format(new Date(value));
export const timeLabel = (value: string) => new Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo', hour: '2-digit', minute: '2-digit' }).format(new Date(value));

export function ContentPage({ eyebrow, title, intro, children }: { eyebrow: string; title: string; intro?: string; children: ReactNode }) {
  return <div className="mx-auto max-w-6xl px-5 py-8 sm:py-12">
    <Link to="/" className={textLinkClass}>ホーム</Link>
    <header className="mb-8 mt-4 border-b border-marche-line pb-8">
      <p className="m-0 text-xs font-bold tracking-[0.2em] text-marche-green">{eyebrow}</p>
      <h1 className="mb-3 mt-3 font-serif text-3xl leading-snug sm:text-4xl">{title}</h1>
      {intro && <p className="m-0 text-marche-muted">{intro}</p>}
    </header>
    {USE_MOCK && <p className="mb-6 rounded-xl bg-marche-sage px-4 py-3 text-sm text-marche-muted">デモ表示：掲載情報は架空です。申込・応募は動作確認用で、実際の予約・採用・決済・通知は行いません。</p>}
    {children}
  </div>;
}
export function ContentStatus({ loading, error, retry }: { loading: boolean; error: string; retry: () => void }) {
  if (loading) return <p role="status" className={panelClass}>読み込み中です…</p>;
  if (error) return <div role="alert" className={panelClass}><p className="text-marche-red">{error}</p><Button onClick={retry}>再読み込み</Button></div>;
  return null;
}
export function EmptyContent({ children }: { children: ReactNode }) {
  return <div role="status" className="rounded-2xl border border-dashed border-marche-line bg-marche-sage p-8 text-center">{children}</div>;
}
export function ContentImage({ src, alt, className = '' }: { src: string | null; alt: string; className?: string }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  return <div className={`overflow-hidden bg-marche-sage ${className}`}>
    {src && failedSrc !== src ? <img src={src} alt={alt} loading="lazy" className="block h-full w-full object-cover" onError={() => setFailedSrc(src)} /> : <span className="flex h-full items-center justify-center text-sm text-marche-muted">写真準備中</span>}
  </div>;
}
export function ContentSection({ title, text, items }: { title: string; text?: string | null; items?: string[] }) {
  if (!text && !items?.length) return null;
  return <section className="my-8"><h2 className="font-serif text-xl">{title}</h2>{text && <p className="whitespace-pre-line">{text}</p>}{items && <ul className="space-y-2 pl-5">{items.map((item, index) => <li key={index}>{item}</li>)}</ul>}</section>;
}
