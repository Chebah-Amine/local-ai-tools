# Installe Text Polish en arrière-plan : lancé automatiquement à l'ouverture de session,
# et démarré tout de suite. Rien à lancer ni à quitter ensuite : Ctrl+Alt+P fonctionne partout.
# Un raccourci « Text Polish » est aussi ajouté au menu Démarrer (pour relancer après un arrêt).
#   .\install_shortcuts.ps1 -KeyFile C:\chemin\mistral-api-key.txt
#   .\install_shortcuts.ps1 -KeyFile ... -Desktop   -> + raccourci Bureau (relancer après un « Quitter »)
#   .\install_shortcuts.ps1 -Remove                 -> arrête l'appli et supprime les raccourcis
param([string]$KeyFile, [switch]$Desktop, [switch]$Remove)

$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$script  = Join-Path $here "text_polish.py"
$ico     = Join-Path $here "text_polish.ico"
$startup = Join-Path ([Environment]::GetFolderPath('Startup')) "Text Polish.lnk"
$desk    = Join-Path ([Environment]::GetFolderPath('Desktop')) "Text Polish.lnk"
$menu    = Join-Path ([Environment]::GetFolderPath('Programs')) "Text Polish.lnk"

# Arrête une instance déjà lancée (pour la relancer avec la nouvelle configuration).
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -like "*text_polish.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force; "Instance arrêtée (PID $($_.ProcessId))" }

if ($Remove) {
    $startup, $desk, $menu | Where-Object { Test-Path $_ } | ForEach-Object { Remove-Item $_; "Supprimé : $_" }
    return
}

$arguments = "`"$script`""
if ($KeyFile) {
    $KeyFile = (Resolve-Path $KeyFile -ErrorAction Stop).Path
    $arguments += " --key-file `"$KeyFile`""
} elseif (-not $env:MISTRAL_API_KEY) {
    throw "Indiquer la clé API Mistral : -KeyFile C:\chemin\vers\cle.txt (ou variable MISTRAL_API_KEY)."
}

$pythonw = (Get-Command pythonw.exe -ErrorAction Stop).Source

# Icône générée à partir du même dessin que l'icône de la zone de notification.
python -c "import sys; sys.path.insert(0, r'$here'); from text_polish import make_icon; make_icon('#6b7280').save(r'$ico', sizes=[(16,16),(32,32),(48,48),(64,64)])"

$targets = @($startup, $menu)
if ($Desktop) { $targets += $desk } elseif (Test-Path $desk) { Remove-Item $desk; "Supprimé : $desk" }

$shell = New-Object -ComObject WScript.Shell
foreach ($lnk in $targets) {
    $s = $shell.CreateShortcut($lnk)
    $s.TargetPath       = $pythonw
    $s.Arguments        = $arguments
    $s.WorkingDirectory = $here
    $s.IconLocation     = $ico
    $s.Description      = "Nettoyage de texte dicté (Mistral)"
    $s.Save()
    "Créé : $lnk"
}

Start-Process $startup
"Text Polish est lancé (icône près de l'horloge) et démarrera avec Windows."
