#define MyAppName "SweetVibe"
#define MyAppVersion "1.2.1"
#define MyAppPublisher "DihanRamanayaka"
#define MyAppURL "https://github.com/RandomCatUser/SweetVibe"
#define MyAppExeName "SweetVibe.exe"
#define MyIconName "ico.ico"
#define MyBuildDir "dist\SweetVibe"

[Setup]
; NOTE: The AppId uniquely identifies this application. Do not use the same AppId in installers for other applications.
AppId={{8B1A2C3D-E4F5-4A6B-8C9D-0E1F2A3B4C5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2024 {#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=dist\installer
OutputBaseFilename=Setup_Windows_x64
SetupIconFile={#MyIconName}
UninstallDisplayIcon={app}\{#MyIconName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
AppMutex=SweetVibeAppMutex
PrivilegesRequired=admin
UsePreviousAppDir=yes
UsePreviousTasks=yes

; Modern 64-bit architecture settings
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Automatically closes running instances of SweetVibe using Windows Restart Manager
CloseApplications=force

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
; ADDED: Custom Welcome Messages
WelcomeLabel1=Welcome to the SweetVibe Setup
WelcomeLabel2=This installer will guide you through the steps to install SweetVibe Music Player on your computer.%n%nIt is recommended that you close all other applications before continuing.%n%nClick Next to continue.
FinishedHeadingLabel=Completing the SweetVibe Setup
FinishedLabel=Setup has finished installing SweetVibe on your computer.%n%nEnjoy your music!

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Files]
Source: "{#MyBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyIconName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyIconName}"
Name: "{group}\Open Songs Folder"; Filename: "{app}\songs"; IconFilename: "{app}\{#MyIconName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\{#MyIconName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyIconName}"; Tasks: desktopicon

[Registry]
; Add "Play in SweetVibe" to right-click context menu for folders
Root: HKCR; Subkey: "Directory\shell\SweetVibe"; ValueType: string; ValueName: ""; ValueData: "Play in {#MyAppName}"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Directory\shell\SweetVibe"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyIconName}"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Directory\shell\SweetVibe\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey

[Run]
; runasoriginaluser ensures the app doesn't launch with Admin privileges
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent runasoriginaluser
Filename: "{#MyAppURL}"; Description: "Visit GitHub Repository"; Flags: postinstall skipifsilent nowait shellexec runasoriginaluser

[Code]
// Windows API call to refresh Windows Explorer
const
  SHCNE_ASSOCCHANGED = $08000000;
  SHCNF_IDLIST = $0000;

procedure SHChangeNotify(wEventId: Longint; uFlags: UINT; dwItem1: Longint; dwItem2: Longint); external 'SHChangeNotify@shell32.dll stdcall';

function InitializeSetup(): Boolean;
begin
  Result := True;
  if CheckForMutexes('SweetVibeAppMutex') then
  begin
    MsgBox('SweetVibe is currently running. Please close it before installing.', mbError, MB_OK);
    Result := False;
  end;
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

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Ask the user if they want to keep their downloaded songs
    if DirExists(ExpandConstant('{app}\songs')) then
    begin
      if MsgBox('Do you want to completely remove the downloaded songs folder as well?', 
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(ExpandConstant('{app}\songs'), True, True, True);
      end;
    end;
    // Refresh shell after uninstalling
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
  end;
end;