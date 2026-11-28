import { useEffect, useState } from 'react';
import ApiError from '../api/apiError';

export function usePublicContent<T>(
  loader: (signal: AbortSignal) => Promise<T>,
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- 取得前に読み込み状態を初期化
    setData(null);
    setError('');
    setErrorStatus(null);
    setLoading(true);
    loader(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setData(value);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            cause instanceof Error
              ? cause.message
              : '情報を取得できませんでした。',
          );
          setErrorStatus(cause instanceof ApiError ? cause.status : null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [loader, version]);
  return {
    data,
    error,
    errorStatus,
    loading,
    retry: () => setVersion((value) => value + 1),
  };
}
