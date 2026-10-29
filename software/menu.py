#!/usr/bin/env python3
"""Öğrenci menüsü: uzun komutları ezberlemeden aşamaları sayı seçerek çalıştırır.
Başlatmak için:   python3 menu.py
Her adımdan önce güvenlik sorusu sorar; hiçbir şeyi sormadan hareket ettirmez."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

# (başlık, güvenlik uyarısı veya None, [komut, ...], ne olacağını anlatan kısa not)
ITEMS = [
    ("1  Bilgisayar ve yazılım testi (motor HAREKET ETMEZ)", None,
     [[PY, "-m", "unittest", "discover", "-s", "tests"]],
     "Sonunda 'OK' yazmalı. 'FAILED' yazarsa dur ve çıktıyı öğretmene gönder."),
    ("2  Motor testi: SOL tekerlek", "TEKERLEKLER YERDEN KESİLMİŞ mi ve elin güç şalterinde mi?",
     [[PY, "stages/02-motor/run.py", "--side", "left", "--duty", "0.3"]],
     "Ekrandaki yönergeleri izle: tekerlek İLERİ yönde dönmeli."),
    ("3  Motor testi: SAĞ tekerlek", "TEKERLEKLER YERDEN KESİLMİŞ mi ve elin güç şalterinde mi?",
     [[PY, "stages/02-motor/run.py", "--side", "right", "--duty", "0.3"]],
     "Ekrandaki yönergeleri izle: tekerlek İLERİ yönde dönmeli."),
    ("4  Enkoder izleme (tekerleği ELLE çevir)", None,
     [[PY, "stages/03-enkoder/run.py", "watch"]],
     "Tekerleği ileri çevirince sayı ARTMALI. Durdurmak için Ctrl+C."),
    ("5  Enkoder tur ölçümü: SOL (10 tur elle çevireceksin)", None,
     [[PY, "stages/03-enkoder/run.py", "calibrate", "--side", "left", "--turns", "10"]],
     "Ekrandaki talimatı izle."),
    ("6  Enkoder tur ölçümü: SAĞ (10 tur elle çevireceksin)", None,
     [[PY, "stages/03-enkoder/run.py", "calibrate", "--side", "right", "--turns", "10"]],
     "Ekrandaki talimatı izle."),
    ("7  PID OTOMATİK AYAR (iki tekerlek)", "TEKERLEKLER YERDEN KESİLMİŞ mi (havada) ve elin güç şalterinde mi?",
     [[PY, "stages/04-pid/autotune.py"]],
     "Tekerlekler kendi kendine dönecek. Sonunda her tekerlek için 'GEÇTİ' görmelisin."),
    ("8  LiDAR bağlantı kontrolü", None,
     [[PY, "stages/05-lidar/check_lidar.py"]],
     "'Sağlık: İYİ' görmelisin."),
    ("9  Yarıçap kalibrasyonu (aracı ELLE 1 m düz it)", "Motorlar çalışmaz; aracı elinle iteceksin. Hazır mısın?",
     [[PY, "stages/06-odometri/calibrate.py", "radius", "--distance", "1.0"]],
     "Aracı ölçtüğün 1 metrelik çizgide düz it."),
    ("10 Tekerlek arası mesafe kalibrasyonu (aracı ELLE 3 tur çevir)", "Motorlar çalışmaz; aracı elinle çevireceksin. Hazır mısın?",
     [[PY, "stages/06-odometri/calibrate.py", "base", "--turns", "3"]],
     "Aracı yerinde 3 tam tur çevir."),
    ("11 Duvar takibi SİMÜLASYON (robot gerekmez)", None,
     [[PY, "stages/07-duvar-takibi/sim_demo.py", "--world", "oda", "--side", "right"]],
     "Sonunda 'ÇARPMA YOK' görmelisin. Grafik wall_follow_sim.png olarak kaydedilir."),
    ("12 Teşhis raporu (motor HAREKET ETMEZ)", None,
     [[PY, "tools/diag.py"]],
     "Sorun olduğunda çalıştır; diag_rapor.txt dosyasını öğretmene gönder."),
]

ROS_NOTE = ("ROS gerektiren adımlar (LiDAR sürüş, duvar takibi, SLAM) için menüde komut yok: "
            "stages/05..08 klasörlerindeki README'yi izle.")


def main():
    while True:
        print("\n" + "=" * 62)
        print(" OTONOM ARAÇ - ÖĞRENCİ MENÜSÜ  (çıkmak için q)")
        print("=" * 62)
        for t, *_ in ITEMS:
            print("  " + t)
        print("\n" + ROS_NOTE)
        c = input("\nNumara seç: ").strip().lower()
        if c in ("q", "quit", "çıkış", "cikis"):
            return
        sel = [it for it in ITEMS if it[0].split()[0] == c]
        if not sel:
            print("Geçersiz seçim. Listedeki bir numara yaz.")
            continue
        title, warn, cmds, note = sel[0]
        print(f"\n>>> {title}\nNe olacak: {note}")
        if warn:
            if input(f"\nGÜVENLİK: {warn} (e/h): ").strip().lower() not in ("e", "evet"):
                print("Hazır değilsen BAŞLAMA. Menüye dönülüyor.")
                continue
        for cmd in cmds:
            print("\nÇalışıyor:", " ".join(Path(x).name if x.startswith("/") else x for x in cmd))
            try:
                subprocess.run(cmd, cwd=ROOT)
            except KeyboardInterrupt:
                print("\nDurduruldu (Ctrl+C).")
        input("\nBittiğinde Enter'a bas, menüye dönelim...")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nÇıkıldı.")
