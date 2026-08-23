#define MyAppName "SweetVibe"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "DihanRamanayaka"
#define MyAppURL "https://github.com/RandomCatUser/SweetVibe"
#define MyAppExeName "SweetVibe.exe"
#define MyIconName "ico.ico"
#define MyBuildDir "dist\SweetVibe"

[Setup]
AppId={{8B1A2C3D-E4F5-4A6B-8C9D-0E1F2A3B4C5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=dist\installer
OutputBaseFilename=SweetVibe_Setup
SetupIconFile={#MyIconName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
AppMutex=SweetVibeAppMutex
PrivilegesRequired=admin
UsePreviousAppDir=yes
UsePreviousTasks=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel2=Welcome to the SweetVibe Setup Wizard!#13#10#13#10This will install SweetVibe Music Player on your computer.#13#10#13#10Click Next to continue.
FinishedLabel=Setup has finished installing SweetVibe on your computer.#13#10#13#10Enjoy your music

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Files]
Source: "{#MyBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyIconName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyIconName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyIconName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\songs"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  if CheckForMutexes('SweetVibeAppMutex') then
  begin
    MsgBox('SweetVibe is already running. Please close it before installing.', mbError, MB_OK);
    Result := False;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpWelcome then
    WizardForm.WelcomeLabel1.Caption := 'Welcome to SweetVibe';

  if CurPageID = wpFinished then
    WizardForm.FinishedLabel.Caption :=
      'SweetVibe has been installed successfully!' + #13#10 +
      'Click Finish to start enjoying your music.';
end;
