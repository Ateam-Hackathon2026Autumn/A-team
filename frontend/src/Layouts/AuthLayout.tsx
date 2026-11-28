import { useEffect, useState } from 'react';
import { Outlet } from 'react-router';
import { USE_MOCK } from '../config/env';
import {
  BackgroundVideo,
  PlayPauseButton,
} from '../components/BackgroundVideo';
import { useBackgroundVideo } from '../hooks/useBackgroundVideo';

export default function AuthLayout() {
  const [showVideo, setShowVideo] = useState(
    () =>
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(min-width: 48rem)').matches,
  );
  const video = useBackgroundVideo(showVideo);

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const viewport = window.matchMedia('(min-width: 48rem)');
    const updateViewport = (event: MediaQueryListEvent) =>
      setShowVideo(event.matches);
    viewport.addEventListener('change', updateViewport);
    return () => viewport.removeEventListener('change', updateViewport);
  }, []);

  return (
    <div className="px-4 py-8 sm:px-6 lg:py-14">
      <div className="mx-auto grid max-w-[1060px] overflow-hidden rounded-3xl border border-marche-line bg-white md:grid-cols-[0.8fr_1.2fr]">
        <aside className="relative isolate hidden min-h-[700px] flex-col justify-between overflow-hidden bg-marche-green-dark px-6 py-12 text-white md:flex lg:px-9">
          {showVideo && <BackgroundVideo control={video} />}
          <div
            aria-hidden="true"
            className="absolute inset-0"
            style={{
              background:
                'linear-gradient(to bottom, rgb(36 85 62 / 0.9) 0px, rgb(36 85 62 / 0.9) 280px, rgb(36 85 62 / 0.15) 340px, rgb(36 85 62 / 0.15) calc(100% - 190px), rgb(36 85 62 / 0.9) calc(100% - 150px), rgb(36 85 62 / 0.9) 100%)',
            }}
          />
          <div
            className="relative z-10"
            style={{ textShadow: '0 1px 3px rgb(0 0 0 / 0.45)' }}
          >
            <p className="m-0 text-xs font-bold tracking-[0.18em] text-white/80">
              A NEW CONNECTION
            </p>

            <h2 className="m-0 font-serif mt-6 text-2xl font-bold leading-relaxed lg:text-3xl">
              つくる人を知る。
              <br />
              暮らしが、変わる。
            </h2>

            <p className="m-0 mt-5 text-sm leading-8 text-white/80">
              おいしい出会いも、新しい挑戦も。
              <br />
              あなたと産地をつなぐ場所へ。
            </p>
          </div>

          <div
            className="relative z-10 flex flex-col items-start gap-3"
            style={{ textShadow: '0 1px 3px rgb(0 0 0 / 0.45)' }}
          >
            <p className="m-0 text-sm text-white/80">
              買う ・ 体験する ・ 働く ・ 学ぶ
            </p>
            <PlayPauseButton
              control={video}
              className="grid min-h-11 min-w-11 cursor-pointer place-items-center rounded-full border border-white/70 bg-marche-green-dark p-2 text-white"
            />
          </div>
        </aside>

        <section
          aria-label="アカウント手続き"
          className="min-w-0 px-5 py-8 sm:px-8 lg:px-12 lg:py-10"
        >
          <Outlet />
        </section>
      </div>

      {USE_MOCK && (
        <p className="m-0 mx-auto mt-5 max-w-3xl text-center text-xs leading-6 text-marche-muted">
          画面確認用デモです。APIは未接続です。
          実際の個人情報や普段使うパスワードは入力しないでください。
        </p>
      )}
    </div>
  );
}
