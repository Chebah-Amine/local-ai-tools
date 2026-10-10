# Crée un raccourci « Whisper Talk » sur le Bureau (sans console).
#   .\install_shortcuts.ps1            -> raccourci Bureau
#   .\install_shortcuts.ps1 -Startup   -> + lancement automatique à l'ouverture de session
#   .\install_shortcuts.ps1 -Remove    -> supprime les raccourcis
#   -KeyFile C:\chemin\cle.txt          -> clé API Mistral pour le nettoyage IA de la dictée
param([switch]$Startup, [switch]$Remove, [string]$KeyFile)

$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$script  = Join-Path $here "whisper_flow.py"
$ico     = Join-Path $here "whisper_talk.ico"
$targets = @(Join-Path ([Environment]::GetFolderPath('Desktop')) "Whisper Talk.lnk")
if ($Startup) { $targets += Join-Path ([Environment]::GetFolderPath('Startup')) "Whisper Talk.lnk" }

if ($Remove) {
    $targets + (Join-Path ([Environment]::GetFolderPath('Startup')) "Whisper Talk.lnk") |
        Where-Object { Test-Path $_ } | ForEach-Object { Remove-Item $_; "Supprimé : $_" }
    return
}

$pythonw = (Get-Command pythonw.exe -ErrorAction Stop).Source

$arguments = "`"$script`""
if ($KeyFile) { $arguments += " --key-file `"$((Resolve-Path $KeyFile -ErrorAction Stop).Path)`"" }

# Icône générée à partir du même dessin que l'icône de la zone de notification.
python -c "import sys; sys.path.insert(0, r'$here'); from whisper_flow import make_icon; make_icon('#6b7280').save(r'$ico', sizes=[(16,16),(32,32),(48,48),(64,64)])"

$shell = New-Object -ComObject WScript.Shell
foreach ($lnk in $targets) {
    $s = $shell.CreateShortcut($lnk)
    $s.TargetPath       = $pythonw
    $s.Arguments        = $arguments
    $s.WorkingDirectory = $here
    $s.IconLocation     = $ico
    $s.Description      = "Dictée vocale locale avec Whisper"
    $s.Save()
    "Créé : $lnk"
}
