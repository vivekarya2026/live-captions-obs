import React, { useState, useEffect } from "react";
import { getVersion } from "@tauri-apps/api/app";
import { useTranslation } from "react-i18next";

import ModelSelector from "../model-selector";
import UpdateChecker from "../update-checker";
import NoticeChip from "./NoticeChip";
import TranscriptionStatus from "./TranscriptionStatus";
import { useEngine } from "../../hooks/useEngine";
import { useSettings } from "../../hooks/useSettings";
import { SpeechModelSummary } from "../speech/SpeechModels";

interface FooterProps {
  onShowHistory: () => void;
  onShowModels: () => void;
  onShowLive?: () => void;
}

const Footer: React.FC<FooterProps> = ({
  onShowHistory,
  onShowModels,
  onShowLive,
}) => {
  const { t } = useTranslation();
  const [version, setVersion] = useState("");
  const { state: engine } = useEngine(2000);
  const { getSetting } = useSettings();
  // Dictation set to a type-only model: that's the one worth showing here.
  const typeOnly = getSetting("speech_engine") === "built_in";

  useEffect(() => {
    getVersion()
      .then(setVersion)
      .catch((error) => console.error("Failed to get app version:", error));
  }, []);

  return (
    <div className="w-full border-t border-line pt-3">
      <div className="flex justify-between items-center text-xs px-4 pb-3 text-ink-2">
        <div className="flex items-center gap-4">
          {typeOnly ? (
            <ModelSelector />
          ) : (
            engine && (
              <SpeechModelSummary d={engine} onOpen={onShowModels} compact />
            )
          )}
          <TranscriptionStatus onShowHistory={onShowHistory} />
          {/* A song is on the stream: shown on every page (spec 3c) */}
          {engine?.songs?.song &&
            (engine.songs.state === "following" || engine.songs.state === "lost" ||
              engine.songs.state === "suggested") && (
              <button
                type="button"
                onClick={onShowLive}
                className={`truncate max-w-56 hover:text-text cursor-pointer ${
                  engine.songs.state === "suggested" ? "text-logo-primary" : ""
                }`}
              >
                {t("songs.now.footer", { title: engine.songs.song.title })}
              </button>
            )}
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <UpdateChecker />
            {version && (
              <>
                <span>•</span>
                {/* eslint-disable-next-line i18next/no-literal-string */}
                <span>v{version}</span>
              </>
            )}
          </div>
          <NoticeChip />
        </div>
      </div>
    </div>
  );
};

export default Footer;
