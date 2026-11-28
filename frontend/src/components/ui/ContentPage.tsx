import { useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';
import Button from './Button';
import { USE_MOCK } from '../../config/env';
import { linkClass, panelClass, textLinkClass } from './contentPageValues';

export function ContentPage({
  eyebrow,
  title,
  intro,
  children,
}: {
  eyebrow: string;
  title: string;
  intro?: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-6xl px-5 py-8 sm:py-12">
      <Link to="/" className={textLinkClass}>
        ホーム
      </Link>
      <header className="mb-8 mt-4 border-b border-marche-line pb-8">
        <p className="m-0 text-xs font-bold tracking-[0.2em] text-marche-green">
          {eyebrow}
        </p>
        <h1 className="mb-3 mt-3 font-serif text-3xl leading-snug sm:text-4xl">
          {title}
        </h1>
        {intro && <p className="m-0 text-marche-muted">{intro}</p>}
      </header>
      {USE_MOCK && (
        <p className="mb-6 rounded-xl bg-marche-sage px-4 py-3 text-sm text-marche-muted">
          デモ表示：掲載情報は架空です。申込・応募は動作確認用で、実際の予約・採用・決済・通知は行いません。
        </p>
      )}
      {children}
    </div>
  );
}
export function ContentStatus({
  loading,
  error,
  retry,
  errorStatus,
  notFoundTo,
}: {
  loading: boolean;
  error: string;
  retry: () => void;
  errorStatus?: number | null;
  notFoundTo?: string;
}) {
  if (loading)
    return (
      <p role="status" className={panelClass}>
        読み込み中です…
      </p>
    );
  if (error)
    return (
      <div role="alert" className={panelClass}>
        <p className="text-marche-red">{error}</p>
        {errorStatus === 404 && notFoundTo ? (
          <Link to={notFoundTo} className={linkClass}>
            一覧へ戻る
          </Link>
        ) : (
          <Button onClick={retry}>再読み込み</Button>
        )}
      </div>
    );
  return null;
}
export function EmptyContent({ children }: { children: ReactNode }) {
  return (
    <div
      role="status"
      className="rounded-2xl border border-dashed border-marche-line bg-marche-sage p-8 text-center"
    >
      {children}
    </div>
  );
}
export function ContentImage({
  src,
  alt,
  className = '',
}: {
  src: string | null;
  alt: string;
  className?: string;
}) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  return (
    <div className={`overflow-hidden bg-marche-sage ${className}`}>
      {src && failedSrc !== src ? (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          className="block h-full w-full object-cover"
          onError={() => setFailedSrc(src)}
        />
      ) : (
        <span className="flex h-full items-center justify-center text-sm text-marche-muted">
          写真準備中
        </span>
      )}
    </div>
  );
}
export function ContentSection({
  title,
  text,
  items,
}: {
  title: string;
  text?: string | null;
  items?: string[] | { time: string; text: string }[] | null;
}) {
  if (!text && !items?.length) return null;
  return (
    <section className="my-8">
      <h2 className="font-serif text-xl">{title}</h2>
      {text && <p className="whitespace-pre-line">{text}</p>}
      {items && (
        <ul className="space-y-2 pl-5">
          {items.map((item, index) => (
            <li key={index}>
              {typeof item === 'string' ? (
                item
              ) : (
                <>
                  <time dateTime={item.time} className="font-bold">
                    {item.time}
                  </time>{' '}
                  {item.text}
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
