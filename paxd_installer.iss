[Setup]
AppName=PaxD
AppVersion=1.0
AppPublisher=mralfiem591
AppPublisherURL=https://mralfiem591.github.io/paxd/
AppSupportURL=https://github.com/mralfiem591/paxd/issues
AppUpdatesURL=https://github.com/mralfiem591/paxd/releases
DefaultDirName={localappdata}\PaxD
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=.\Output
OutputBaseFilename=PaxD_Installer
Compression=lzma
SolidCompression=yes
Uninstallable=no
WizardStyle=modern

[Files]
Source: "paxd-installer.py"; DestDir: "{tmp}"; Flags: dontcopy

[Run]
Filename: "python.exe"; Parameters: """{tmp}\paxd-installer.py"" --quiet --no-cleanup --repo ""{code:GetRepoUrl}"""; WorkingDir: "{tmp}"; StatusMsg: "Installing PaxD... (this may take a moment)"

[Code]
var
  RepoPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  RepoPage := CreateInputQueryPage(wpWelcome,
    'Repository Configuration', 'Where should PaxD be installed from?',
    'Please specify the PaxD-ready repository URL to install from. (Leave default for official)');
  RepoPage.Add('Repository URL:', False);
  RepoPage.Values[0] := 'https://raw.githubusercontent.com/mralfiem591/paxd/refs/heads/main';
end;

function GetRepoUrl(Param: String): String;
begin
  Result := RepoPage.Values[0];
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    ExtractTemporaryFile('paxd-installer.py');
  end;
end;
