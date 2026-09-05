

#define MyAppName "SweetVibe"
#define MyAppVersion "1.4.2"
#define MyAppPublisher "DihanRamanayaka"
#define MyAppURL "https://github.com/RandomCatUser/SweetVibe"
#define MyAppExeName "SweetVibe.exe"
#define MyBuildDir "dist\SweetVibe"

#define AppIcon "ico.ico"
#define SetupIcon "installer.ico"
#define UninstallIcon "uninstaller.ico"

; Fail fast with a clear message instead of a cryptic compile error
#if !FileExists(SetupIcon) || !FileExists(UninstallIcon) || !FileExists(AppIcon)
  #error "installer.ico, uninstaller.ico and ico.ico must be next to this script."
#endif
#if !DirExists(MyBuildDir)
  #error "dist\SweetVibe was not found - build the app before compiling the installer."
#endif

[Setup]
AppId={{8B1A2C3D-E4F5-4A6B-8C9D-0E1F2A3B4C5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} {#MyAppVersion} Installer
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2025 {#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
DisableWelcomePage=no
OutputDir=dist\installer
OutputBaseFilename=Setup_Windows_x64
SetupIconFile={#SetupIcon}
UninstallDisplayIcon={app}\{#UninstallIcon}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
WizardResizable=yes
AppMutex=SweetVibeAppMutex
PrivilegesRequired=admin
UsePreviousAppDir=yes
UsePreviousTasks=yes
MinVersion=10.0.17763
RestartApplications=yes

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to {#MyAppName} v{#MyAppVersion}
WelcomeLabel2=This installer will guide you through the installation of {#MyAppName} on your computer.%n%n{#MyAppName} is a terminal-based music player with a built-in visualizer, playlist browser, and real-time audio spectrum.%n%nClick Next to continue.
FinishedHeadingLabel=Installation Complete
FinishedLabel={#MyAppName} has been successfully installed on your computer.%n%nClick Finish to close this wizard and start listening to your music.
FinishedLabelNoIcons={#MyAppName} has been successfully installed on your computer.%n%nClick Finish to close this wizard and start listening to your music.

[Tasks]
Name: "cleansetup"; Description: "&Clean installation (removes old program files, keeps your songs)"; Flags: checkedonce
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Files]
Source: "{#MyBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "setup_online.ps1"
Source: "{#AppIcon}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#UninstallIcon}"; DestDir: "{app}"; Flags: ignoreversion

; Wipe files left behind by older versions before copying the new ones
[InstallDelete]
Type: filesandordirs; Name: "{app}\plugins"

[Dirs]
Name: "{app}"; Permissions: users-modify
Name: "{app}\songs"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#AppIcon}"; Comment: "{#MyAppName} - terminal music player with visualizer"
Name: "{group}\Open Songs Folder"; Filename: "{app}\songs"; IconFilename: "{app}\{#AppIcon}"; Comment: "Open your {#MyAppName} songs folder"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\{#UninstallIcon}"; Comment: "Uninstall {#MyAppName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#AppIcon}"; Comment: "{#MyAppName} - terminal music player with visualizer"; Tasks: desktopicon

[Registry]
Root: HKLM; Subkey: "Software\Classes\Directory\shell\SweetVibe"; ValueType: string; ValueName: ""; ValueData: "Play in {#MyAppName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\shell\SweetVibe"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#AppIcon}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\shell\SweetVibe\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey
; Also show the option when right-clicking the empty space INSIDE a folder
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\SweetVibe"; ValueType: string; ValueName: ""; ValueData: "Play in {#MyAppName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\SweetVibe"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#AppIcon}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\SweetVibe\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%V"""; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent runasoriginaluser
Filename: "{#MyAppURL}"; Description: "Visit GitHub Repository"; Flags: postinstall skipifsilent nowait shellexec runasoriginaluser

[Code]
const
  SHCNE_ASSOCCHANGED = $08000000;
  SHCNF_IDLIST = $0000;

procedure SHChangeNotify(wEventId: Longint; uFlags: UINT; dwItem1: Longint; dwItem2: Longint);
  external 'SHChangeNotify@shell32.dll stdcall';

// Deletes everything inside {app} EXCEPT the songs folder.
// (DelTree doesn't support wildcards, so we walk the folder manually.)
procedure CleanInstallDir();
var
  AppDir, FullPath: string;
  FR: TFindRec;
begin
  AppDir := ExpandConstant('{app}');
  if not DirExists(AppDir) then
    Exit;

  if FindFirst(AddBackslash(AppDir) + '*', FR) then
  try
    repeat
      if (FR.Name <> '.') and (FR.Name <> '..') and
         (Lowercase(FR.Name) <> 'songs') then
      begin
        FullPath := AddBackslash(AppDir) + FR.Name;
        DelTree(FullPath, True, True, True);
      end;
    until not FindNext(FR);
  finally
    FindClose(FR);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    if WizardIsTaskSelected('cleansetup') then
      CleanInstallDir();
  end
  else if CurStep = ssPostInstall then
  begin
    // Refresh Explorer so the new right-click entries show up immediately
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if DirExists(ExpandConstant('{app}\songs')) then
    begin
      if MsgBox('Do you also want to delete your downloaded songs?',
                mbConfirmation, MB_YESNO) = IDYES then
        DelTree(ExpandConstant('{app}\songs'), True, True, True);
    end;
  end;
end;