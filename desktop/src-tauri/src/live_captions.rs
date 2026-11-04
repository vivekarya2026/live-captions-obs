//! The Live Captions engine: the Python program in `app/livecaptions` (Qwen3-ASR
//! speech, NLLB translation, the Nirankari vocabulary, caption styles, OBS and
//! Google Docs). It runs as its own local process and serves
//! http://127.0.0.1:8765 (the same server the OBS dock uses).
//!
//! This module finds that program, starts it with `--desktop <our pid>` (so it
//! stops when this app quits), and forwards calls from the UI:
//!
//! * `lc_request` – any of the engine's GET routes (`/state`, `/mode?set=…`,
//!   `/style?set=…`, `/speech?model=…`, `/mic?…`, `/gdocs?…`, `/session/…`,
//!   `/captions?on=…`, `/terms`, …): see `translator.py` `do_GET`.
//! * `lc_save_terms` – the Custom Words list (`POST /terms`).
//! * `dictate` – push-to-talk audio → finished, translated text (`POST /dictate`).

use log::{info, warn};
use serde::{Deserialize, Serialize};
use specta::Type;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Manager};

pub const PORT: u16 = 8765;

fn base() -> String {
    let port = std::env::var("LIVECAPTIONS_PORT")
        .ok()
        .and_then(|p| p.parse::<u16>().ok())
        .unwrap_or(PORT);
    format!("http://127.0.0.1:{port}")
}

/// Where the engine lives: its Python and the folder containing `livecaptions`.
#[derive(Debug, Clone)]
struct EngineLocation {
    python: PathBuf,
    app_dir: PathBuf,
}

fn python_in(dir: &Path) -> Option<PathBuf> {
    let candidates: &[&str] = if cfg!(windows) {
        &["pythonw.exe", "python.exe", "Scripts/pythonw.exe", "Scripts/python.exe"]
    } else {
        &["bin/python3", "bin/python"]
    };
    candidates
        .iter()
        .map(|c| dir.join(c))
        .find(|p| p.is_file())
}

fn locate(app: &AppHandle) -> Option<EngineLocation> {
    // 1. LIVECAPTIONS_HOME=<repo or install folder> (developers, custom installs)
    // 2. bundled next to this app (installer: Resources/{python,app})
    // 3. the source checkout this app was built from (`bun run tauri dev`)
    // 4. a separate Live Captions install (~/Applications, %LOCALAPPDATA%\Programs)
    let mut roots: Vec<PathBuf> = Vec::new();
    if let Ok(home) = std::env::var("LIVECAPTIONS_HOME") {
        roots.push(PathBuf::from(home));
    }
    if let Ok(res) = app.path().resource_dir() {
        roots.push(res.join("engine"));
        roots.push(res);
    }
    roots.push(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    if cfg!(target_os = "macos") {
        roots.push(PathBuf::from("/Applications/Live Captions.app/Contents/Resources"));
    }
    if let Ok(local) = std::env::var("LOCALAPPDATA") {
        roots.push(PathBuf::from(local).join("Programs/Live Captions"));
    }
    for root in roots {
        let app_dir = root.join("app");
        if !app_dir.join("livecaptions/translator.py").is_file()
            && !app_dir.join("livecaptions/__main__.py").is_file()
        {
            continue;
        }
        // installer: <root>/python ; source checkout: <root>/.venv
        for py_dir in [root.join("python"), root.join(".venv")] {
            if let Some(python) = python_in(&py_dir) {
                return Some(EngineLocation { python, app_dir });
            }
        }
    }
    None
}

#[derive(Default)]
pub struct LiveCaptionsEngine {
    child: Mutex<Option<Child>>,
    last_error: Mutex<Option<String>>,
}

impl LiveCaptionsEngine {
    /// Start the engine unless one is already serving (e.g. started by OBS).
    pub fn ensure_started(&self, app: &AppHandle) {
        if ping() {
            return;
        }
        let mut child = self.child.lock().unwrap();
        if let Some(c) = child.as_mut() {
            if matches!(c.try_wait(), Ok(None)) {
                return; // still starting up
            }
        }
        let Some(loc) = locate(app) else {
            let msg = "Live Captions engine not found. Install Live Captions, or set \
                       LIVECAPTIONS_HOME to its folder."
                .to_string();
            warn!("{msg}");
            *self.last_error.lock().unwrap() = Some(msg);
            return;
        };
        info!(
            "Starting Live Captions engine: {} -m livecaptions (in {})",
            loc.python.display(),
            loc.app_dir.display()
        );
        let mut cmd = Command::new(&loc.python);
        cmd.args(["-m", "livecaptions", "--desktop", &std::process::id().to_string()])
            .current_dir(&loc.app_dir)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
        }
        match cmd.spawn() {
            Ok(c) => {
                *child = Some(c);
                *self.last_error.lock().unwrap() = None;
            }
            Err(e) => {
                let msg = format!("Could not start the Live Captions engine: {e}");
                warn!("{msg}");
                *self.last_error.lock().unwrap() = Some(msg);
            }
        }
    }

    pub fn last_error(&self) -> Option<String> {
        self.last_error.lock().unwrap().clone()
    }

    /// Ask the engine to stop (it also stops by itself once this app exits).
    pub fn stop(&self) {
        let _ = http_get("/quit", Duration::from_secs(2));
        if let Some(mut c) = self.child.lock().unwrap().take() {
            let deadline = Instant::now() + Duration::from_secs(3);
            while Instant::now() < deadline {
                if matches!(c.try_wait(), Ok(Some(_))) {
                    return;
                }
                std::thread::sleep(Duration::from_millis(100));
            }
            let _ = c.kill();
        }
    }
}

