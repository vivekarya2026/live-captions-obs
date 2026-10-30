--[[
Live Captions for OBS (macOS + Windows). Loaded by OBS (Tools -> Scripts);
the installer adds it for you.

1. Starts the caption translator when OBS opens; it stops by itself when OBS
   closes (it watches the state file below).
2. First run: adds the LocalVocal speech filter to the microphone and the
   "Live Captions Overlay" browser source to the current scene.
3. Applies changes made in the "Live Captions" dock. The translator writes a
   request to <DATA>/obs_control.json:
     {"id": 7, "source": "Mic/Aux",
      "settings": {...LocalVocal filter settings...},
      "input_settings": {"device_id": "..."},   -- microphone device
      "volume": 0.8, "muted": false,            -- mixer
      "filter_enabled": true}                   -- Whisper on/off
   and this script applies it once, then writes the id to obs_ack.txt.
4. Every second writes <DATA>/obs_state.json (mic + LocalVocal state).
<DATA> is ~/.livecaptions (macOS) or %USERPROFILE%\.livecaptions (Windows).
]]
obs = obslua

local IS_WIN = package.config:sub(1, 1) == "\\"
local SEP = IS_WIN and "\\" or "/"
local home = (IS_WIN and os.getenv("USERPROFILE")) or os.getenv("HOME") or ""
local DATA = home .. SEP .. ".livecaptions"
local CONTROL = DATA .. SEP .. "obs_control.json"
local ACK = DATA .. SEP .. "obs_ack.txt"
local STATE = DATA .. SEP .. "obs_state.json"
local STOP = DATA .. SEP .. "stop_translator"
local SETUP_DONE = DATA .. SEP .. "obs_first_run_done"
local ALIVE = DATA .. SEP .. "translator_alive"
local last_restart = 0
local MIC = "Mic/Aux"
local FILTER = "LocalVocal Transcription"
local FILTER_ID = "transcription_filter_audio_filter"
local OVERLAY = "Live Captions Overlay"
local STR_KEYS = { "whisper_language_select", "whisper_model_path", "subtitle_sources",
                   "subtitle_output_filename", "initial_prompt" }
local BOOL_KEYS = { "no_timestamps", "no_context", "file_output_enable", "truncate_output_file" }
local NUM_KEYS = { "vad_threshold" }

local last_text = nil
local ticks = 0
local devices_cache = nil

local function read_file(path)
  local f = io.open(path, "rb")
  if not f then return nil end
  local s = f:read("*a")
  f:close()
  return s
end

local function write_file(path, text)
  local tmp = path .. ".tmp"
  local f = io.open(tmp, "wb")
  if not f then return end
  f:write(text)
  f:close()
  if IS_WIN then os.remove(path) end  -- os.rename doesn't replace on Windows
  os.rename(tmp, path)
end

local function exists(path)
  local f = io.open(path, "rb")
  if f then f:close() return true end
  return false
end

-- --------------------------------------------------------------------------
-- Translator process
-- --------------------------------------------------------------------------
local function root_dir()
  -- script_path() is <install>/obs/ ; the app is in <install>/app
  return script_path() .. ".." .. SEP
end

local function python_exe()
  local r = root_dir()
  -- installed: <Live Captions.app>/Contents/Resources/{obs,python,app} or <install>\{obs,python,app}
  local candidates = IS_WIN and { r .. "python\\pythonw.exe", r .. ".venv\\Scripts\\pythonw.exe" }
                             or { r .. "python/bin/python3", r .. ".venv/bin/python" }
  for _, p in ipairs(candidates) do
    if exists(p) then return p end
  end
  return nil
end

local function start_translator()
  os.remove(STOP)
  local py = python_exe()
  if py == nil then
    obs.script_log(obs.LOG_WARNING, "Live Captions: Python runtime not found next to the script")
    return
  end
  local app = root_dir() .. "app"
  if IS_WIN then
    -- ShellExecute with SW_HIDE: no console window flashes up
    local ffi = require("ffi")
    pcall(ffi.cdef, [[
      int ShellExecuteA(void* hwnd, const char* op, const char* file, const char* params,
                        const char* dir, int show);
    ]])
    ffi.load("shell32").ShellExecuteA(nil, "open", py, "-m livecaptions --with-obs", app, 0)
  else
    os.execute('cd "' .. app .. '" && nohup "' .. py .. '" -m livecaptions --with-obs ' ..
               '>/dev/null 2>&1 &')
  end
end

local function stop_translator()
  -- The translator exits within a moment of seeing this file (and also when
  -- obs_state.json stops being updated, e.g. after a crash).
  write_file(STOP, "stop\n")
end

