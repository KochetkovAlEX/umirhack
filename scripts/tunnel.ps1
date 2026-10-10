# Публичный HTTPS-туннель к локальному бэкенду для Telegram Mini App.
# Использование:  .\scripts\tunnel.ps1            (localhost.run через ssh, без регистрации)
#                 .\scripts\tunnel.ps1 -Cloudflare (cloudflared quick tunnel; не работает, если VPN блокирует DNS argotunnel.com)
# Полученный адрес запишите в .env: WEBAPP_URL=https://... и перезапустите бота (python -m bot).
param([switch]$Cloudflare, [int]$Port = 8000)
if ($Cloudflare) {
  & "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url "http://127.0.0.1:$Port" --no-autoupdate
} else {
  Write-Host "Адрес вида https://xxxx.lhr.life появится ниже; окно не закрывайте." -ForegroundColor Green
  ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R "80:127.0.0.1:$Port" nokey@localhost.run
}
