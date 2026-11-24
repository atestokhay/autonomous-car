#!/usr/bin/env bash
# Başlat butonunu Pi açılınca otomatik çalıştırır (systemd servisi: arac-buton).
#   bash tools/buton_servis_kur.sh          -> kur ve başlat
#   bash tools/buton_servis_kur.sh kaldir   -> durdur ve kaldır
# Kayıtları izlemek için:  journalctl -u arac-buton -f
# Not: servis açıkken buton her zaman dinlenir. Aşama 1-6 ayarlarını yaparken servisi durdur:
#   sudo systemctl stop arac-buton
set -euo pipefail

SERVIS=arac-buton
DOSYA=/etc/systemd/system/$SERVIS.service
KLASOR="$(cd "$(dirname "$0")/.." && pwd)"
KULLANICI="${SUDO_USER:-$USER}"

if [ "${1:-}" = "kaldir" ]; then
    sudo systemctl disable --now "$SERVIS" 2>/dev/null || true
    sudo rm -f "$DOSYA"
    sudo systemctl daemon-reload
    echo "Kaldırıldı: $SERVIS"
    exit 0
fi

if ! id -nG "$KULLANICI" | grep -qw gpio; then
    echo "UYARI: $KULLANICI 'gpio' grubunda değil (notes/kurulum-ubuntu-ros.md, adım 1). Servis GPIO'yu açamayabilir."
fi

sudo tee "$DOSYA" >/dev/null <<EOF
[Unit]
Description=Otonom arac - baslat butonu (GPIO16, pin 36)
After=multi-user.target

[Service]
Type=simple
User=$KULLANICI
WorkingDirectory=$KLASOR
ExecStart=/usr/bin/python3 -u $KLASOR/tools/baslat_butonu.py
Restart=on-failure
RestartSec=3
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVIS"
echo "Kuruldu: $SERVIS (Pi her açıldığında butonu bekler)."
echo "Durum:   systemctl status $SERVIS      Kayıtlar: journalctl -u $SERVIS -f"
