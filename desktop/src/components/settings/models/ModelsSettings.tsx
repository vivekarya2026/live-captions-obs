import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw } from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { useModelStore } from "@/stores/modelStore";
import {
  ModelTable,
  Note,
  useModelFilters,
  type TableSection,
} from "@/components/shared/modelTable/ModelTable";
import RetiredModelsNotice from "./RetiredModelsNotice";
import { ModelRow } from "./ModelRow";
import { Legend } from "./Legend";
import { useModelEntries } from "./modelEntries";
import { Switch } from "@/components/ui/Switch";
import { useSettings } from "@/hooks/useSettings";
import { useEngine } from "@/hooks/useEngine";
import { EngineModelTable } from "@/components/speech/EngineModelTable";
import { EngineBanner } from "@/components/settings/live/LiveCaptionsSettings";

/** Past this many models on disk, the rest fold under "Show N more". */
const YOURS_LIMIT = 5;

/** Look for model files added outside Handy: quiet, beside its section's name. */
const Rescan: React.FC = () => {
  const { t } = useTranslation();
  const rescanning = useModelStore((s) => s.isRescanning);
  return (
    <Tooltip text={t("settings.models.rescan.tooltip")}>
      <button
        type="button"
        onClick={() => useModelStore.getState().rescanLocalModels()}
        disabled={rescanning}
        aria-label={t("settings.models.rescan.tooltip")}
        className="ms-[6px] grid size-[22px] cursor-pointer place-items-center rounded-full text-ink-3 hover:bg-wash hover:text-text disabled:cursor-default focus:outline-none focus-visible:ring-1 focus-visible:ring-logo-primary"
      >
        <RefreshCw
          className={`size-[12px] ${rescanning ? "animate-spin" : ""}`}
          aria-hidden="true"
        />
      </button>
    </Tooltip>
  );
};

interface ModelsSettingsProps {
  /** Where the languages are changed (General). */
  onChangeLanguages?: () => void;
}

/** The Models page. First the speech model (Qwen3) that live captions and
 *  dictation use; under it, folded away, the type-only models (Whisper,
 *  Parakeet, …) for dictation without translation and for audio files. */
