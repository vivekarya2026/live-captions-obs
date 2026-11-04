import React, { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { FileUp, Play, Trash2 } from "lucide-react";
import { SettingsGroup } from "../ui/SettingsGroup";
import { SettingContainer } from "../ui/SettingContainer";
import { Switch } from "../ui/Switch";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Textarea } from "../ui/Textarea";
import { Dialog } from "../ui/Dialog";
import { commands } from "@/bindings";
import { engineGet, type SongModeState } from "../../hooks/useEngine";
import { EngineBanner } from "../settings/live/LiveCaptionsSettings";
import { CheckSongs, type FoundSong } from "./CheckSongs";

export interface SongSummary {
  id: string;
  title: string;
  language: "hi" | "pa" | "en";
  lines: number;
  translations: string[];
}

interface SongsReply {
  songs: SongSummary[];
  song_mode: SongModeState;
  folder: string;
}

export const SONG_FILES = ["docx", "pdf", "xlsx", "xlsm", "csv", "txt", "md"];

/** A JSON POST to the engine (song import and save). */
export async function enginePost<T>(
  path: string,
  body: unknown,
): Promise<{ data: T | null; error: string | null }> {
  const r = await commands.lcPost(path, JSON.stringify(body));
  if (r.data) {
    try {
      return { data: JSON.parse(r.data) as T, error: null };
    } catch (e) {
      return { data: null, error: String(e) };
    }
  }
  return { data: null, error: r.error ?? "no answer" };
}

/** Songs page (docs/song-mode/04-prototype.md, 3a): library, upload anything, search. */
export const SongsSettings: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<SongsReply | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [reading, setReading] = useState(false);
  const [readErrors, setReadErrors] = useState<string[]>([]);
  const [found, setFound] = useState<{ songs: FoundSong[]; files: string[] } | null>(null);
  const [pasting, setPasting] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [deleting, setDeleting] = useState<SongSummary | null>(null);
  const [saved, setSaved] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);

  const load = async () => {
    const r = await engineGet<SongsReply>("/songs");
    if (r.data) {
      setData(r.data);
      setError(null);
    } else setError(r.error);
  };
  useEffect(() => {
    load();
    const id = window.setInterval(load, 2000);
    return () => window.clearInterval(id);
  }, []);

  const read = async (files: string[], text = "") => {
    setReading(true);
    setReadErrors([]);
    setSaved(null);
    const r = await enginePost<{ ok: boolean; songs: FoundSong[]; errors: string[] }>(
      "/songs/import",
      { files, text },
    );
    setReading(false);
    if (!r.data) {
      setReadErrors([r.error ?? ""]);
      return;
    }
    setReadErrors(r.data.errors);
    if (r.data.songs.length) setFound({ songs: r.data.songs, files });
  };

  // Files dropped while this page is open are song files (the window-wide drop goes to History).
  useEffect(() => {
    const unlisten = getCurrentWebview().onDragDropEvent((event) => {
      const p = event.payload;
      if (p.type === "enter") setDragging(true);
      else if (p.type === "leave") setDragging(false);
      else if (p.type === "drop") {
        setDragging(false);
        const files = p.paths.filter((f) =>
          SONG_FILES.includes(f.split(".").pop()?.toLowerCase() ?? ""),
        );
        if (files.length) read(files);
      }
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  const choose = async () => {
    const picked = await open({
      multiple: true,
      filters: [{ name: t("songs.add.title"), extensions: SONG_FILES }],
    });
    if (!picked) return;
    read(Array.isArray(picked) ? picked : [picked]);
  };

  const save = async (songs: FoundSong[]) => {
    const r = await enginePost<{ ok: boolean; saved: number; error?: string }>(
      "/songs/save",
      { songs, files: found?.files ?? [] },
    );
    if (r.data?.ok) {
      setFound(null);
      setSaved(r.data.saved);
      load();
    } else setReadErrors([r.data?.error ?? r.error ?? ""]);
  };

  const list = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const all = data?.songs ?? [];
    return needle ? all.filter((s) => s.title.toLowerCase().includes(needle)) : all;
  }, [data, q]);

  if (!data) {
    return (
      <div className="max-w-3xl w-full mx-auto space-y-6">
        <EngineBanner error={error} />
      </div>
    );
  }

  if (found) {
    return (
      <div className="max-w-3xl w-full mx-auto space-y-6">
        <CheckSongs
          songs={found.songs}
          source={found.files.map((f) => f.split(/[\\/]/).pop()).join(", ") || t("songs.add.paste")}
          onCancel={() => setFound(null)}
          onSave={save}
        />
      </div>
    );
  }

  const sm = data.song_mode;
  const playing =
    sm.song && (sm.state === "following" || sm.state === "lost") ? sm.song.id : "";

  return (
    <div className="max-w-3xl w-full mx-auto space-y-6">
      <SettingsGroup title={t("songs.title")} description={t("songs.description")}>
        <SettingContainer
          title={t("songs.mode")}
          description={t("songs.modeDescription")}
          grouped
        >
          <Switch
            checked={sm.on}
            onChange={async (on) => {
              await engineGet(`/songs/mode?on=${on ? 1 : 0}`);
              load();
            }}
            ariaLabel={t("songs.mode")}
          />
        </SettingContainer>
      </SettingsGroup>

      <SettingsGroup title={t("songs.add.title")}>
        <div className="px-4 py-3">
          <div
            className={`rounded-lg border-2 border-dashed px-4 py-5 text-center space-y-3 transition-colors ${
              dragging ? "border-logo-primary bg-logo-primary/10" : "border-line"
            }`}
          >
            <FileUp size={22} className="mx-auto text-ink-3" aria-hidden />
            <p className="text-sm">{reading ? t("songs.add.reading") : t("songs.add.drop")}</p>
            <div className="flex justify-center gap-2">
              <Button size="sm" onClick={choose} disabled={reading}>
                {t("songs.add.choose")}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setPasting(true)}
                disabled={reading}
              >
                {t("songs.add.paste")}
              </Button>
            </div>
            <p className="text-xs text-ink-3">{t("songs.add.tip")}</p>
            <button
              type="button"
              className="text-xs text-logo-primary underline cursor-pointer"
              onClick={() => engineGet("/songs/example")}
            >
              {t("songs.add.example")}
            </button>
          </div>
          {readErrors.filter(Boolean).map((e) => (
            <p key={e} className="mt-2 text-xs text-error" role="alert">
              {e}
            </p>
          ))}
          {saved !== null && (
            <p className="mt-2 text-xs text-moss" role="status">
              {t("songs.check.saved", { count: saved })}
            </p>
          )}
        </div>
      </SettingsGroup>

      <SettingsGroup title={t("songs.count", { count: data.songs.length })}>
        <div className="px-4 py-3">
          <Input
            variant="compact"
            className="w-full"
            placeholder={t("songs.search")}
            aria-label={t("songs.search")}
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        {data.songs.length === 0 ? (
          <p className="px-4 py-3 text-sm text-ink-3">{t("songs.empty")}</p>
        ) : list.length === 0 ? (
          <p className="px-4 py-3 text-sm text-ink-3">{t("songs.noMatch", { q })}</p>
        ) : (
          list.map((s) => (
            <SongRow
              key={s.id}
              s={s}
              playing={playing === s.id}
              onStart={async () => {
                await engineGet(`/songs/start?id=${encodeURIComponent(s.id)}`);
                load();
              }}
              onDelete={() => setDeleting(s)}
            />
          ))
        )}
        <div className="px-4 py-2">
          <Button size="sm" variant="ghost" onClick={() => engineGet("/songs/open")}>
            {t("songs.openFolder")}
          </Button>
        </div>
      </SettingsGroup>

      <Dialog
        open={pasting}
        onOpenChange={setPasting}
        title={t("songs.add.pasteTitle")}
        closeLabel={t("songs.close")}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setPasting(false)}>
              {t("songs.add.cancel")}
            </Button>
            <Button
              disabled={!pasteText.trim()}
              onClick={() => {
                setPasting(false);
                read([], pasteText);
              }}
            >
              {t("songs.add.read")}
            </Button>
          </div>
        }
      >
        <Textarea
          className="w-full min-h-[240px] font-normal"
          placeholder={t("songs.add.pastePlaceholder")}
          aria-label={t("songs.add.pasteTitle")}
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
        />
      </Dialog>

      <Dialog
        open={deleting !== null}
        onOpenChange={(o) => !o && setDeleting(null)}
        title={t("songs.deleteTitle", { title: deleting?.title ?? "" })}
        description={t("songs.deleteBody")}
        closeLabel={t("songs.close")}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDeleting(null)}>
              {t("songs.add.cancel")}
            </Button>
            <Button
              variant="danger"
              onClick={async () => {
                if (deleting)
                  await engineGet(`/songs/delete?id=${encodeURIComponent(deleting.id)}`);
                setDeleting(null);
                load();
              }}
            >
              {t("songs.deleteConfirm")}
            </Button>
          </div>
        }
      >
        <span />
      </Dialog>
    </div>
  );
};

