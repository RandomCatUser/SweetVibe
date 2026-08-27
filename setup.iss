#define MyAppName "SweetVibe"
#define MyAppVersion "1.4.0"
#define MyAppPublisher "DihanRamanayaka"
#define MyAppURL "https://github.com/RandomCatUser/SweetVibe"
#define MyAppExeName "SweetVibe.exe"
#define MyIconName "ico.ico"
#define MyBuildDir "dist\SweetVibe"

[Setup]
AppId={{8B1A2C3D-E4F5-4A6B-8C9D-0E1F2A3B4C5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2025 {#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=dist\installer
OutputBaseFilename=Setup_Windows_x64
SetupIconFile={#MyIconName}
UninstallDisplayIcon={app}\{#MyIconName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
AppMutex=SweetVibeAppMutex
PrivilegesRequired=admin
UsePreviousAppDir=yes
UsePreviousTasks=yes
MinVersion=10.0.17763
RestartApplications=yes
CreateUninstallRegKey=yes

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

CloseApplications=force

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to {#MyAppName} v{#MyAppVersion}
WelcomeLabel2=This installer will guide you through the installation of {#MyAppName} on your computer.%n%n{#MyAppName} is a terminal-based music player with a built-in visualizer, playlist browser, and real-time audio spectrum.%n%nClick Next to continue.
FinishedHeadingLabel=Installation Complete
FinishedLabel={#MyAppName} has been successfully installed on your computer.%n%nClick Finish to close this wizard and start listening to your music.

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked
Name: "cleansetup"; Description: "&Clean installation (removes previous files, recommended)"; Flags: unchecked

[Files]
Source: "{#MyBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyIconName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyIconName}"
Name: "{group}\Open Songs Folder"; Filename: "{app}\songs"; IconFilename: "{app}\{#MyIconName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\{#MyIconName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyIconName}"; Tasks: desktopicon

[Registry]
Root: HKCR; Subkey: "Directory\shell\SweetVibe"; ValueType: string; ValueName: ""; ValueData: "Play in {#MyAppName}"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Directory\shell\SweetVibe"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyIconName}"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Directory\shell\SweetVibe\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\plugins\setup_online.ps1"""; Description: "Set up online music (Python and yt-dlp)"; Flags: waituntilterminated postinstall skipifsilent runasoriginaluser
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent runasoriginaluser
Filename: "{#MyAppURL}"; Description: "Visit GitHub Repository"; Flags: postinstall skipifsilent nowait shellexec runasoriginaluser

[Code]
const
  SHCNE_ASSOCCHANGED = $08000000;
  SHCNF_IDLIST = $0000;

procedure SHChangeNotify(wEventId: Longint; uFlags: UINT; dwItem1: Longint; dwItem2: Longint); external 'SHChangeNotify@shell32.dll stdcall';

function InitializeSetup(): Boolean;
begin
  Result := True;
  
  // Check if the app is currently running
  if CheckForMutexes('SweetVibeAppMutex') then
  begin
    MsgBox('SweetVibe is currently running. Please close it before installing.', mbError, MB_OK);
    Result := False;
    Exit; // Stop the installer from proceeding
  end;

  // Show a custom Welcome message box
  MsgBox('Welcome to {#MyAppName} v{#MyAppVersion}!' + #13#10 + #13#10 +
         'Thank you for downloading. You are about to install a terminal-based music player with a built-in visualizer, playlist browser, and real-time audio spectrum.' + #13#10 + #13#10 +
         'Click OK to start the setup wizard.',
         mbInformation, MB_OK);
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  if CheckForMutexes('SweetVibeAppMutex') then
  begin
    MsgBox('SweetVibe is currently running. Please close it before uninstalling.', mbError, MB_OK);
    Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    if WizardIsTaskSelected('cleansetup') then
    begin
      DelTree(ExpandConstant('{app}\*'), True, True, True);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if DirExists(ExpandConstant('{app}\songs')) then
    begin
      if MsgBox('Do you want to completely remove the downloaded songs folder as well?',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(ExpandConstant('{app}\songs'), True, True, True);
      end;
    end;
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
  end;
end;