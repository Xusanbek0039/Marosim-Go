"use client";

import {
  Loader2Icon,
  MaximizeIcon,
  MinimizeIcon,
  PauseIcon,
  PlayIcon,
  RotateCcwIcon,
  RotateCwIcon,
  Volume2Icon,
  VolumeXIcon,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "./ui";

const SPEEDS = [0.5, 1, 1.25, 1.5, 2];

function clock(sec: number) {
  if (!Number.isFinite(sec) || sec < 0) return "0:00";
  const s = Math.floor(sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${r}` : `${m}:${r}`;
}

/**
 * Wedding-video player: big play button, scrubbable timeline with buffer, ±10 s, volume, speed,
 * fullscreen, keyboard (Space/K, ←/→, ↑/↓, F, M), controls that hide while playing.
 *
 * No download affordances when `allowDownload` is false: no native controls (so no "Save video"
 * menu), no context menu, no picture-in-picture, no drag. That only removes the easy paths — the
 * real protection is that such viewers are served the copy with the MarosimGo logo burned in.
 */
export function VideoPlayer({
  src,
  poster,
  allowDownload,
  autoPlay = true,
  onReady,
}: {
  src: string;
  poster?: string;
  allowDownload: boolean;
  autoPlay?: boolean;
  onReady?: () => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const bar = useRef<HTMLDivElement>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [playing, setPlaying] = useState(false);
  const [waiting, setWaiting] = useState(true);
  const [time, setTime] = useState(0);
  const [length, setLength] = useState(0);
  const [buffered, setBuffered] = useState(0);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [full, setFull] = useState(false);
  const [shown, setShown] = useState(true);
  const [failed, setFailed] = useState(false);
  const [scrub, setScrub] = useState<number | null>(null);

  const v = () => video.current;

  const reveal = useCallback(() => {
    setShown(true);
    if (hideTimer.current) clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => {
      if (v() && !v()!.paused) setShown(false);
    }, 2600);
  }, []);

  const toggle = useCallback(() => {
    const el = v();
    if (!el) return;
    if (el.paused) void el.play().catch(() => undefined);
    else el.pause();
    reveal();
  }, [reveal]);

  const seekBy = useCallback(
    (d: number) => {
      const el = v();
      if (!el) return;
      el.currentTime = Math.min(Math.max(0, el.currentTime + d), el.duration || 0);
      reveal();
    },
    [reveal],
  );

  const toggleFull = useCallback(() => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void box.current?.requestFullscreen?.().catch(() => undefined);
  }, []);

  const toggleMute = useCallback(() => {
    const el = v();
    if (!el) return;
    el.muted = !el.muted;
    if (!el.muted && el.volume === 0) el.volume = 0.6;
  }, []);

  useEffect(() => {
    const onFs = () => setFull(document.fullscreenElement === box.current);
    document.addEventListener("fullscreenchange", onFs);
    return () => document.removeEventListener("fullscreenchange", onFs);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input, textarea, select")) return;
      const k = e.key.toLowerCase();
      if (k === " " || k === "k") {
        e.preventDefault();
        toggle();
      } else if (k === "arrowright") {
        e.stopPropagation();
        seekBy(5);
      } else if (k === "arrowleft") {
        e.stopPropagation();
        seekBy(-5);
      } else if (k === "arrowup" || k === "arrowdown") {
        e.preventDefault();
        const el = v();
        if (el) el.volume = Math.min(1, Math.max(0, el.volume + (k === "arrowup" ? 0.1 : -0.1)));
        reveal();
      } else if (k === "f") toggleFull();
      else if (k === "m") toggleMute();
    };
    // capture: the gallery's ←/→ (next item) must not fire while the player handles seeking
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [toggle, seekBy, toggleFull, toggleMute, reveal]);

  const fraction = (clientX: number) => {
    const r = bar.current!.getBoundingClientRect();
    return Math.min(1, Math.max(0, (clientX - r.left) / r.width));
  };
  const onBarDown = (e: React.PointerEvent) => {
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    setScrub(fraction(e.clientX));
  };
  const onBarMove = (e: React.PointerEvent) => {
    if (scrub !== null) setScrub(fraction(e.clientX));
  };
  const onBarUp = (e: React.PointerEvent) => {
    if (scrub === null) return;
    const el = v();
    if (el && length) el.currentTime = fraction(e.clientX) * length;
    setScrub(null);
  };

  const shownTime = scrub !== null ? scrub * length : time;
  const progress = length ? (shownTime / length) * 100 : 0;
  const block = allowDownload ? undefined : (e: React.SyntheticEvent) => e.preventDefault();

  return (
    <div
      ref={box}
      onMouseMove={reveal}
      onTouchStart={reveal}
      onContextMenu={block}
      className={cn(
        "group/player relative flex max-h-full w-full max-w-6xl items-center justify-center overflow-hidden bg-black select-none",
        full ? "h-full rounded-none" : "aspect-video rounded-2xl",
        !shown && playing && "cursor-none",
      )}
    >
      <video
        ref={video}
        src={src}
        poster={poster}
        autoPlay={autoPlay}
        playsInline
        preload="metadata"
        controls={false}
        controlsList={allowDownload ? undefined : "nodownload noplaybackrate noremoteplayback"}
        disablePictureInPicture={!allowDownload}
        disableRemotePlayback={!allowDownload}
        draggable={false}
        onClick={toggle}
        onDoubleClick={toggleFull}
        onPlay={() => {
          setPlaying(true);
          reveal();
        }}
        onPause={() => {
          setPlaying(false);
          setShown(true);
        }}
        onWaiting={() => setWaiting(true)}
        onPlaying={() => setWaiting(false)}
        onCanPlay={() => setWaiting(false)}
        onLoadedData={() => onReady?.()}
        onLoadedMetadata={(e) => setLength(e.currentTarget.duration)}
        onDurationChange={(e) => setLength(e.currentTarget.duration)}
        onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
        onProgress={(e) => {
          const el = e.currentTarget;
          if (el.buffered.length && el.duration) setBuffered(el.buffered.end(el.buffered.length - 1) / el.duration);
        }}
        onVolumeChange={(e) => {
          setVolume(e.currentTarget.volume);
          setMuted(e.currentTarget.muted);
        }}
        onError={() => {
          setFailed(true);
          setWaiting(false);
          onReady?.();
        }}
        className="size-full object-contain"
      />

      {failed && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/80 p-6 text-center text-white">
          <p className="font-semibold">Videoni ochib bo&apos;lmadi.</p>
          <p className="text-sm text-white/70">Internet aloqasini tekshirib, qaytadan oching.</p>
        </div>
      )}

      {!failed && waiting && <Loader2Icon className="pointer-events-none absolute size-12 animate-spin text-white/70" aria-label="Yuklanmoqda" />}

      {!failed && !playing && !waiting && (
        <button
          type="button"
          onClick={toggle}
          aria-label="Ijro etish"
          className="absolute flex size-20 items-center justify-center rounded-full bg-white/90 text-blue-700 shadow-2xl transition hover:scale-105"
        >
          <PlayIcon className="ml-1 size-9 fill-current" />
        </button>
      )}

      {/* control bar */}
      <div
        className={cn(
          "absolute inset-x-0 bottom-0 flex flex-col gap-2 bg-gradient-to-t from-black/85 via-black/40 to-transparent px-3 pt-10 pb-3 text-white transition-opacity duration-300 sm:px-4",
          shown || !playing ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      >
        <div
          ref={bar}
          role="slider"
          tabIndex={0}
          aria-label="Vaqt"
          aria-valuemin={0}
          aria-valuemax={Math.round(length)}
          aria-valuenow={Math.round(shownTime)}
          aria-valuetext={clock(shownTime)}
          onPointerDown={onBarDown}
          onPointerMove={onBarMove}
          onPointerUp={onBarUp}
          className="group/bar relative h-4 cursor-pointer touch-none"
        >
          <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-white/25 transition-[height] group-hover/bar:h-1.5">
            <div className="absolute inset-y-0 left-0 rounded-full bg-white/35" style={{ width: `${buffered * 100}%` }} />
            <div className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400" style={{ width: `${progress}%` }} />
          </div>
          <div
            className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow transition-transform group-hover/bar:scale-125"
            style={{ left: `${progress}%` }}
          />
        </div>

        <div className="flex items-center gap-1 sm:gap-2">
          <IconButton label={playing ? "Pauza" : "Ijro etish"} onClick={toggle}>
            {playing ? <PauseIcon className="fill-current" /> : <PlayIcon className="fill-current" />}
          </IconButton>
          <IconButton label="10 soniya orqaga" onClick={() => seekBy(-10)}>
            <RotateCcwIcon />
          </IconButton>
          <IconButton label="10 soniya oldinga" onClick={() => seekBy(10)}>
            <RotateCwIcon />
          </IconButton>
          <div className="group/vol flex items-center">
            <IconButton label={muted ? "Ovozni yoqish" : "Ovozni o'chirish"} onClick={toggleMute}>
              {muted || volume === 0 ? <VolumeXIcon /> : <Volume2Icon />}
            </IconButton>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={muted ? 0 : volume}
              aria-label="Ovoz balandligi"
              onChange={(e) => {
                const el = v();
                if (!el) return;
                el.volume = Number(e.target.value);
                el.muted = el.volume === 0;
              }}
              className="hidden w-0 accent-cyan-400 transition-all group-hover/vol:w-20 sm:block"
            />
          </div>
          <span className="ml-1 text-xs font-semibold tabular-nums sm:text-sm">
            {clock(shownTime)} <span className="text-white/60">/ {clock(length)}</span>
          </span>
          <div className="ml-auto flex items-center gap-1">
            <button
              type="button"
              onClick={() => {
                const next = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length];
                setSpeed(next);
                if (v()) v()!.playbackRate = next;
              }}
              aria-label="Tezlik"
              className="h-9 min-w-12 rounded-lg px-2 text-xs font-bold tabular-nums hover:bg-white/15"
            >
              {speed}×
            </button>
            <IconButton label={full ? "To'liq ekrandan chiqish" : "To'liq ekran"} onClick={toggleFull}>
              {full ? <MinimizeIcon /> : <MaximizeIcon />}
            </IconButton>
          </div>
        </div>
      </div>
    </div>
  );
}

function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} title={label} className="inline-flex size-9 items-center justify-center rounded-lg hover:bg-white/15 [&_svg]:size-5">
      {children}
    </button>
  );
}
