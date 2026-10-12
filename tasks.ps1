# Команды для Windows PowerShell:  .\tasks.ps1 <команда>
param([Parameter(Position = 0)][string]$Task = "help")
$py = ".\.venv\Scripts\python.exe"
switch ($Task) {
  "venv"     { py -3.12 -m venv .venv; & $py -m pip install -U pip; & $py -m pip install -r requirements\dev.txt }
  "models"   { & $py scripts\download_models.py }
  "predict"  { & $py scripts\predict.py --manifest data\documents.json --questions data\questions.json --base data --input image --out results.json --reference data\reference_results.json }
  "eval"     { & $py data\evaluate.py --reference data\reference_results.json --predictions results.json }
  "build-frontend" { Push-Location frontend; npm install; npm run build; Pop-Location }
  "backend"  { Push-Location backend; & "..\.venv\Scripts\python.exe" manage.py migrate; & "..\.venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000; Pop-Location }
  "serve"    { Push-Location backend; & "..\.venv\Scripts\python.exe" manage.py migrate; & "..\.venv\Scripts\python.exe" -m waitress --listen=0.0.0.0:8000 --threads=4 dekanat.wsgi:application; Pop-Location }
  "frontend" { Push-Location frontend; npm run dev; Pop-Location }
  "bot"      { & $py -m bot }
  "tunnel"   { & $py scripts\tunnel_keeper.py }
  default    { Write-Host "Команды: venv, models, predict, eval, build-frontend, backend, serve, frontend, bot, tunnel" }
}