fn client(timeout: Duration) -> reqwest::blocking::Client {
    reqwest::blocking::Client::builder()
        .timeout(timeout)
        .no_proxy()
        .build()
        .expect("http client")
}

fn ping() -> bool {
    http_get("/state", Duration::from_millis(800)).is_ok()
}

fn http_get(path_and_query: &str, timeout: Duration) -> Result<serde_json::Value, String> {
    let resp = client(timeout)
        .get(format!("{}{}", base(), path_and_query))
        .send()
        .map_err(|e| e.to_string())?;
    if !resp.status().is_success() {
        return Err(format!("engine answered {}", resp.status()));
    }
    let is_json = resp
        .headers()
        .get(reqwest::header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .map_or(false, |v| v.contains("json"));
    if is_json {
        resp.json::<serde_json::Value>().map_err(|e| e.to_string())
    } else {
        // e.g. /gdocs/script (the Apps Script text): passed on as a JSON string
        resp.text().map(serde_json::Value::String).map_err(|e| e.to_string())
    }
}

fn http_post(path: &str, body: Vec<u8>, timeout: Duration) -> Result<serde_json::Value, String> {
    let resp = client(timeout)
        .post(format!("{}{}", base(), path))
        .body(body)
        .send()
        .map_err(|e| e.to_string())?;
    if !resp.status().is_success() {
        return Err(format!("engine answered {}", resp.status()));
    }
    resp.json::<serde_json::Value>().map_err(|e| e.to_string())
}

/// Result of one push-to-talk recording.
#[derive(Debug, Clone, Deserialize)]
pub struct Dictation {
    pub ok: bool,
    #[serde(default)]
    pub transcript: String,
    #[serde(default)]
    pub text: String,
    #[serde(default)]
    pub lang: String,
    #[serde(default)]
    pub error: Option<String>,
}

/// Blocking: send one recording (16 kHz mono f32) and get the finished text.
pub fn dictate(app: &AppHandle, samples: &[f32]) -> Result<Dictation, String> {
    let engine = app.state::<LiveCaptionsEngine>();
    engine.ensure_started(app);
    let mut body = Vec::with_capacity(samples.len() * 4);
    for s in samples {
        body.extend_from_slice(&s.to_le_bytes());
    }
    // Speech time plus translation and style; generous for long recordings on slow PCs.
    let secs = 30 + (samples.len() as u64 / 16_000) * 2;
    let value = http_post("/dictate", body, Duration::from_secs(secs)).map_err(|e| {
        engine
            .last_error()
            .unwrap_or_else(|| format!("Live Captions engine not reachable ({e})"))
    })?;
    let d: Dictation = serde_json::from_value(value).map_err(|e| e.to_string())?;
    if !d.ok {
        return Err(d.error.unwrap_or_else(|| "dictation failed".into()));
    }
    Ok(d)
}

// ---- commands for the UI ---------------------------------------------------

/// Paths the UI may call: the engine's own routes, nothing else.
const ALLOWED: &[&str] = &[
    "/state",
    "/mode",
    "/style",
    "/speech",
    "/mic",
    "/captions",
    "/session/new",
    "/session/open",
    "/setup/retry",
    "/gdocs",
    "/gdocs/open",
    "/gdocs/script",
    "/terms",
    "/terms/open",
    "/translation",
    "/models/delete",
    "/songs",
    "/songs/song",
    "/songs/mode",
    "/songs/confirm",
    "/songs/reject",
    "/songs/next",
    "/songs/back",
    "/songs/stop",
    "/songs/start",
    "/songs/delete",
    "/songs/open",
    "/songs/example",
];

/// POST routes the window may call with a JSON body (`lc_post`).
const ALLOWED_POST: &[&str] = &["/songs/import", "/songs/save"];

#[derive(Serialize, Type)]
pub struct EngineReply {
    /// The engine's JSON answer as text (shape: see `App.state()` in translator.py).
    pub data: Option<String>,
    /// Why there is no answer (engine starting, not installed, …).
    pub error: Option<String>,
}

#[tauri::command]
#[specta::specta]
pub async fn lc_request(app: AppHandle, path: String) -> EngineReply {
    let route = path.split('?').next().unwrap_or("");
    if !ALLOWED.contains(&route) {
        return EngineReply {
            data: None,
            error: Some(format!("not allowed: {route}")),
        };
    }
    tauri::async_runtime::spawn_blocking(move || {
        let engine = app.state::<LiveCaptionsEngine>();
        match http_get(&path, Duration::from_secs(15)) {
            Ok(v) => EngineReply {
                data: Some(v.to_string()),
                error: None,
            },
            Err(e) => {
                engine.ensure_started(&app);
                EngineReply {
                    data: None,
                    error: Some(engine.last_error().unwrap_or_else(|| {
                        format!("Starting the Live Captions engine… ({e})")
                    })),
                }
            }
        }
    })
    .await
    .unwrap_or(EngineReply {
        data: None,
        error: Some("internal error".into()),
    })
}

#[derive(Serialize, Deserialize, Type, Clone)]
pub struct CustomTerm {
    pub term: String,
    pub english: String,
    pub hindi: String,
}

#[tauri::command]
#[specta::specta]
pub async fn lc_save_terms(terms: Vec<CustomTerm>) -> EngineReply {
    tauri::async_runtime::spawn_blocking(move || {
        let body = serde_json::to_vec(&terms).unwrap_or_default();
        match http_post("/terms", body, Duration::from_secs(15)) {
            Ok(v) => EngineReply {
                data: Some(v.to_string()),
                error: None,
            },
            Err(e) => EngineReply {
                data: None,
                error: Some(e),
            },
        }
    })
    .await
    .unwrap_or(EngineReply {
        data: None,
        error: Some("internal error".into()),
    })
}

/// A JSON POST to the engine (song import and save). Only `ALLOWED_POST` routes.
#[tauri::command]
#[specta::specta]
pub async fn lc_post(path: String, body: String) -> EngineReply {
    if !ALLOWED_POST.contains(&path.as_str()) {
        return EngineReply {
            data: None,
            error: Some(format!("not allowed: {path}")),
        };
    }
    tauri::async_runtime::spawn_blocking(move || {
        // Reading a big PDF or Word file can take a while.
        match http_post(&path, body.into_bytes(), Duration::from_secs(120)) {
            Ok(v) => EngineReply {
                data: Some(v.to_string()),
                error: None,
            },
            Err(e) => EngineReply {
                data: None,
                error: Some(e),
            },
        }
    })
    .await
    .unwrap_or(EngineReply {
        data: None,
        error: Some("internal error".into()),
    })
}

/// The OBS overlay page (Browser Source URL) and the engine's own control page.
#[derive(Serialize, Type)]
pub struct EngineLinks {
    pub control_page: String,
    pub overlay_file: String,
}

#[tauri::command]
#[specta::specta]
pub fn lc_links() -> EngineLinks {
    let home = std::env::var(if cfg!(windows) { "USERPROFILE" } else { "HOME" }).unwrap_or_default();
    let data = std::env::var("LIVECAPTIONS_DATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(home).join(".livecaptions"));
    EngineLinks {
        control_page: format!("{}/", base()),
        overlay_file: data.join("overlay.html").to_string_lossy().to_string(),
    }
}
