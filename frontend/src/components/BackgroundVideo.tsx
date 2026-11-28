import { PauseIcon, PlayIcon } from './Icons';
import type { VideoControl } from '../hooks/useBackgroundVideo';

export function BackgroundVideo({ control }: { control: VideoControl }) {
  const { attachVideo, shouldAutoPlay, onPlay, onPause, onError } = control;
  return (
    <video
      ref={attachVideo}
      className="pointer-events-none absolute inset-0 h-full w-full object-cover"
      autoPlay={shouldAutoPlay}
      muted
      loop
      playsInline
      preload="metadata"
      poster="/videos/home-hero-poster.jpg"
      aria-hidden="true"
      onPlay={onPlay}
      onPause={onPause}
    >
      <source src="/videos/home-hero.webm" type="video/webm" />
      <source src="/videos/home-hero.mp4" type="video/mp4" onError={onError} />
    </video>
  );
}

export function PlayPauseButton({
  control,
  className,
}: {
  control: VideoControl;
  className: string;
}) {
  return (
    <button
      type="button"
      onClick={control.toggle}
      aria-label={control.isPlaying ? '背景動画を一時停止' : '背景動画を再生'}
      className={className}
    >
      {control.isPlaying ? (
        <PauseIcon className="size-5" />
      ) : (
        <PlayIcon className="size-5" />
      )}
    </button>
  );
}
