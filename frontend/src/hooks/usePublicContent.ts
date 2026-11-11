import { useEffect, useState } from 'react';

export function usePublicContent<T>(loader: (signal: AbortSignal) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(''); setLoading(true);
    loader(controller.signal).then(value => {
      if (!controller.signal.aborted) setData(value);
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : '情報を取得できませんでした。');
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [loader, version]);
  return { data, error, loading, retry: () => setVersion(value => value + 1) };
}
