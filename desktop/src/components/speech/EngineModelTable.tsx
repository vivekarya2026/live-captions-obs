import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Loader2, Lock, Trash2 } from "lucide-react";
import { Radio } from "../ui/Radio";
import { Button } from "../ui/Button";
import { DownloadMark } from "../shared/DownloadMark";
import { ModelTableRow } from "../shared/modelTable/ModelTableRow";
import { ModelTableContext, type TableModel } from "../shared/modelTable/context";
import { Codes, rowGrid, CODE_CLASS } from "../shared/modelTable/columns";
import type { Grading } from "@/lib/models/grading";
import type { EngineState } from "../../hooks/useEngine";

type Send = (
  path: string,
) => Promise<{ data: EngineState | null; error: string | null }>;

export type EngineModelKind = "speech" | "translation";

/** What the engine says about one kind of model. */
function view(d: EngineState, kind: EngineModelKind) {
  if (kind === "speech")
    return {
      models: d.speech_models,
      chosen: d.speech_model,
      loaded: d.speech_loaded ?? (d.engine === "qwen" ? d.speech_model : ""),
      loading: d.speech_loading,
      fallback: d.speech_default ?? "qwen-0.6b",
      route: "/speech?model=",
    };
  return {
    models: d.translation_models ?? {},
    chosen: d.translation_model ?? "nllb",
    loaded: d.translation_loaded ?? "",
    loading: d.translation_loading ?? false,
    fallback: d.translation_default ?? "nllb",
    route: "/translation?model=",
  };
}

/** Speech (transcription) or translation models from the engine, in the
 *  Models page's table look: pick to download or load, trash to delete. */
export const EngineModelTable: React.FC<{
  d: EngineState;
  send: Send;
  kind: EngineModelKind;
  grading: Grading;
  title: string;
}> = ({ d, send, kind, grading, title }) => {
  const { t } = useTranslation();
  const v = view(d, kind);
  const [asking, setAsking] = useState<string | null>(null);
  const [error, setError] = useState("");

  const remove = async (key: string) => {
    setAsking(null);
    const r = await send(`/models/delete?key=${key}`);
    const why = (r.data as (EngineState & { delete_error?: string }) | null)
      ?.delete_error;
    setError(why || r.error || "");
  };

  return (
    <ModelTableContext.Provider
      value={{ grading, actions: true, highlighted: null }}
    >
      <div className="flex w-full flex-col overflow-hidden rounded-panel border border-line bg-background text-start">
        <div className={`${rowGrid(true)} h-[32px] px-[20px]`}>
          <span />
          <span className={`flex min-w-0 items-center truncate ${CODE_CLASS}`}>
            {title}
          </span>
          <Codes langs={grading.langs} />
          <span />
        </div>
        <div
          role="radiogroup"
          aria-label={title}
          className="flex flex-col gap-[4px] px-[6px] pb-[6px]"
        >
          {Object.entries(v.models).map(([key, m]) => {
            const chosen = v.chosen === key;
            const inUse = chosen && v.loaded === key && !v.loading;
            const downloading = chosen && !m.ready;
            const loading = chosen && m.ready && !inUse;
            const protectedModel = key === v.fallback;
            const deletable = m.ready && !chosen && !protectedModel;
            const name = t(`engineModels.${key}.name`, {
              defaultValue: m.label,
            });
            const entry: TableModel = {
              id: key,
              name,
              description: t(`engineModels.${key}.about`, {
                defaultValue: "",
              }),
              languages: ["en", "hi"],
              streaming: false,
              translate: kind === "translation",
              sizeMb: (m.size_gb ?? 0) * 1000,
              quant: "int8",
              kind: "catalog",
            };
            const mark = downloading ? null : loading ? (
              <Loader2
                className="size-[18px] animate-spin text-ink-3"
                aria-hidden="true"
              />
            ) : m.ready ? (
              <Radio checked={inUse} />
            ) : (
              <DownloadMark accent />
            );
            const line = asking === key ? (
              <span className="text-text">
                {t("engineModels.deleteAsk", {
                  name,
                  size: `${m.size_gb} GB`,
                })}
              </span>
            ) : downloading && d.setup.error ? (
              <span className="text-error">{d.setup.message}</span>
            ) : downloading && !d.setup.running ? (
              t("engineModels.queued")
            ) : loading ? (
              t("engineModels.loading")
            ) : inUse ? (
              <span className="text-moss">
                {t("engineModels.inUse")}
                {protectedModel ? ` · ${t("engineModels.default")}` : ""}
              </span>
            ) : undefined;
            const slotClass =
              "grid size-[24px] cursor-pointer place-items-center rounded-[7px] text-ink-3 hover:bg-line hover:text-text focus:outline-none focus-visible:ring-1 focus-visible:ring-logo-primary";
            const slot = deletable ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setAsking(key);
                }}
                title={t("engineModels.delete", { name })}
                aria-label={t("engineModels.delete", { name })}
                className={`${slotClass} opacity-40 transition-opacity group-hover:opacity-100 focus-visible:opacity-100`}
              >
                <Trash2 className="size-[14px]" aria-hidden="true" />
              </button>
            ) : m.ready && protectedModel ? (
              <span title={t("engineModels.defaultKept")}>
                <Lock className="size-[13px] text-ink-3" aria-hidden="true" />
              </span>
            ) : (
              <span />
            );
            const tail = asking === key && (
              <span className="col-span-2 flex items-center justify-end gap-[6px]">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setAsking(null);
                  }}
                >
                  {t("settings.models.cancel")}
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    void remove(key);
                  }}
                >
                  {t("common.delete")}
                </Button>
              </span>
            );
            return (
              <ModelTableRow
                key={key}
                entry={entry}
                selected={inUse}
                mark={mark}
                download={
                  downloading && d.setup.running
                    ? { state: "downloading", percent: d.setup.percent }
                    : null
                }
                line={line}
                slot={slot}
                tail={tail || undefined}
                onDisk={m.ready}
                inert={d.status === "switching"}
                onActivate={() => {
                  if (asking || chosen || d.status === "switching") return;
                  setError("");
                  void send(`${v.route}${key}`);
                }}
                hint={m.ready ? undefined : t("engineModels.download")}
              />
            );
          })}
        </div>
        {error && (
          <p className="px-[20px] pb-[10px] text-small text-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </ModelTableContext.Provider>
  );
};
