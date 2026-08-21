; --- SweetVibe Music Player Installer (FINAL FIXED) ---

#define MyAppName "SweetVibe"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "RandomCatUser"
#define MyAppURL "https://github.com/RandomCatUser/SweetVibe"
#define MyAppExeName "main.exe"
#define MyIconName "ico.ico"

[Setup]
AppId={{8B1A2C3D-E4F5-4G6H-7I8J-9K0L1M2N3O4P}
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

OutputDir=Output
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
Source: "{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyIconName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "songs\*"; DestDir: "{app}\songs"; Flags: ignoreversion recursesubdirs createallsubdirs

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
  begin
    WizardForm.WelcomeLabel1.Caption := 'Welcome to SweetVibe';
  end;

  if CurPageID = wpFinished then
  begin
    WizardForm.FinishedLabel.Caption :=
      'SweetVibe has been installed successfully!' + #13#10 +
      'Click Finish to start enjoying your music.';
  end;
end;