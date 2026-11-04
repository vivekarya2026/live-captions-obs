import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronLeft, ChevronRight, Music, Square } from "lucide-react";
import { Button } from "../ui/Button";
import { engineGet, type SongModeState } from "../../hooks/useEngine";

/** Small keyboard hint on a button (review fix H5). */
const Key: React.FC<{ k: string }> = ({ k }) => (
  <kbd className="ms-1.5 px-1 rounded border border-line text-[10px] text-ink-3 font-sans">
    {k}
  </kbd>
);

const typing = (e: KeyboardEvent) => {
  const el = e.target as HTMLElement | null;
  return (
    !!el &&
    (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName))
  );
};

/**
 * Song mode on the Live Captions page (docs/song-mode/04-prototype.md, 3c):
 * the status chip, the "Sounds like" card, and the Now singing bar.
 */
export const NowSinging: React.FC<{
  s: SongModeState | undefined;
  onOpenSongs?: () => void;
  onChanged: () => void;
}> = ({ s, onOpenSongs, onChanged }) => {
  const { t } = useTranslation();
  const [picking, setPicking] = useState(false);
  const call = async (path: string) => {
    await engineGet(path);
    onChanged();
  };
  const state = s?.state;
  const active = state === "following" || state === "lost";

  // ← → Esc while a song is shown (not while typing in a field).
  useEffect(() => {
    if (!active && state !== "suggested") return;
    const onKey = (e: KeyboardEvent) => {
      if (typing(e) || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "ArrowRight") call("/songs/next");
      else if (e.key === "ArrowLeft" && active) call("/songs/back");
      else if (e.key === "Escape") call(active ? "/songs/stop" : "/songs/reject");
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, state]);

  useEffect(() => {
    if (state !== "suggested") setPicking(false);
  }, [state]);

  if (!s) return null;

  // Status chip (review fix H1): always shows whether Song mode is listening.
  const chipText = !s.on
    ? t("songs.now.off")
    : s.count === 0
      ? t("songs.now.empty")
      : t("songs.now.listening", { count: s.count });
  if (!s.song || state === "listening" || state === "off") {
    return (
      <div className="px-4 py-2">
        <button
          type="button"
          onClick={onOpenSongs}
          className="inline-flex items-center gap-1.5 text-xs text-ink-2 hover:text-text rounded-full border border-line px-2.5 py-1 cursor-pointer"
        >
          <Music size={12} aria-hidden />
          {chipText}
        </button>
      </div>
    );
  }

  const song = s.song;
  if (state === "suggested") {
    // Gentle pulse when nobody has tapped for 10 s (review fix H4).
    const pulse = s.since > 10 ? "motion-safe:animate-pulse" : "";
    return (
      <div
        className={`mx-4 my-2 rounded-lg border border-logo-primary bg-logo-primary/10 px-4 py-3 space-y-2 ${pulse}`}
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center gap-2">
          <Music size={16} className="text-logo-primary shrink-0" aria-hidden />
          <span className="text-sm">
            {t("songs.now.soundsLike")}{" "}
            <b className="font-semibold">{song.title}</b>
          </span>
        </div>
        {s.heard && (
          <p className="text-xs text-ink-3 break-words">
            {t("songs.now.heard", { text: s.heard })}
          </p>
        )}
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPicking((p) => !p)}
            aria-expanded={picking}
          >
            {t("songs.now.pick")}
          </Button>
          <Button variant="secondary" size="md" onClick={() => call("/songs/reject")}>
            {t("songs.now.notThis")}
            <Key k="Esc" />
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={() => call("/songs/confirm")}
          >
            {t("songs.now.show")}
            <Key k="→" />
          </Button>
        </div>
        {picking && (
          <SongPicker
            guesses={s.guesses}
            onPick={(id) => call(`/songs/start?id=${encodeURIComponent(id)}`)}
          />
        )}
      </div>
    );
  }

  // Following or lost: the Now singing bar.
  const lost = state === "lost";
  return (
    <div
      className={`mx-4 my-2 rounded-lg border px-4 py-3 space-y-2 ${
        lost ? "border-warning bg-warning-wash" : "border-logo-primary bg-logo-primary/10"
      }`}
    >
      <div className="flex items-center gap-2">
        <Music size={16} className="text-logo-primary shrink-0" aria-hidden />
        <span className="text-sm font-semibold truncate">{song.title}</span>
        <span className="text-xs text-ink-3 shrink-0">
          {t("songs.now.line", { n: song.line + 1, m: song.lines })}
          {song.chorus && ` · ${t("songs.now.chorus")}`}
        </span>
        <span className="flex-1" />
        <Button variant="secondary" size="sm" onClick={() => call("/songs/stop")}>
          <span className="inline-flex items-center gap-1">
            <Square size={12} aria-hidden />
            {t("songs.now.stop")}
          </span>
          <Key k="Esc" />
        </Button>
      </div>
      {lost ? (
        <p className="text-sm" role="status" aria-live="polite">
          {t("songs.now.lost")}
        </p>
      ) : (
        <div className="space-y-0.5">
          <p className="text-base font-semibold break-words">{song.text}</p>
          {song.translation && (
            <p className="text-sm text-ink-2 break-words">{song.translation}</p>
          )}
        </div>
      )}
      {song.next && (
        <p className="text-xs text-ink-3 break-words">
          {t("songs.now.next", { text: song.next })}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button
          variant="secondary"
          size="md"
          disabled={song.line <= 0}
          onClick={() => call("/songs/back")}
        >
          <span className="inline-flex items-center gap-1">
            <ChevronLeft size={16} aria-hidden />
            {t("songs.now.back")}
          </span>
          <Key k="←" />
        </Button>
        <Button
          variant="primary"
          size="md"
          disabled={song.line >= song.lines - 1 && !lost}
          onClick={() => call("/songs/next")}
        >
          <span className="inline-flex items-center gap-1">
            {t("songs.now.forward")}
            <ChevronRight size={16} aria-hidden />
          </span>
          <Key k="→" />
        </Button>
      </div>
    </div>
  );
};

/** "Pick the song…": the best guesses first, then search the library (review fix H2). */
export const SongPicker: React.FC<{
  guesses: { id: string; title: string }[];
  onPick: (id: string) => void;
}> = ({ guesses, onPick }) => {
  const { t } = useTranslation();
  const [q, setQ] = useState("");
  const [all, setAll] = useState<{ id: string; title: string }[]>([]);
  useEffect(() => {
    engineGet<{ songs: { id: string; title: string }[] }>("/songs").then(
      (r) => r.data && setAll(r.data.songs),
    );
  }, []);
  const needle = q.trim().toLowerCase();
  const list = needle
    ? all.filter((x) => x.title.toLowerCase().includes(needle))
    : [...guesses, ...all.filter((x) => !guesses.some((g) => g.id === x.id))];
  return (
    <div className="space-y-1">
      <input
        autoFocus
        className="w-full px-2 py-1 text-sm bg-wash border border-line-strong rounded-md focus:outline-none focus:border-logo-primary"
        placeholder={t("songs.search")}
        aria-label={t("songs.now.pickTitle")}
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <ul className="max-h-40 overflow-y-auto rounded-md border border-line divide-y divide-line">
        {list.slice(0, 30).map((x) => (
          <li key={x.id}>
            <button
              type="button"
              className="w-full text-start px-2 py-1.5 text-sm hover:bg-logo-primary/10 cursor-pointer"
              onClick={() => onPick(x.id)}
            >
              {x.title}
            </button>
          </li>
        ))}
        {list.length === 0 && (
          <li className="px-2 py-1.5 text-sm text-ink-3">
            {t("songs.noMatch", { q })}
          </li>
        )}
      </ul>
    </div>
  );
};