export const ModelsSettings: React.FC<ModelsSettingsProps> = ({
  onChangeLanguages,
}) => {
  const { t } = useTranslation();
  const loading = useModelStore((s) => s.loading);
  const { facts, lists } = useModelEntries();
  // Engine models have no per-language grades: only speed and size columns.
  const engineGrading = useMemo(() => ({ ...facts, langs: [] }), [facts]);
  const { filters, setFilters, searching, matches } = useModelFilters();
  const [more, setMore] = useState(false);
  const { state: engine, error: engineError, send } = useEngine(1000);
  const { getSetting, updateSetting } = useSettings();
  const typeOnly = getSetting("speech_engine") === "built_in";
  const [open, setOpen] = useState(typeOnly);

  if (loading) {
    return (
      <div className="max-w-3xl w-full mx-auto">
        <div className="flex items-center justify-center py-16">
          <div className="w-8 h-8 border-2 border-logo-primary border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  const keep = (xs: typeof lists.yours) => xs.filter(matches);
  const moreButton = !searching && lists.yours.length > YOURS_LIMIT && (
    <button
      type="button"
      onClick={() => setMore((m) => !m)}
      className="ms-[40px] mt-[2px] flex h-[28px] cursor-pointer items-center gap-[8px] rounded-[7px] px-[2px] text-small font-medium text-ink-2 hover:text-text focus:outline-none focus-visible:ring-1 focus-visible:ring-logo-primary"
    >
      {more
        ? t("settings.models.showFewer")
        : t("settings.models.showMore", {
            count: lists.yours.length - YOURS_LIMIT,
          })}
      <span
        aria-hidden="true"
        className={`inline-block size-[6px] shrink-0 border-e-[1.5px] border-b-[1.5px] border-current ${more ? "mt-[3px] -rotate-[135deg]" : "-mt-[3px] rotate-45"}`}
      />
    </button>
  );

  const sections: TableSection[] = searching
    ? [
        {
          key: "yours",
          label: t("settings.models.sections.yours"),
          rows: keep(lists.yours),
        },
        {
          key: "fits",
          label: t("settings.models.sections.fits"),
          rows: keep(lists.fits),
        },
        {
          key: "partial",
          label: t("modelTable.missingLanguage"),
          rows: keep(lists.partial),
        },
        {
          key: "untested",
          label: t("settings.models.sections.untested"),
          rows: filters.query.trim() ? keep(lists.untested) : [],
          note: t("settings.models.untestedNote"),
        },
      ]
    : [
        {
          key: "yours",
          label: (
            <>
              {t("settings.models.sections.yours")}
              <Rescan />
            </>
          ),
          rows: more ? lists.yours : lists.yours.slice(0, YOURS_LIMIT),
          after: lists.yours.length ? (
            moreButton
          ) : (
            <Note>{t("settings.models.emptyYours")}</Note>
          ),
        },
        {
          key: "fits",
          label: t("settings.models.sections.fits"),
          rows: lists.fits,
        },
        {
          key: "partial",
          label: t("modelTable.missingLanguage"),
          rows: lists.partial,
        },
      ];

  const heading = "text-xs font-medium text-ink-3 uppercase tracking-wide";

  return (
    <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col gap-6">
      <h1 className="flex-none px-[12px] text-xl font-semibold">
        {t("settings.models.title")}
      </h1>

      {/* Live Captions' two models: transcription and translation. */}
      {(["speech", "translation"] as const).map((kind) => (
        <section key={kind} className="flex-none space-y-2">
          <div className="px-4">
            <h2 className={heading}>{t(`engineModels.${kind}Title`)}</h2>
            <p className="text-xs text-ink-3 mt-1">
              {t(`engineModels.${kind}Description`)}
            </p>
          </div>
          {engine ? (
            <EngineModelTable
              d={engine}
              send={send}
              kind={kind}
              grading={engineGrading}
              title={t(`engineModels.${kind}Head`)}
            />
          ) : (
            kind === "speech" && <EngineBanner error={engineError} />
          )}
        </section>
      ))}

      {/* Type-only models: dictation without translation, audio files. */}
      <section
        className={`space-y-2 ${open ? "flex min-h-[360px] flex-1 flex-col" : "flex-none"}`}
      >
        <div className="flex flex-none items-start justify-between gap-3 px-4">
          <div>
            <h2 className={heading}>{t("speechModels.typeOnly.title")}</h2>
            <p className="text-xs text-ink-3 mt-1">
              {t("speechModels.typeOnly.description")}
            </p>
          </div>
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
            className="shrink-0 cursor-pointer rounded-md px-2 py-1 text-xs font-medium text-ink-2 hover:bg-wash hover:text-text focus:outline-none focus-visible:ring-2 focus-visible:ring-background-ui"
          >
            {open
              ? t("speechModels.typeOnly.hide")
              : t("speechModels.typeOnly.show")}
          </button>
        </div>
        {open && (
          <>
            <div className="flex flex-none items-center justify-between gap-4 rounded-lg border border-line bg-background px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium">
                  {t("speechModels.typeOnly.toggle")}
                </p>
                <p className="text-xs text-ink-3 mt-0.5">
                  {typeOnly
                    ? t("speechModels.typeOnly.toggleOn")
                    : t("speechModels.typeOnly.toggleOff")}
                </p>
              </div>
              <Switch
                checked={typeOnly}
                onChange={(on) =>
                  updateSetting(
                    "speech_engine",
                    on ? "built_in" : "live_captions",
                  )
                }
                ariaLabel={t("speechModels.typeOnly.toggle")}
              />
            </div>
            {onChangeLanguages && (
              <button
                type="button"
                onClick={onChangeLanguages}
                className="flex-none self-end cursor-pointer px-[12px] text-sm text-text underline decoration-line-strong underline-offset-[3px] hover:decoration-text focus:outline-none focus-visible:ring-1 focus-visible:ring-logo-primary"
              >
                {t("settings.models.changeLanguages")}
              </button>
            )}
            <div className="flex-none empty:hidden">
              <RetiredModelsNotice />
            </div>
            <ModelTable
              grading={facts}
              filters={filters}
              setFilters={setFilters}
              // "Yours" always shows at rest; a search hides empty sections.
              sections={sections.filter(
                (s) => s.rows.length || (s.key === "yours" && !searching),
              )}
              renderRow={(e) => <ModelRow key={e.id} entry={e} />}
              actionsHead={<Legend tier={facts.tier} />}
              footer={
                !searching &&
                lists.untested.length > 0 && (
                  <Note>
                    {t("settings.models.untestedHidden", {
                      count: lists.untested.length,
                    })}
                  </Note>
                )
              }
              thinEdge
            />
          </>
        )}
      </section>
    </div>
  );
};
