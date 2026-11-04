; Live Captions for Windows (Inno Setup 6). Built by installer\windows\build.ps1.
; Installs for the current user only (no admin needed), into
; %LOCALAPPDATA%\Programs\Live Captions\{python,app,obs}.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
; The desktop app (live-captions.exe + resources\) sits next to python\ and app\
#define LaunchExe "{app}\live-captions.exe"
#define LaunchArgs ""
#define LaunchDir "{app}"

[Setup]
AppId={{6C1E2F4A-6F2B-4E7B-9C1D-7A51C0B2D3E4}
AppName=Live Captions
AppVersion={#AppVersion}
AppPublisher=Live Captions for OBS
AppPublisherURL=https://github.com/vivekarya2026/live-captions-obs
DefaultDirName={localappdata}\Programs\Live Captions
DefaultGroupName=Live Captions
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutDir}
OutputBaseFilename=LiveCaptions-{#AppVersion}-Windows-x64-Setup
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile={#BuildDir}\LICENSE.txt
WizardStyle=modern
UninstallDisplayName=Live Captions
CloseApplications=no

[Messages]
WelcomeLabel2=Live captions and translation, English <-> Hindi / Hinglish, with the Nirankari vocabulary.%n%nWorks with OBS (captions on your stream), without OBS, and can write into a Google Doc.%n%nAfter installing, Live Captions downloads its speech and translation models once (about 4 GB). Everything then runs on this PC.

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "localvocal"; Description: "Install the LocalVocal OBS plugin (captions in OBS while the models download; asks for permission)"; GroupDescription: "OBS:"; Check: ObsInstalled

[Files]
Source: "{#BuildDir}\python\*"; DestDir: "{app}\python"; Flags: recursesubdirs ignoreversion
Source: "{#BuildDir}\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs ignoreversion
Source: "{#BuildDir}\obs\*"; DestDir: "{app}\obs"; Flags: recursesubdirs ignoreversion
Source: "{#BuildDir}\LICENSE.txt"; DestDir: "{app}"
Source: "{#BuildDir}\desktop\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{userprograms}\Live Captions"; Filename: "{#LaunchExe}"; Parameters: "{#LaunchArgs}"; WorkingDir: "{#LaunchDir}"; Comment: "Live captions, translation and dictation"
Name: "{userdesktop}\Live Captions"; Filename: "{#LaunchExe}"; Parameters: "{#LaunchArgs}"; WorkingDir: "{#LaunchDir}"; Tasks: desktopicon

[Run]
; Stop an older copy, add the script + dock to OBS (postponed if OBS is open), LocalVocal, then open the window
Filename: "{cmd}"; Parameters: "/C echo stop> ""%USERPROFILE%\.livecaptions\stop_translator"""; Flags: runhidden; Check: DataDirExists
Filename: "{app}\python\python.exe"; Parameters: "-m livecaptions.obs_setup --later-if-open --script ""{app}\obs\live_captions.lua"""; WorkingDir: "{app}\app"; Flags: runhidden waituntilterminated; StatusMsg: "Adding Live Captions to OBS..."; Check: ObsInstalled
Filename: "{app}\python\python.exe"; Parameters: "-m livecaptions.install_localvocal"; WorkingDir: "{app}\app"; Flags: runhidden waituntilterminated; StatusMsg: "Installing LocalVocal..."; Tasks: localvocal
Filename: "{cmd}"; Parameters: "/C del /Q ""%USERPROFILE%\.livecaptions\stop_translator"""; Flags: runhidden; Check: DataDirExists
Filename: "{#LaunchExe}"; Parameters: "{#LaunchArgs}"; WorkingDir: "{#LaunchDir}"; Description: "Open Live Captions now"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM live-captions.exe"; Flags: runhidden; RunOnceId: "StopDesktopApp"
Filename: "{cmd}"; Parameters: "/C echo stop> ""%USERPROFILE%\.livecaptions\stop_translator"""; Flags: runhidden; RunOnceId: "StopLC"
Filename: "{app}\python\python.exe"; Parameters: "-m livecaptions.obs_setup --remove"; WorkingDir: "{app}\app"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveFromOBS"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\resources"

[Code]
function ObsInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{commonpf64}\obs-studio\bin\64bit\obs64.exe'));
end;

// A running desktop app locks live-captions.exe: close it before copying files.
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM live-captions.exe', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Result := '';
end;

function DataDirExists: Boolean;
begin
  Result := DirExists(ExpandConstant('{%USERPROFILE}\.livecaptions'));
end;
