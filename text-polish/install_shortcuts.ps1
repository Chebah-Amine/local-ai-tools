# Crée un raccourci « Text Polish » sur le Bureau (sans console).
#   .\install_shortcuts.ps1            -> raccourci Bureau
#   .\install_shortcuts.ps1 -Startup   -> + lancement automatique à l'ouverture de session
#   .\install_shortcuts.ps1 -Remove    -> supprime les raccourcis
param([switch]$Startup, [switch]$Remove)

$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$script  = Join-Path $here "text_polish.py"
$ico     = Join-Path $here "text_polish.ico"
$targets = @(Join-Path ([Environment]::GetFolderPath('Desktop')) "Text Polish.lnk")
if ($Startup) { $targets += Join-Path ([Environment]::GetFolderPath('Startup')) "Text Polish.lnk" }

if ($Remove) {
    $targets + (Join-Path ([Environment]::GetFolderPath('Startup')) "Text Polish.lnk") |
        Where-Object { Test-Path $_ } | ForEach-Object { Remove-Item $_; "Supprimé : $_" }
    return
}

$pythonw = (Get-Command pythonw.exe -ErrorAction Stop).Source

# Icône générée à partir du même dessin que l'icône de la zone de notification.
python -c "import sys; sys.path.insert(0, r'$here'); from text_polish import make_icon; make_icon('#6b7280').save(r'$ico', sizes=[(16,16),(32,32),(48,48),(64,64)])"

$shell = New-Object -ComObject WScript.Shell
foreach ($lnk in $targets) {
    $s = $shell.CreateShortcut($lnk)
    $s.TargetPath       = $pythonw
    $s.Arguments        = "`"$script`""
    $s.WorkingDirectory = $here
    $s.IconLocation     = $ico
    $s.Description      = "Nettoyage de texte dicté avec un modèle local"
    $s.Save()
    "Créé : $lnk"
}
