import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { openUrl } from "@tauri-apps/plugin-opener";
import { NowSinging } from "../../songs/NowSinging";
import { SettingsGroup } from "../../ui/SettingsGroup";
import { SettingContainer } from "../../ui/SettingContainer";
import { Switch } from "../../ui/Switch";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";
import { Dropdown } from "../../ui/Dropdown";
import { SpeechModelSummary } from "../../speech/SpeechModels";
import {
  engineGet,
  useEngine,
  type EngineState,
} from "../../../hooks/useEngine";
import { commands } from "@/bindings";
import type { TFunction } from "i18next";

/** A row of buttons where one is chosen (language, caption style, …). */
export const Segmented: React.FC<{
  options: { value: string; label: string; hint?: string }[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  ariaLabel: string;
}> = ({ options, value, onChange, disabled, ariaLabel }) => (
  <div
    role="radiogroup"
    aria-label={ariaLabel}
    className="flex flex-wrap gap-1.5"
  >
    {options.map((o) => {
      const chosen = o.value === value;
      return (
        <button
          key={o.value}
          role="radio"
          aria-checked={chosen}
          disabled={disabled}
          title={o.hint}
          onClick={() => !chosen && onChange(o.value)}
          className={`px-3 py-1.5 text-sm rounded-lg border transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
            chosen
              ? "bg-logo-primary/25 border-logo-primary font-semibold"
              : "bg-wash border-line hover:border-logo-primary hover:bg-logo-primary/10"
          }`}
        >
          {o.label}
          {o.hint && (
            <span className="block text-[11px] font-normal text-ink-3 leading-tight">
              {o.hint}
            </span>
          )}
        </button>
      );
    })}
  </div>
);

/** One-line status: what the engine is doing right now. */
function statusLine(d: EngineState, t: TFunction) {
  if (d.status === "switching")
    return { tone: "busy", text: t("live.status.switching") };
  if (d.setup.running)
    return { tone: "busy", text: `${d.setup.message} (${d.setup.percent}%)` };
  if (d.setup.error) return { tone: "error", text: d.setup.error };
  if (d.speech_loading)
    return { tone: "busy", text: d.speech_status || t("live.status.loading") };
  if (d.engine !== "qwen")
    return { tone: "busy", text: t("live.status.gettingReady") };
  if (!d.captions_on) return { tone: "off", text: t("live.status.micOff") };
  return {
    tone: "ok",
    text: t("live.status.listening", {
      model: d.speech_models[d.speech_model]?.label ?? d.speech_model,
    }),
  };
}

export const EngineBanner: React.FC<{ error: string | null }> = ({ error }) => {
  const { t } = useTranslation();
  return (
    <div className="rounded-lg border border-line bg-wash p-4 text-sm space-y-1">
      <p className="font-medium">{t("live.engine.starting")}</p>
      {error && <p className="text-ink-3 break-words">{error}</p>}
    </div>
  );
};

export const LiveCaptionsSettings: React.FC<{
  onOpenModels?: () => void;
  onOpenSongs?: () => void;
}> = ({ onOpenModels, onOpenSongs }) => {
  const { t } = useTranslation();
  const { state: d, error, send, refresh } = useEngine(1000);
  const [volume, setVolume] = useState<number | null>(null);
  const volTimer = useRef<number | null>(null);

  if (!d) {
    return (
      <div className="max-w-3xl w-full mx-auto space-y-6">
        <EngineBanner error={error} />
      </div>
    );
  }

  const st = statusLine(d, t);
  const busy = d.status === "switching";
  const dot =
    st.tone === "ok"
      ? "bg-moss"
      : st.tone === "error"
        ? "bg-error"
        : st.tone === "off"
          ? "bg-ink-3"
          : "bg-warning";
  const root = d.sessions_root || "";
  const folder = d.session.startsWith(root)
    ? d.session.slice(root.length).replace(/^[\\/]/, "")
    : d.session;

  return (
    <div className="max-w-3xl w-full mx-auto space-y-6">
      {/* Live captions: the main switch and what is on screen now */}
      <SettingsGroup title={t("live.title")}>
        <SettingContainer
          title={d.captions_on ? t("live.master.on") : t("live.master.off")}
          description={t("live.master.description")}
          grouped
        >
          <Switch
            checked={d.captions_on}
            disabled={busy}
            onChange={(on) => send(`/captions?on=${on ? 1 : 0}`)}
            ariaLabel={t("live.master.label")}
          />
        </SettingContainer>
        <div
          className="px-4 py-2 flex items-center gap-2 text-sm"
          aria-live="polite"
        >
          <span
            className={`inline-block w-2 h-2 rounded-full ${dot}`}
            aria-hidden
          />
          <span>{st.text}</span>
          {d.obs && (
            <span className="ms-auto text-xs text-ink-3">
              {t("live.obs.connected")}
            </span>
          )}
        </div>
        <div className="px-4 py-3">
          <p className="text-xs text-ink-3 mb-1">{t("live.nowOnScreen")}</p>
          <p className="text-lg font-medium min-h-7 break-words whitespace-pre-line">
            {d.caption || (
              <span className="text-ink-3 text-sm font-normal">
                {t("live.clear")}
              </span>
            )}
          </p>
        </div>
        <NowSinging s={d.songs} onOpenSongs={onOpenSongs} onChanged={refresh} />
      </SettingsGroup>

      {/* Language and caption style */}
      <SettingsGroup title={t("live.language.title")}>
        <SettingContainer
          title={t("live.language.label")}
          description={t("live.language.description")}
          layout="stacked"
          grouped
        >
          <Segmented
            ariaLabel={t("live.language.label")}
            value={d.mode}
            disabled={busy}
            onChange={(v) => send(`/mode?set=${v}`)}
            options={Object.entries(d.modes).map(([value, label]) => ({
              value,
              label,
              hint: d.hints[value],
            }))}
          />
        </SettingContainer>
        <SettingContainer
          title={t("live.style.label")}
          description={t("live.style.description")}
          layout="stacked"
          grouped
        >
          <Segmented
            ariaLabel={t("live.style.label")}
            value={d.style}
            onChange={(v) => send(`/style?set=${v}`)}
            options={Object.entries(d.styles).map(([value, label]) => ({
              value,
              label,
              hint: d.style_hints[value],
            }))}
          />
          {d.style !== "word" &&
            d.style_status &&
            d.style_status !== "ready" && (
              <p className="text-xs text-ink-3 mt-2">{d.style_status}</p>
            )}
        </SettingContainer>
      </SettingsGroup>

      {/* Speech: which model listens. Chosen on the Models page. */}
      <SettingsGroup title={t("live.speech.title")}>
        <SettingContainer
          title={t("live.speech.model")}
          description={t("live.speech.modelDescription")}
          grouped
        >
          <SpeechModelSummary d={d} onOpen={() => onOpenModels?.()} />
        </SettingContainer>
        {(d.setup.running || d.setup.error) && (
          <div className="px-4 py-3 space-y-2">
            <div
              className="h-2 rounded-full bg-line overflow-hidden"
              role="progressbar"
              aria-valuenow={d.setup.percent}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full bg-background-ui transition-all"
                style={{ width: `${d.setup.percent}%` }}
              />
            </div>
            <p className="text-xs text-ink-3">
              {d.setup.error || d.setup.message}
            </p>
            {d.setup.error && (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => send("/setup/retry")}
              >
                {t("live.speech.retry")}
              </Button>
            )}
          </div>
        )}
      </SettingsGroup>

      {/* The microphone the live captions listen to */}
      <SettingsGroup
        title={t("live.mic.title")}
        description={d.obs ? t("live.mic.obs") : undefined}
      >
        {!d.obs && (
          <SettingContainer
            title={t("live.mic.device")}
            description={t("live.mic.deviceDescription")}
            grouped
          >
            <Dropdown
              selectedValue={d.mic.device_id}
              disabled={busy}
              onSelect={(v) => send(`/mic?device=${encodeURIComponent(v)}`)}
              options={d.mic.devices.map((m) => ({
                value: m.id,
                label: m.name,
              }))}
            />
          </SettingContainer>
        )}
        <SettingContainer
          title={t("live.mic.volume")}
          description={t("live.mic.volumeDescription")}
          grouped
        >
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={0}
              max={100}
              aria-label={t("live.mic.volume")}
              value={Math.round((volume ?? d.mic.volume) * 100)}
              onChange={(e) => {
                const v = Number(e.target.value) / 100;
                setVolume(v);
                if (volTimer.current) window.clearTimeout(volTimer.current);
                volTimer.current = window.setTimeout(async () => {
                  await send(`/mic?volume=${v}`);
                  setVolume(null);
                }, 150);
              }}
              className="w-32 accent-[var(--color-background-ui)]"
            />
            <Button
              size="sm"
              variant={d.mic.muted ? "primary" : "secondary"}
              onClick={() => send(`/mic?muted=${d.mic.muted ? 0 : 1}`)}
            >
              {d.mic.muted ? t("live.mic.unmute") : t("live.mic.mute")}
            </Button>
          </div>
        </SettingContainer>
        <SettingContainer
          title={t("live.mic.noise")}
          description={t("live.mic.noiseDescription")}
          grouped
        >
          <Segmented
            ariaLabel={t("live.mic.noise")}
            value={d.mic.noise}
            onChange={(v) => send(`/mic?noise=${v}`)}
            options={["low", "medium", "high"].map((v) => ({
              value: v,
              label: t(`live.mic.noise_${v}`),
            }))}
          />
        </SettingContainer>
      </SettingsGroup>

      {/* Saving */}
      <SettingsGroup title={t("live.save.title")}>
        <div className="px-4 py-3 space-y-2">
          <p className="text-sm break-words">
            {folder
              ? t("live.save.folder", { folder, count: d.lines })
              : t("live.save.next")}
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => engineGet("/session/open")}
            >
              {t("live.save.open")}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => send("/session/new")}
            >
              {t("live.save.new")}
            </Button>
          </div>
        </div>
      </SettingsGroup>

      <GoogleDocs d={d} send={send} />
      <ObsCard d={d} />
    </div>
  );
};