const SongRow: React.FC<{
  s: SongSummary;
  playing: boolean;
  onStart: () => void;
  onDelete: () => void;
}> = ({ s, playing, onStart, onDelete }) => {
  const { t } = useTranslation();
  const [openLines, setOpenLines] = useState<{ text: string; translations: Record<string, string> }[] | null>(null);
  const toggle = async () => {
    if (openLines) return setOpenLines(null);
    const r = await engineGet<{ song: { lines: { text: string; translations: Record<string, string> }[] } | null }>(
      `/songs/song?id=${encodeURIComponent(s.id)}`,
    );
    setOpenLines(r.data?.song?.lines ?? []);
  };
  return (
    <div className="px-4 py-2 text-sm">
      <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-3 items-center">
        <button
          type="button"
          className="text-start font-medium break-words hover:text-logo-primary cursor-pointer"
          onClick={toggle}
          aria-expanded={openLines !== null}
        >
          {playing && "♪ "}
          {s.title}
        </button>
        <span className="text-ink-3">{t(`songs.lang.${s.language}`)}</span>
        <span className="text-ink-3">{t("songs.lineCount", { count: s.lines })}</span>
        <span className="text-ink-3 min-w-16">
          {s.translations.map((l) => t(`songs.lang.${l}`)).join(", ") || "—"}
        </span>
        <span className="flex gap-1">
          <Button size="sm" variant="ghost" aria-label={t("songs.start", { title: s.title })} onClick={onStart}>
            <Play size={16} />
          </Button>
          <Button
            size="sm"
            variant="danger-ghost"
            disabled={playing}
            title={playing ? t("songs.stopFirst") : undefined}
            aria-label={playing ? t("songs.stopFirst") : t("songs.delete", { title: s.title })}
            onClick={onDelete}
          >
            <Trash2 size={16} />
          </Button>
        </span>
      </div>
      {openLines && (
        <ol className="mt-2 ms-4 space-y-1.5 list-decimal text-sm">
          {openLines.map((ln, i) => (
            <li key={i}>
              <span className="break-words">{ln.text}</span>
              {Object.values(ln.translations).map((tr) => (
                <span key={tr} className="block text-ink-3 break-words">
                  {tr}
                </span>
              ))}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
};
