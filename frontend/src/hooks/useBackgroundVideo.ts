import { useCallback, useEffect, useRef, useState } from 'react';

export type VideoControl = {
  attachVideo: (node: HTMLVideoElement | null) => void;
  shouldAutoPlay: boolean;
  isPlaying: boolean;
  toggle: () => void;
  onPlay: () => void;
  onPause: () => void;
  onError: () => void;
};

export function useBackgroundVideo(enabled = true): VideoControl {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [shouldAutoPlay] = useState(
    () =>
      typeof window === 'undefined' ||
      typeof window.matchMedia !== 'function' ||
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );
  const [isPlaying, setIsPlaying] = useState(false);
  const [previousEnabled, setPreviousEnabled] = useState(enabled);
  if (previousEnabled !== enabled) {
    setPreviousEnabled(enabled);
    if (!enabled) setIsPlaying(false);
  }

  useEffect(() => {
    if (!enabled) return;
    if (typeof window.matchMedia !== 'function') return;
    const motionPreference = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    );
    const pauseForReducedMotion = (event: MediaQueryListEvent) => {
      if (event.matches) videoRef.current?.pause();
    };
    motionPreference.addEventListener('change', pauseForReducedMotion);
    return () =>
      motionPreference.removeEventListener('change', pauseForReducedMotion);
  }, [enabled]);

  const toggle = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) void video.play().catch(() => setIsPlaying(false));
    else video.pause();
  };

  const attachVideo = useCallback((node: HTMLVideoElement | null) => {
    videoRef.current = node;
  }, []);

  return {
    attachVideo,
    shouldAutoPlay,
    isPlaying,
    toggle,
    onPlay: () => setIsPlaying(true),
    onPause: () => setIsPlaying(false),
    onError: () => setIsPlaying(false),
  };
}
