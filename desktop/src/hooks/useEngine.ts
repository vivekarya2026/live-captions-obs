import { useCallback, useEffect, useRef, useState } from "react";
import { commands } from "@/bindings";

/** What the Live Captions engine reports at /state (see App.state() in translator.py). */
export interface EngineState {
  mode: string;
  modes: Record<string, string>;
  hints: Record<string, string>;
  style: string;
  styles: Record<string, string>;
  style_hints: Record<string, string>;
  style_status: string;
  status: string;
  captions_on: boolean;
  caption: string;
  speech_model: string;
  speech_models: Record<string, { label: string; ready: boolean }>;
  speech_status: string;
  speech_loading: boolean;
  engine: "qwen" | "whisper";
  translator_ready: boolean;
  setup: {
    running: boolean;
    stage: string;
    percent: number;
    message: string;
    error: string;
    ready: Record<string, boolean>;
  };
  mic: {
    device_id: string;
    devices: { id: string; name: string }[];
    volume: number;
    muted: boolean;
    noise: string;
  };
  session: string;
  sessions_root: string;
  lines: number;
  obs: boolean;
  gdocs: GDocsState;
}

export interface GDocsState {
  configured: boolean;
  signed_in: boolean;
  way: "" | "script" | "google";
  writing: boolean;
  doc: string;
  doc_url: string;
  error: string;
  sent: number;
  show_time: boolean;
  waiting: number;
}

/** One call to the engine. `path` is a route + query, e.g. "/mode?set=hi-en". */
export async function engineGet<T = EngineState>(
  path: string,
): Promise<{ data: T | null; error: string | null }> {
  const reply = await commands.lcRequest(path);
  if (reply.data) {
    try {
      return { data: JSON.parse(reply.data) as T, error: null };
    } catch (e) {
      return { data: null, error: String(e) };
    }
  }
  return { data: null, error: reply.error ?? "no answer" };
}

/** The engine's state, refreshed every `intervalMs` while the page is open. */
export function useEngine(intervalMs = 1000) {
  const [state, setState] = useState<EngineState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const busy = useRef(false);

  const apply = useCallback(
    (r: { data: EngineState | null; error: string | null }) => {
      if (r.data) {
        setState(r.data);
        setError(null);
      } else {
        setError(r.error);
      }
    },
    [],
  );

  const refresh = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      apply(await engineGet("/state"));
    } finally {
      busy.current = false;
    }
  }, [apply]);

  /** Change something (e.g. "/style?set=natural") and show the new state. */
  const send = useCallback(
    async (path: string) => {
      const r = await engineGet(path);
      apply(r);
      return r;
    },
    [apply],
  );

  useEffect(() => {
    if (intervalMs <= 0) return; // 0 = don't ask the engine at all
    refresh();
    const id = window.setInterval(refresh, intervalMs);
    return () => window.clearInterval(id);
  }, [refresh, intervalMs]);

  return { state, error, refresh, send };
}
