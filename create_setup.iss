[Setup]
AppName=Restaurant POS System
AppVersion=3.0
DefaultDirName={autopf}\RestaurantPOS
DefaultGroupName=Restaurant POS
OutputDir=dist
OutputBaseFilename=RestaurantPOS_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\RestaurantPOS.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\RestaurantPOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Restaurant POS System"; Filename: "{app}\RestaurantPOS.exe"; IconFilename: "{app}\icon.ico"
Name: "{group}\{cm:UninstallProgram,Restaurant POS System}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Restaurant POS System"; Filename: "{app}\RestaurantPOS.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\RestaurantPOS.exe"; Description: "{cm:LaunchProgram,Restaurant POS System}"; Flags: nowait postinstall skipifsilent
