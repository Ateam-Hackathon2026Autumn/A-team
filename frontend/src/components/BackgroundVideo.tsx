import { useEffect, useRef, useState } from "react";
import { PauseIcon, PlayIcon } from "./Icons";

export function useBackgroundVideo(enabled = true) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [shouldAutoPlay] = useState(() => typeof window === "undefined" || typeof window.matchMedia !== "function" || !window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setIsPlaying(false);
      return;
    }
    if (typeof window.matchMedia !== "function") return;
    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const pauseForReducedMotion = (event: MediaQueryListEvent) => {
      if (event.matches) videoRef.current?.pause();
    };
    motionPreference.addEventListener("change", pauseForReducedMotion);
    return () => motionPreference.removeEventListener("change", pauseForReducedMotion);
  }, [enabled]);

  const toggle = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) void video.play().catch(() => setIsPlaying(false));
    else video.pause();
  };

  return {
    videoRef,
    shouldAutoPlay,
    isPlaying,
    toggle,
    onPlay: () => setIsPlaying(true),
    onPause: () => setIsPlaying(false),
    onError: () => setIsPlaying(false),
  };
}

type VideoControl = ReturnType<typeof useBackgroundVideo>;

export function BackgroundVideo({ control }: { control: VideoControl }) {
  return <video ref={control.videoRef} className="pointer-events-none absolute inset-0 h-full w-full object-cover" autoPlay={control.shouldAutoPlay} muted loop playsInline preload="metadata" poster="/videos/home-hero-poster.jpg" aria-hidden="true" onPlay={control.onPlay} onPause={control.onPause}><source src="/videos/home-hero.webm" type="video/webm" /><source src="/videos/home-hero.mp4" type="video/mp4" onError={control.onError} /></video>;
}

export function PlayPauseButton({ control, className }: { control: VideoControl; className: string }) {
  return <button type="button" onClick={control.toggle} aria-label={control.isPlaying ? "背景動画を一時停止" : "背景動画を再生"} className={className}>{control.isPlaying ? <PauseIcon className="size-5" /> : <PlayIcon className="size-5" />}</button>;
}
