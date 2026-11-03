import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Trash2 } from "lucide-react";
import { SettingsGroup } from "../../ui/SettingsGroup";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";
import { commands, type CustomTerm } from "@/bindings";
import { engineGet } from "../../../hooks/useEngine";
import { EngineBanner } from "./LiveCaptionsSettings";
import { FillerWordRemoval } from "../FillerWordRemoval";

interface TermsReply {
  terms: CustomTerm[];
  sheet: string;
  sheet_terms: number;
}

const clean = (s: string) => s.replace(/\s+/g, " ").trim().slice(0, 200);

/** Words the captions must always spell (and explain) the same way. Saved by the
 * engine in custom_terms.csv, on top of the vocabulary sheet; applies at once. */
export const VocabularySettings: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<TermsReply | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<CustomTerm>({
    term: "",
    english: "",
    hindi: "",
  });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    const r = await engineGet<TermsReply>("/terms");
    if (r.data) {
      setData(r.data);
      setError(null);
    } else {
      setError(r.error);
    }
  };
  useEffect(() => {
    load();
    const id = window.setInterval(() => !data && load(), 2000);
    return () => window.clearInterval(id);
  }, [data === null]);

  const save = async (terms: CustomTerm[]) => {
    setSaving(true);
    const r = await commands.lcSaveTerms(terms);
    setSaving(false);
    if (r.data) {
      const reply = JSON.parse(r.data) as {
        ok: boolean;
        terms?: CustomTerm[];
        error?: string;
      };
      if (reply.ok && reply.terms && data)
        setData({ ...data, terms: reply.terms });
      setError(reply.ok ? null : (reply.error ?? null));
    } else {
      setError(r.error);
    }
  };

  if (!data) {
    return (
      <div className="max-w-3xl w-full mx-auto space-y-6">
        <EngineBanner error={error} />
      </div>
    );
  }

  const term = clean(draft.term);
  const duplicate = data.terms.some(
    (x) => x.term.toLowerCase() === term.toLowerCase(),
  );
  const add = () => {
    if (!term || duplicate) return;
    save([
      ...data.terms,
      { term, english: clean(draft.english), hindi: clean(draft.hindi) },
    ]);
    setDraft({ term: "", english: "", hindi: "" });
  };

  return (
    <div className="max-w-3xl w-full mx-auto space-y-6">
      <SettingsGroup
        title={t("vocab.title")}
        description={t("vocab.description")}
      >
        <div className="px-4 py-3 space-y-2">
          <div className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2 items-center">
            <Input
              variant="compact"
              placeholder={t("vocab.term")}
              aria-label={t("vocab.term")}
              value={draft.term}
              onChange={(e) => setDraft({ ...draft, term: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && add()}
            />
            <Input
              variant="compact"
              placeholder={t("vocab.english")}
              aria-label={t("vocab.english")}
              value={draft.english}
              onChange={(e) => setDraft({ ...draft, english: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && add()}
            />
            <Input
              variant="compact"
              placeholder={t("vocab.hindi")}
              aria-label={t("vocab.hindi")}
              lang="hi"
              value={draft.hindi}
              onChange={(e) => setDraft({ ...draft, hindi: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && add()}
            />
            <Button
              size="sm"
              onClick={add}
              disabled={!term || duplicate || saving}
            >
              {t("vocab.add")}
            </Button>
          </div>
          {duplicate && (
            <p className="text-xs text-warning">
              {t("vocab.duplicate", { term })}
            </p>
          )}
          <p className="text-xs text-ink-3">{t("vocab.example")}</p>
        </div>
        {data.terms.length === 0 ? (
          <p className="px-4 py-3 text-sm text-ink-3">{t("vocab.empty")}</p>
        ) : (
          data.terms.map((x) => (
            <div
              key={x.term}
              className="px-4 py-2 grid grid-cols-[1fr_1fr_1fr_auto] gap-2 items-center text-sm"
            >
              <span className="font-medium break-words">{x.term}</span>
              <span className="text-ink-3 break-words">{x.english || "—"}</span>
              <span className="break-words" lang="hi">
                {x.hindi || "—"}
              </span>
              <Button
                size="sm"
                variant="danger-ghost"
                aria-label={t("vocab.remove", { term: x.term })}
                disabled={saving}
                onClick={() =>
                  save(data.terms.filter((y) => y.term !== x.term))
                }
              >
                <Trash2 size={16} />
              </Button>
            </div>
          ))
        )}
        {error && (
          <p className="px-4 py-2 text-xs text-error" role="alert">
            {error}
          </p>
        )}
      </SettingsGroup>

      <SettingsGroup title={t("vocab.sheetTitle")}>
        <div className="px-4 py-3 space-y-2 text-sm">
          <p>{t("vocab.sheet", { count: data.sheet_terms })}</p>
          <p className="text-xs text-ink-3 break-all">
            <code>{data.sheet}</code>
          </p>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => engineGet("/terms/open")}
          >
            {t("vocab.openSheet")}
          </Button>
        </div>
      </SettingsGroup>

      <SettingsGroup title={t("vocab.dictationTitle")}>
        <FillerWordRemoval descriptionMode="tooltip" grouped />
      </SettingsGroup>
    </div>
  );
};
