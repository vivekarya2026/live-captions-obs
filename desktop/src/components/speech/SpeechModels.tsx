import React from "react";
import { useTranslation } from "react-i18next";
import { ChevronRight } from "lucide-react";
import type { EngineState } from "../../hooks/useEngine";

/** Where one speech model is right now, in the user's words. */
function rowState(d: EngineState, key: string) {
  const m = d.speech_models[key];
  const chosen = d.speech_model === key;
  if (chosen && !m.ready && d.setup.error) return "error" as const;
  if (chosen && !m.ready) return "downloading" as const;
  if (chosen && (d.speech_loading || d.engine !== "qwen"))
    return "starting" as const;
  if (chosen) return "inUse" as const;
  return m.ready ? ("ready" as const) : ("remote" as const);
}

/** One line that says which speech model is listening, and opens the
 *  Models page to change it. */
export const SpeechModelSummary: React.FC<{
  d: EngineState;
  onOpen: () => void;
  compact?: boolean;
}> = ({ d, onOpen, compact }) => {
  const { t } = useTranslation();
  const key = d.speech_model;
  const state = rowState(d, key);
  const dot =
    state === "inUse"
      ? "bg-moss"
      : state === "error"
        ? "bg-error"
        : "bg-warning animate-pulse motion-reduce:animate-none";
  const name = t(`speechModels.models.${key}.name`, {
    defaultValue: d.speech_models[key]?.label ?? key,
  });
  const label = t("speechModels.change", { model: name });
  return (
    <button
      type="button"
      onClick={onOpen}
      title={label}
      aria-label={label}
      className={
        compact
          ? "flex items-center gap-2 hover:text-text transition-colors cursor-pointer"
          : "flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 text-sm hover:bg-wash hover:border-line-strong transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-background-ui"
      }
    >
      <span className={`inline-block size-2 rounded-full ${dot}`} aria-hidden />
      <span className={compact ? "max-w-36 truncate" : "font-medium"}>
        {name}
      </span>
      <ChevronRight
        className={compact ? "size-3" : "size-4 text-ink-3"}
        aria-hidden
      />
    </button>
  );
};
