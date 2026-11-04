import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertCircle, ArrowDown, ArrowUp, CheckCircle2 } from "lucide-react";
import { SettingsGroup } from "../ui/SettingsGroup";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";

export interface FoundLine {
  text: string;
  translations: Record<string, string>;
}

export interface FoundSong {
  title: string;
  language: "hi" | "pa" | "en";
  lines: FoundLine[];
  source: string;
  warnings: string[];
  title_guessed?: boolean;
}

const LANGS = ["hi", "pa", "en"] as const;
const PREVIEW = 2;

/** The language the translations of a song are in (the first one that has any). */
const trLang = (s: FoundSong) =>
  (["en", "hi", "pa"] as const).find((k) => s.lines.some((l) => l.translations[k])) ?? "en";

/** Move every translation one line up or down (review fix H7). */
function shift(lines: FoundLine[], lang: string, d: 1 | -1): FoundLine[] {
  const trs = lines.map((l) => l.translations[lang] ?? "");
  const moved = d === 1 ? ["", ...trs.slice(0, -1)] : [...trs.slice(1), ""];
  return lines.map((l, i) => {
    const t = { ...l.translations };
    if (moved[i]) t[lang] = moved[i];
    else delete t[lang];
    return { ...l, translations: t };
  });
}

/** Check page (docs/song-mode/04-prototype.md, 3b): what was understood, before saving. */
export const CheckSongs: React.FC<{
  songs: FoundSong[];
  source: string;
  onCancel: () => void;
  onSave: (songs: FoundSong[]) => void;
}> = ({ songs: initial, source, onCancel, onSave }) => {
  const { t } = useTranslation();
  const [songs, setSongs] = useState(initial);
  const [skipped, setSkipped] = useState<Set<number>>(new Set());
  const [editing, setEditing] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const keep = songs.filter((_, i) => !skipped.has(i));

  const update = (i: number, s: FoundSong) =>
    setSongs((all) => all.map((x, j) => (j === i ? s : x)));
  const toggle = (set: Set<number>, i: number) => {
    const n = new Set(set);
    if (n.has(i)) n.delete(i);
    else n.add(i);
    return n;
  };

  return (
    <SettingsGroup
      title={t("songs.check.title")}
      description={`${t("songs.check.found", { count: songs.length })} ${t("songs.check.in", { source })}`}
    >
      {songs.map((s, i) => {
        const lang = trLang(s);
        const have = s.lines.filter((l) => l.translations[lang]).length;
        const warn = s.warnings.length > 0;
        const isSkipped = skipped.has(i);
        const isEditing = editing === i;
        const shown = isEditing || expanded.has(i) ? s.lines : s.lines.slice(0, PREVIEW);
        return (
          <div key={i} className={`px-4 py-3 space-y-2 ${isSkipped ? "opacity-50" : ""}`}>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              {warn ? (
                <AlertCircle size={16} className="text-warning shrink-0" aria-label="!" />
              ) : (
                <CheckCircle2 size={16} className="text-moss shrink-0" aria-hidden />
              )}
              {isEditing ? (
                <Input
                  variant="compact"
                  className="flex-1 min-w-48"
                  aria-label={t("songs.check.titleLabel")}
                  value={s.title}
                  onChange={(e) => update(i, { ...s, title: e.target.value, title_guessed: false })}
                />
              ) : (
                <span className="font-semibold break-words">{s.title}</span>
              )}
              <select
                className="text-xs bg-wash border border-line rounded px-1 py-0.5"
                aria-label={t("songs.lang." + s.language)}
                value={s.language}
                onChange={(e) => update(i, { ...s, language: e.target.value as FoundSong["language"] })}
              >
                {LANGS.map((l) => (
                  <option key={l} value={l}>
                    {t(`songs.lang.${l}`)}
                  </option>
                ))}
              </select>
              <span className="text-xs text-ink-3">
                {t("songs.check.lines", { count: s.lines.length })} ·{" "}
                {have
                  ? t("songs.check.trFor", { lang: t(`songs.lang.${lang}`), have, n: s.lines.length })
                  : t("songs.check.noTr")}
              </span>
              <span className="flex-1" />
              {!isSkipped && (
                <Button size="sm" variant="ghost" onClick={() => setEditing(isEditing ? null : i)}>
                  {isEditing ? t("songs.check.done") : t("songs.check.edit")}
                </Button>
              )}
              <Button size="sm" variant="ghost" onClick={() => setSkipped(toggle(skipped, i))}>
                {isSkipped ? t("songs.check.undo") : t("songs.check.skip")}
              </Button>
            </div>
            {warn && !isSkipped && (
              <p className="text-xs text-warning ms-6">
                {s.warnings.map((w) => t(`songs.check.warn.${w}`, { defaultValue: w })).join(" · ")}
              </p>
            )}
            {!isSkipped && (
              <ol className="ms-6 space-y-1.5">
                {shown.map((ln, n) => (
                  <li key={n} className="text-sm">
                    {isEditing ? (
                      <div className="grid grid-cols-2 gap-2">
                        <Input
                          variant="compact"
                          aria-label={t("songs.check.lineLabel", { n: n + 1 })}
                          value={ln.text}
                          onChange={(e) =>
                            update(i, {
                              ...s,
                              lines: s.lines.map((x, k) => (k === n ? { ...x, text: e.target.value } : x)),
                            })
                          }
                        />
                        <Input
                          variant="compact"
                          aria-label={t("songs.check.trLabel", { n: n + 1 })}
                          value={ln.translations[lang] ?? ""}
                          onChange={(e) =>
                            update(i, {
                              ...s,
                              lines: s.lines.map((x, k) =>
                                k === n
                                  ? { ...x, translations: { ...x.translations, [lang]: e.target.value } }
                                  : x,
                              ),
                            })
                          }
                        />
                      </div>
                    ) : (
                      <>
                        <span className="block break-words">{ln.text}</span>
                        {ln.translations[lang] && (
                          <span className="block text-ink-3 break-words">{ln.translations[lang]}</span>
                        )}
                      </>
                    )}
                  </li>
                ))}
              </ol>
            )}
            {!isSkipped && !isEditing && s.lines.length > PREVIEW && (
              <button
                type="button"
                className="ms-6 text-xs text-logo-primary underline cursor-pointer"
                onClick={() => setExpanded(toggle(expanded, i))}
              >
                {expanded.has(i) ? t("songs.check.showLess") : t("songs.check.showAll")}
              </button>
            )}
            {isEditing && have > 0 && (
              <div className="ms-6 flex items-center gap-2 text-xs text-ink-3">
                <span>{t("songs.check.shiftHint")}</span>
                <Button
                  size="sm"
                  variant="secondary"
                  aria-label={t("songs.check.shiftUp")}
                  onClick={() => update(i, { ...s, lines: shift(s.lines, lang, -1) })}
                >
                  <ArrowUp size={14} />
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  aria-label={t("songs.check.shiftDown")}
                  onClick={() => update(i, { ...s, lines: shift(s.lines, lang, 1) })}
                >
                  <ArrowDown size={14} />
                </Button>
              </div>
            )}
          </div>
        );
      })}
      <div className="px-4 py-3 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          {t("songs.check.cancel")}
        </Button>
        <Button
          disabled={keep.length === 0}
          onClick={() =>
            onSave(
              keep.map((s) => ({
                ...s,
                lines: s.lines.filter((l) => l.text.trim()),
              })),
            )
          }
        >
          {t("songs.check.save", { count: keep.length })}
        </Button>
      </div>
    </SettingsGroup>
  );
};