-- --------------------------------------------------------------------------
-- Finding / creating sources
-- --------------------------------------------------------------------------
local function get_mic()
  local src = obs.obs_get_source_by_name(MIC)
  if src ~= nil then return src end
  return obs.obs_get_output_source(3)  -- the first "Mic/Auxiliary Audio" device (any language)
end

local function data_path(name)
  return DATA .. SEP .. name
end

local function first_run_setup()
  if exists(SETUP_DONE) then return end
  local done = true
  -- 1. microphone
  local mic = get_mic()
  if mic == nil then
    local s = obs.obs_data_create()
    mic = obs.obs_source_create(IS_WIN and "wasapi_input_capture" or "coreaudio_input_capture", MIC, s, nil)
    obs.obs_data_release(s)
    if mic ~= nil then obs.obs_set_output_source(3, mic) end
  end
  -- 2. LocalVocal filter (Whisper; used until Qwen3 has been downloaded)
  if mic ~= nil then
    local filt = obs.obs_source_get_filter_by_name(mic, FILTER)
    if filt == nil then
      local s = obs.obs_data_create()
      obs.obs_data_set_bool(s, "file_output_enable", true)
      obs.obs_data_set_string(s, "subtitle_output_filename", data_path("raw" .. SEP .. "speech.txt"))
      obs.obs_data_set_bool(s, "truncate_output_file", true)
      obs.obs_data_set_string(s, "subtitle_sources", "(file output only)")
      obs.obs_data_set_string(s, "whisper_language_select", "auto")
      obs.obs_data_set_string(s, "whisper_model_path", "Whisper Small q5 (181Mb)")
      obs.obs_data_set_bool(s, "no_context", true)
      obs.obs_data_set_bool(s, "process_while_muted", false)
      filt = obs.obs_source_create_private(FILTER_ID, FILTER, s)
      obs.obs_data_release(s)
      if filt ~= nil then
        obs.obs_source_filter_add(mic, filt)
      else
        obs.script_log(obs.LOG_WARNING, "Live Captions: LocalVocal plugin not found (Qwen3 still works)")
      end
    end
    if filt ~= nil then obs.obs_source_release(filt) end
    obs.obs_source_release(mic)
  else
    done = false
  end
  -- 3. caption overlay in the current scene
  local overlay = obs.obs_get_source_by_name(OVERLAY)
  if overlay == nil then
    local scene_src = obs.obs_frontend_get_current_scene()
    if scene_src ~= nil then
      local s = obs.obs_data_create()
      obs.obs_data_set_bool(s, "is_local_file", true)
      obs.obs_data_set_string(s, "local_file", data_path("overlay.html"))
      obs.obs_data_set_int(s, "width", 1920)
      obs.obs_data_set_int(s, "height", 1080)
      overlay = obs.obs_source_create("browser_source", OVERLAY, s, nil)
      obs.obs_data_release(s)
      if overlay ~= nil then
        obs.obs_scene_add(obs.obs_scene_from_source(scene_src), overlay)
      end
      obs.obs_source_release(scene_src)
    else
      done = false
    end
  end
  if overlay ~= nil then obs.obs_source_release(overlay) end
  if done then write_file(SETUP_DONE, os.date("%Y-%m-%d %H:%M:%S") .. "\n") end
end

-- --------------------------------------------------------------------------
-- Applying dock requests
-- --------------------------------------------------------------------------
local function apply_request()
  local text = read_file(CONTROL)
  if text == nil or text == last_text then return end
  last_text = text
  local data = obs.obs_data_create_from_json(text)
  if data == nil then return end
  local id = obs.obs_data_get_int(data, "id")
  local src = get_mic()
  local ok = false
  if src ~= nil then
    ok = true
    local input_settings = obs.obs_data_get_obj(data, "input_settings")
    if input_settings ~= nil then
      obs.obs_source_update(src, input_settings)
      obs.obs_data_release(input_settings)
    end
    if obs.obs_data_has_user_value(data, "volume") then
      obs.obs_source_set_volume(src, obs.obs_data_get_double(data, "volume"))
    end
    if obs.obs_data_has_user_value(data, "muted") then
      obs.obs_source_set_muted(src, obs.obs_data_get_bool(data, "muted"))
    end
    local filt = obs.obs_source_get_filter_by_name(src, FILTER)
    if filt ~= nil then
      local settings = obs.obs_data_get_obj(data, "settings")
      if settings ~= nil then
        obs.obs_source_update(filt, settings)
        obs.obs_data_release(settings)
      end
      if obs.obs_data_has_user_value(data, "filter_enabled") then
        obs.obs_source_set_enabled(filt, obs.obs_data_get_bool(data, "filter_enabled"))
      end
      obs.obs_source_release(filt)
    end
    obs.obs_source_release(src)
  end
  obs.obs_data_release(data)
  write_file(ACK, tostring(id) .. (ok and " ok" or " missing") .. "\n")
