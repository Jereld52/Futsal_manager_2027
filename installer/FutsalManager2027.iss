; Installateur Futsal Manager 2027 (+ éditeur optionnel)
; Compilation : ISCC.exe installer\FutsalManager2027.iss

#define MyAppName "Futsal Manager 2027"
#define MyAppVersion "2027.2"
#define MyAppPublisher "JGames"
#define MyAppExeName "FutsalManager2027.exe"
#define MyEditorExeName "FutsalManager2027Editeur.exe"

[Setup]
AppId={{8E3B5C2A-7F4D-4A91-9B6E-2C1D5A7F3B10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\installer_output
OutputBaseFilename=FutsalManager2027_Setup_{#MyAppVersion}
SetupIconFile=..\data\fm27.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
VersionInfoVersion=2027.2.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Installateur {#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "editeur"; Description: "Installer l'éditeur de sauvegarde (outil avancé)"; GroupDescription: "Outils"; Flags: unchecked

[Files]
Source: "..\build_dist\FutsalManager2027\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build_dist\FutsalManager2027Editeur\*"; DestDir: "{app}\Editeur"; Flags: ignoreversion recursesubdirs createallsubdirs; Tasks: editeur
Source: "..\data\fm27.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\build_assets\LISEZMOI_BETA.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\fm27.ico"; WorkingDir: "{app}"
Name: "{group}\{#MyAppName} — Éditeur"; Filename: "{app}\Editeur\{#MyEditorExeName}"; IconFilename: "{app}\fm27.ico"; WorkingDir: "{app}\Editeur"; Tasks: editeur
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\fm27.ico"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent
