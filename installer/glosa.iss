; Windows installer for glosa (Inno Setup 6).
; Installs Docker Desktop when it is missing, copies the launcher and the compose file,
; and lets the reader pick a Light or Recommended set of extras. Build with:
;   iscc /DAppVersion=0.1.0 installer\glosa.iss

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{6C0D9B4E-2F3A-4E8B-9C51-7A1F0B9D2E64}
AppName=glosa
AppVersion={#AppVersion}
AppPublisher=glosa
AppPublisherURL=https://glosa.suchima.com
AppSupportURL=https://github.com/CoKeFish/glosa/issues
DefaultDirName={autopf}\glosa
DefaultGroupName=glosa
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=glosa-setup-{#AppVersion}
SetupIconFile=glosa.ico
UninstallDisplayIcon={app}\glosa.ico
WizardStyle=modern
WizardSmallImageFile=wizard-small.bmp
Compression=lzma2
SolidCompression=yes
; Docker Desktop's installer needs administrator rights.
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
LicenseFile=..\LICENSE

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
en.TypeRecommended=Recommended: the best experience (about 10 GB of extras)
es.TypeRecommended=Recomendada: la mejor experiencia (unos 10 GB de extras)
en.TypeLight=Light: small, still offline (about 2 GB of extras)
es.TypeLight=Ligera: ocupa poco y funciona sin conexión (unos 2 GB de extras)
en.TypeCore=Only glosa: add extras later from the app
es.TypeCore=Solo glosa: añade extras más tarde desde la app
en.CompCore=glosa
es.CompCore=glosa
en.DockerMissing=glosa runs in Docker Desktop, which is not installed. Setup will download it from docker.com (about 600 MB) and install it.%n%nWindows may ask you to restart afterwards.
es.DockerMissing=glosa funciona dentro de Docker Desktop, que no está instalado. El instalador lo descargará de docker.com (unos 600 MB) y lo instalará.%n%nPuede que Windows te pida reiniciar después.
en.DockerFailed=Docker Desktop could not be installed. Install it from docker.com and run this installer again.
es.DockerFailed=No se pudo instalar Docker Desktop. Instálalo desde docker.com y vuelve a ejecutar este instalador.
en.InstallingDocker=Installing Docker Desktop (this takes a few minutes)…
es.InstallingDocker=Instalando Docker Desktop (tarda unos minutos)…
en.Launch=Open glosa now
es.Launch=Abrir glosa ahora
en.RemoveData=Also delete your books, vocabulary and downloaded extras?%n%nChoose No to keep them for a future install.
es.RemoveData=¿Borrar también tus libros, tu vocabulario y los extras descargados?%n%nElige No para conservarlos para una instalación futura.
en.Stop=Stop glosa
es.Stop=Detener glosa
en.Update=Update glosa
es.Update=Actualizar glosa

[Types]
Name: "recommended"; Description: "{cm:TypeRecommended}"
Name: "light"; Description: "{cm:TypeLight}"
Name: "core"; Description: "{cm:TypeCore}"

[Components]
Name: "core"; Description: "{cm:CompCore}"; Types: recommended light core; Flags: fixed

[Files]
Source: "compose.yaml"; DestDir: "{app}"; Flags: ignoreversion
Source: "glosa.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "glosa.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\glosa"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File ""{app}\glosa.ps1"" start"; IconFilename: "{app}\glosa.ico"
Name: "{group}\{cm:Update}"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\glosa.ps1"" update"; IconFilename: "{app}\glosa.ico"
Name: "{group}\{cm:Stop}"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\glosa.ps1"" stop"; IconFilename: "{app}\glosa.ico"
Name: "{autodesktop}\glosa"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File ""{app}\glosa.ps1"" start"; IconFilename: "{app}\glosa.ico"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\glosa.ps1"" start"; Description: "{cm:Launch}"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\glosa.ps1"" uninstall -Quiet {code:RemoveDataFlag}"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveContainers"

[UninstallDelete]
Type: files; Name: "{app}\.env"
Type: files; Name: "{app}\preset.txt"
Type: files; Name: "{app}\.started"

[Code]
const
  DockerUrl = 'https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe';

var
  RemoveData: Boolean;

function DockerInstalled(): Boolean;
begin
  Result := FileExists(ExpandConstant('{commonpf64}\Docker\Docker\resources\bin\docker.exe'))
    or RegKeyExists(HKLM, 'SOFTWARE\Docker Inc.\Docker Desktop');
end;

function InstallDocker(): Boolean;
var
  Installer: String;
  Code: Integer;
begin
  Result := False;
  Installer := ExpandConstant('{tmp}\DockerDesktopInstaller.exe');
  try
    DownloadTemporaryFile(DockerUrl, 'DockerDesktopInstaller.exe', '', nil);
  except
    Exit;
  end;
  WizardForm.StatusLabel.Caption := CustomMessage('InstallingDocker');
  // Docker's documented unattended install.
  if Exec(Installer, 'install --quiet --accept-license', '', SW_SHOW, ewWaitUntilTerminated, Code) then
    Result := (Code = 0) or (Code = 3010);  // 3010: done, restart required
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Preset: String;
begin
  if CurStep = ssInstall then
  begin
    if not DockerInstalled() then
    begin
      MsgBox(CustomMessage('DockerMissing'), mbInformation, MB_OK);
      if not InstallDocker() then
        MsgBox(CustomMessage('DockerFailed'), mbError, MB_OK);
    end;
  end;
  if CurStep = ssPostInstall then
  begin
    if WizardSetupType(False) = 'recommended' then Preset := 'recommended'
    else if WizardSetupType(False) = 'light' then Preset := 'light'
    else Preset := '';
    SaveStringToFile(ExpandConstant('{app}\preset.txt'), Preset, False);
    if not FileExists(ExpandConstant('{app}\.env')) then
      SaveStringToFile(ExpandConstant('{app}\.env'), 'GLOSA_PORT=7878' + #13#10, False);
  end;
end;

function InitializeUninstall(): Boolean;
begin
  RemoveData := MsgBox(CustomMessage('RemoveData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
  Result := True;
end;

function RemoveDataFlag(Param: String): String;
begin
  if RemoveData then Result := '-RemoveData' else Result := '';
end;