const GoogleDocs: React.FC<{
  d: EngineState;
  send: (
    p: string,
  ) => Promise<{ data: EngineState | null; error: string | null }>;
}> = ({ d, send }) => {
  const { t } = useTranslation();
  const g = d.gdocs;
  const [url, setUrl] = useState("");
  const [note, setNote] = useState("");
  const [copied, setCopied] = useState(false);

  const connect = async () => {
    const r = await engineGet<EngineState & { gdocs_error?: string }>(
      `/gdocs?script=${encodeURIComponent(url.trim())}`,
    );
    setNote(r.data?.gdocs_error || r.error || "");
    if (r.data && !r.data.gdocs_error) setUrl("");
  };
  const copyScript = async () => {
    const r = await engineGet<string>("/gdocs/script");
    if (r.data) {
      await navigator.clipboard.writeText(r.data);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    }
  };
  const signIn = async () => {
    const r = await engineGet<EngineState & { gdocs_error?: string }>(
      "/gdocs?signin=1",
    );
    setNote(r.data?.gdocs_error || t("live.docs.finishInBrowser"));
  };

  if (g.signed_in) {
    const state = g.error
      ? `✕ ${g.error}`
      : g.writing
        ? t("live.docs.writing", { doc: g.doc || t("live.docs.newDoc") })
        : t("live.docs.connected", { doc: g.doc || t("live.docs.yourDoc") });
    return (
      <SettingsGroup title={t("live.docs.title")}>
        <div className="px-4 py-3 space-y-2 text-sm">
          <p aria-live="polite">{state}</p>
          {g.writing && (
            <p className="text-xs text-ink-3">
              {t("live.docs.lines", { count: g.sent })}
              {g.waiting
                ? ` · ${t("live.docs.waiting", { count: g.waiting })}`
                : ""}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant={g.writing ? "secondary" : "primary"}
              onClick={() => send(`/gdocs?write=${g.writing ? 0 : 1}`)}
            >
              {g.writing ? t("live.docs.stop") : t("live.docs.start")}
            </Button>
            {g.doc_url && (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => engineGet("/gdocs/open")}
              >
                {t("live.docs.open")}
              </Button>
            )}
            <label className="flex items-center gap-2 text-sm ms-2">
              <Switch
                checked={g.show_time}
                onChange={(on) => send(`/gdocs?time=${on ? 1 : 0}`)}
                ariaLabel={t("live.docs.time")}
              />
              {t("live.docs.time")}
            </label>
            <Button
              size="sm"
              variant="danger-ghost"
              className="ms-auto"
              onClick={() =>
                window.confirm(t("live.docs.confirmOff")) &&
                send("/gdocs?signout=1")
              }
            >
              {g.way === "script"
                ? t("live.docs.disconnect")
                : t("live.docs.signOut")}
            </Button>
          </div>
        </div>
      </SettingsGroup>
    );
  }

  return (
    <SettingsGroup
      title={t("live.docs.title")}
      description={t("live.docs.description")}
    >
      <div className="px-4 py-3 space-y-3 text-sm">
        <ol className="list-decimal ms-5 space-y-1.5">
          <li>
            {t("live.docs.step1")}{" "}
            <Button size="sm" variant="secondary" onClick={copyScript}>
              {copied ? t("live.docs.copied") : t("live.docs.copyScript")}
            </Button>
          </li>
          <li>{t("live.docs.step2")}</li>
          <li>{t("live.docs.step3")}</li>
        </ol>
        <div className="flex gap-2">
          <Input
            className="flex-1 min-w-0"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://script.google.com/macros/s/…/exec"
            aria-label={t("live.docs.urlLabel")}
          />
          <Button size="sm" onClick={connect} disabled={!url.trim()}>
            {t("live.docs.connect")}
          </Button>
        </div>
        {(note || g.error) && (
          <p className="text-xs text-error" role="alert">
            {note || g.error}
          </p>
        )}
        <details>
          <summary className="text-xs text-ink-3 cursor-pointer">
            {t("live.docs.orGoogle")}
          </summary>
          <div className="pt-2 space-y-1">
            <Button
              size="sm"
              variant="secondary"
              disabled={!g.configured}
              onClick={signIn}
            >
              {t("live.docs.signIn")}
            </Button>
            <p className="text-xs text-ink-3">{t("live.docs.googleNote")}</p>
          </div>
        </details>
        <button
          className="text-xs underline text-ink-3 cursor-pointer"
          onClick={() =>
            openUrl(
              "https://github.com/vivekarya2026/live-captions-obs/blob/main/docs/GOOGLE_DOCS.md",
            )
          }
        >
          {t("live.docs.guide")}
        </button>
      </div>
    </SettingsGroup>
  );
};

const ObsCard: React.FC<{ d: EngineState }> = ({ d }) => {
  const { t } = useTranslation();
  const [overlay, setOverlay] = useState("");
  useEffect(() => {
    commands.lcLinks().then((l) => setOverlay(l.overlay_file));
  }, []);
  return (
    <SettingsGroup title={t("live.obs.title")}>
      <div className="px-4 py-3 space-y-1 text-sm">
        <p>{d.obs ? t("live.obs.running") : t("live.obs.notRunning")}</p>
        <p className="text-xs text-ink-3 break-all">
          {t("live.obs.overlay")} <code>{overlay}</code>
        </p>
      </div>
    </SettingsGroup>
  );
};