end

-- --------------------------------------------------------------------------
-- State for the dock
-- --------------------------------------------------------------------------
local function device_list(src)
  local arr = obs.obs_data_array_create()
  local props = obs.obs_source_properties(src)
  if props ~= nil then
    local p = obs.obs_properties_get(props, "device_id")
    if p ~= nil then
      for i = 0, obs.obs_property_list_item_count(p) - 1 do
        local item = obs.obs_data_create()
        obs.obs_data_set_string(item, "name", obs.obs_property_list_item_name(p, i))
        obs.obs_data_set_string(item, "id", obs.obs_property_list_item_string(p, i))
        obs.obs_data_array_push_back(arr, item)
        obs.obs_data_release(item)
      end
    end
    obs.obs_properties_destroy(props)
  end
  return arr
end

local function save_state(with_devices)
  local root = obs.obs_data_create()
  obs.obs_data_set_int(root, "time", os.time())
  local inputs = obs.obs_data_create()
  local src = get_mic()
  if src ~= nil then
    local info = obs.obs_data_create()
    local filt = obs.obs_source_get_filter_by_name(src, FILTER)
    obs.obs_data_set_bool(info, "has_filter", filt ~= nil)
    if filt ~= nil then
      local s = obs.obs_source_get_settings(filt)
      for _, k in ipairs(STR_KEYS) do obs.obs_data_set_string(info, k, obs.obs_data_get_string(s, k)) end
      for _, k in ipairs(BOOL_KEYS) do obs.obs_data_set_bool(info, k, obs.obs_data_get_bool(s, k)) end
      for _, k in ipairs(NUM_KEYS) do obs.obs_data_set_double(info, k, obs.obs_data_get_double(s, k)) end
      obs.obs_data_release(s)
      obs.obs_data_set_bool(info, "filter_enabled", obs.obs_source_enabled(filt))
      obs.obs_source_release(filt)
    end
    local is = obs.obs_source_get_settings(src)
    obs.obs_data_set_string(info, "device_id", obs.obs_data_get_string(is, "device_id"))
    obs.obs_data_release(is)
    obs.obs_data_set_double(info, "volume", obs.obs_source_get_volume(src))
    obs.obs_data_set_bool(info, "muted", obs.obs_source_muted(src))
    if with_devices or devices_cache == nil then
      local arr = device_list(src)
      local holder = obs.obs_data_create()
      obs.obs_data_set_array(holder, "d", arr)
      devices_cache = obs.obs_data_get_json(holder)
      obs.obs_data_array_release(arr)
      obs.obs_data_release(holder)
    end
    local holder = obs.obs_data_create_from_json(devices_cache)
    local arr = obs.obs_data_get_array(holder, "d")
    obs.obs_data_set_array(info, "devices", arr)
    obs.obs_data_array_release(arr)
    obs.obs_data_release(holder)
    obs.obs_data_set_obj(inputs, MIC, info)
    obs.obs_data_release(info)
    obs.obs_source_release(src)
  end
  obs.obs_data_set_obj(root, "inputs", inputs)
  obs.obs_data_release(inputs)
  write_file(STATE, obs.obs_data_get_json(root))
  obs.obs_data_release(root)
end

local function tick()
  apply_request()
  ticks = ticks + 1
  if ticks == 8 then first_run_setup() end              -- 2 s after load: scene is ready
  if ticks % 4 == 0 then save_state(ticks % 40 == 0) end -- devices re-listed every 10 s
  -- Watchdog: the translator rewrites translator_alive every 2 s. If it has
  -- stopped (crash, killed), start it again (at most every 30 s).
  if ticks % 40 == 0 and ticks >= 240 then
    local t = tonumber(read_file(ALIVE) or "") or 0
    if os.time() - t > 30 and os.time() - last_restart > 30 then
      last_restart = os.time()
      obs.script_log(obs.LOG_WARNING, "Live Captions: translator not running, starting it again")
      start_translator()
    end
  end
end

function script_description()
  return "<b>Live Captions</b>: English &harr; Hindi/Hinglish live captions. Starts the caption "
    .. "translator with OBS and applies the settings chosen in the <i>Live Captions</i> dock "
    .. "(View &rarr; Docks). Leave this script loaded."
end

function script_load(settings)
  if not IS_WIN then os.execute('mkdir -p "' .. DATA .. '/raw"') end  -- (the translator also creates it)
  last_text = read_file(CONTROL)  -- don't re-apply an old request at startup
  save_state(true)
  start_translator()
  obs.timer_add(tick, 250)
end

function script_unload()
  obs.timer_remove(tick)
  stop_translator()
end
