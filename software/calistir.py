#!/usr/bin/env python3
"""Rehberli çalıştırma: aşamaları SIRAYLA yapar, her adımı açıklar, güvenlik sorar, sonucu kontrol eder.
Kendi kaldığı yeri hatırlar. Başlatmak için:   arac
Deneme (donanımsız):  python3 calistir.py --mock"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import kablolama
from ortak import *  # noqa: F401,F403
from ortak import (MOCK, PY, ROOT, ROS_ENV, STATE, ask_yn, baslik, edit_yaml_invert, get_invert,  # noqa: F401
                   guvenlik, load_state, mock_arg, run, save_state, say, script, set_robot_yaw, sorun, tak)


# ---------- adımlar ----------
def a_yazilim_testi():
    baslik("ADIM 1 — Yazılım testi (motor HAREKET ETMEZ)")
    say("Yazılımın doğru kurulduğunu kontrol eder. 15 sn sürer. Sonunda 'OK' görmelisin.")
    return script("-m", "unittest", "discover", "-s", "tests") or sorun("Yazılım testi başarısız.")


def a_motor():
    baslik("ADIM 2 — Motorlar doğru yöne dönüyor mu?")
    say("Her tekerleğe kısa süre güç verilecek. Tekerleğin ARACIN İLERİ yönünde döndüğünü izle.\n"
        "(Araç ileri giderken tekerleğin üst kısmı öne doğru hareket eder.)")
    if not guvenlik("TEKERLEKLER YERDEN KESİLMİŞ mi (araç sehpada) ve ELİN GÜÇ ŞALTERİNDE mi?"):
        say("Önce aracı sehpaya al, sonra tekrar başlat.", "y")
        return False
    for side, ad in (("left", "SOL"), (("right"), "SAĞ")):
        for deneme in range(2):
            say(f"\n--- {ad} tekerlek ---", "b")
            say("Program Enter bekler: Enter'a bas, tekerleğe bak.")
            if not script("stages/02-motor/run.py", "--side", side, "--duty", "0.3", *mock_arg()):
                return sorun(f"{ad} motor testi hata verdi (motor hiç dönmüyorsa kabloları kontrol et).")
            if ask_yn(f"{ad} tekerlek İLERİ komutunda aracın İLERİ yönünde mi döndü?"):
                tak(True)
                break
            if deneme == 0:
                say("Yönü yazılımda çeviriyorum (kablo sökmene gerek yok) ve tekrar deniyoruz.", "y")
                edit_yaml_invert("motors", side, not get_invert("motors", side))
            else:
                return sorun(f"{ad} motor yönü iki denemede de düzelmedi (motor hiç dönmüyor olabilir).")
    return True


def a_enkoder():
    baslik("ADIM 3 — Enkoder doğru sayıyor mu?")
    say("Enkoder, tekerleğin kaç adım döndüğünü sayar. Şimdi tekerlekleri ELLE ileri çevireceksin.\n"
        "Ekranda sayılar akacak. Bitirince Ctrl+C'ye bas.\n"
        "⚠️  Enkoder güç kablosu Pi'nin 3,3 V pinine bağlı olmalı (5 V DEĞİL).")
    if not ask_yn("Enkoder gücü 3,3 V pinine (pin 1 ve 17) bağlı mı?"):
        say("Önce kabloyu düzelt (arac kablo). 5 V Pi'nin pinini yakar!", "r")
        return False
    for side, ad in (("left", "SOL"), ("right", "SAĞ")):
        for deneme in range(2):
            say(f"\n--- {ad} tekerleği ELLE İLERİ çevir, sayının nasıl değiştiğine bak; sonra Ctrl+C ---", "b")
            if MOCK:
                say("(deneme modu: izleme atlandı)", "y")
            else:
                script("stages/03-enkoder/run.py", "watch")
            if ask_yn(f"{ad} tekerlek İLERİ çevrilirken sayı ARTTI mı?"):
                tak(True)
                break
            if ask_yn("Sayı hiç değişmedi mi?", "h"):
                return sorun(f"{ad} enkoder sayı üretmiyor: VCC/GND/A/B kablolarını kontrol et (arac kablo).")
            if deneme == 0:
                say("Yönü yazılımda çeviriyorum, tekrar deniyoruz.", "y")
                edit_yaml_invert("encoders", side, not get_invert("encoders", side))
            else:
                return sorun(f"{ad} enkoder yönü düzelmedi.")
    say("\nŞimdi motor çalışırken enkoder doğru sayıyor mu bakacağız (5 sn).")
    if not guvenlik("TEKERLEKLER HÂLÂ HAVADA mı ve ELİN ŞALTERDE mi?"):
        return False
    if not script("stages/03-enkoder/run.py", "drive", "--duty", "0.5", "--seconds", "5", *mock_arg()):
        return sorun("Enkoderli motor testi hata verdi.")
    say("Her iki tekerlek yaklaşık AYNI hızda dönmeli (RPM değerleri birbirine yakın), 'eksik' hep 0 olmalı.")
    if not ask_yn("'eksik' sayacı 0 kaldı ve iki tekerleğin RPM değeri birbirine yakın mı?", "e"):
        say("Bir tekerleği 10 tur elle çevirip tur başına sayıyı ölçelim.", "y")
        for side in ("left", "right"):
            script("stages/03-enkoder/run.py", "calibrate", "--side", side, "--turns", "10", *mock_arg())
        say("Çıkan sayı 392'den çok farklıysa config/robot.yaml → ticks_per_rev satırına yaz, sonra tekrar çalıştır.", "y")
    return True


def a_pid():
    baslik("ADIM 4 — Hız ayarı (PID otomatik ayar)")
    say("Yazılım motoru farklı güçlerde döndürüp kendi ayarlarını bulur. Tekerlekler kendiliğinden ve hızlı dönecek.\n"
        "Birkaç dakika sürer. Sonunda iki tekerlek için 'GEÇTİ' görmelisin.")
    if not guvenlik("TEKERLEKLER HAVADA mı, parmak/kablo tekerleklerden uzak mı, ELİN ŞALTERDE mi?"):
        return False
    return script("stages/04-pid/autotune.py", *mock_arg()) or sorun(
        "Otomatik ayar geçmedi. En sık neden: batarya düşük (14,0 V altı) ya da gevşek kablo. Şarj et, tekrar dene.")


def a_lidar_seri():
    baslik("ADIM 5 — LiDAR bağlantısı")
    say("LiDAR'a doğrudan 'sağlığın nasıl?' diye sorulur. 'Sağlık: İYİ' görmelisin.\n"
        "Önce multimetreyle MP1584EN çıkışının 4,9–5,2 V olduğunu doğrula.")
    if MOCK:
        say("(deneme modu: atlandı)", "y")
        return True
    if not ask_yn("MP1584EN çıkışı 4,9–5,2 V ve LiDAR USB kablosu Pi'ye takılı mı?"):
        return False
    return script("stages/05-lidar/check_lidar.py") or sorun("LiDAR cevap vermedi (güç, USB veri kablosu, port).")


def a_odometri():
    baslik("ADIM 6 — Aracın gittiği yolu ölçme (odometri)")
    say("Bu adımda motorlar ÇALIŞMAZ. Aracı ELLE iteceksin.\n"
        "Gerekenler: yerde düz bir çizgi ve 1 metrelik şerit metre/cetvel.")
    if not ask_yn("Aracı yere koyup elinle itmeye hazır mısın?"):
        return False
    say("\n--- 1) Aracı çizgi boyunca TAM 1 metre DÜZ it ---", "b")
    if not script("stages/06-odometri/calibrate.py", "radius", "--distance", "1.0", *mock_arg()):
        return sorun("Yarıçap ölçümü başarısız (araç düz gitmedi ya da enkoder yönü yanlış).")
    say("\n--- 2) Aracı yerinde TAM 3 tur çevir (başlangıç işaretine geri dönerek) ---", "b")
    if not script("stages/06-odometri/calibrate.py", "base", "--turns", "3", *mock_arg()):
        return sorun("Tekerlek arası mesafe ölçümü başarısız.")
    say("\nÖnemli: iki soruda da 'robot_cal.yaml'a yazılsın mı?' sorusuna 'e' demiş olmalısın.", "y")
    return True


def ros_baslat(ek=""):
    return subprocess.Popen(["bash", "-c", ROS_ENV + "exec ros2 launch ros/launch/bringup.launch.py" + (" mock:=true" if MOCK else "") + ek],
                            cwd=ROOT, preexec_fn=os.setsid)


def ros_durdur(p):
    if p and p.poll() is None:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGINT)
            p.wait(timeout=8)
        except Exception:  # noqa: BLE001
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except Exception:  # noqa: BLE001
                pass


def a_lidar_yon():
    baslik("ADIM 7 — LiDAR 'ön' yönü doğru mu?")
    say("LiDAR, kabloya göre farklı yönde takılı olabilir. Yazılım 'ön'ü doğru bilmeli.\n"
        "Bir KUTU/KİTAP hazırla: aracın TAM ÖNÜNDE yaklaşık 30 cm uzağa koyacaksın.")
    if MOCK or not shutil.which("ros2"):
        say("(ROS yok ya da deneme modu: atlandı)", "y")
        return True
    for yaw in (0, 90, 180, -90):
        set_robot_yaw(yaw)
        say(f"\nDeneme: LiDAR yönü ayarı = {yaw}°. Kutuyu aracın önüne koy.", "b")
        if input("Hazır olunca Enter'a bas...") is None:
            return False
        p = ros_baslat()
        time.sleep(6)
        run(ROS_ENV + "python3 ros/scan_check.py", shell=True)
        ros_durdur(p)
        if ask_yn("'ön' mesafesi kutuya yakın (≈ 0,3 m) mı çıktı?"):
            if ask_yn("Kutuyu aracın SAĞINA koyunca 'sağ' mesafesi küçüldü mü? (denemek için kutuyu taşı, sonra cevapla)"):
                tak(True)
                return True
            say("Sağ-sol ters: robot.yaml'da lidar_inverted: true yapman gerekiyor (config/robot.yaml).", "y")
            return sorun("LiDAR sağ-sol aynalı görünüyor.")
    return sorun("Hiçbir yönde 'ön' doğru çıkmadı: LiDAR çalışıyor mu, kutu menzilde mi kontrol et.")


def a_sim():
    baslik("ADIM 8 — Duvar takibi SİMÜLASYONU (robot gerekmez)")
    say("Bilgisayar sanal bir odada sanal araçla duvar takibini dener. Sonunda 'ÇARPMA YOK' görmelisin.")
    return script("stages/07-duvar-takibi/sim_demo.py", "--world", "oda", "--side", "right") or sorun("Simülasyon başarısız.")


def duvar_takibi(v_scale, yer):
    if MOCK or not shutil.which("ros2"):
        say("(ROS yok ya da deneme modu: robotlu duvar takibi çalıştırılamaz)", "y")
        return True
    p = ros_baslat()
    time.sleep(6)
    say(f"\nDuvar takibi başlıyor (hız ölçeği {v_scale}). DURDURMAK İÇİN: Ctrl+C ya da ŞALTER.", "y")
    try:
        run(ROS_ENV + f"python3 ros/wall_follow_node.py --side right --v-scale {v_scale} --countdown 5", shell=True)
    finally:
        ros_durdur(p)
    return ask_yn(f"{yer}: araç duvara paralel, çarpmadan ve salınmadan gitti mi?")


def a_duvar_hava():
    baslik("ADIM 9 — Duvar takibi: TEKERLEKLER HAVADA")
    say("Araç havada, düşük hızda. Elini aracın SAĞ yanına, LiDAR yüksekliğinde bir yüzey gibi tut.\n"
        "Elin yakınsa tekerlekler elden uzaklaşacak şekilde, uzaksa yaklaşacak şekilde dönmeli.")
    if not guvenlik("TEKERLEKLER HAVADA ve ELİN ŞALTERDE mi?"):
        return False
    return duvar_takibi(0.3, "Havada")


def a_duvar_yer():
    baslik("ADIM 10 — Duvar takibi: YERDE")
    say("Açık bir zemine, en az 2 metrelik düz bir DUVAR kur (koli/karton/paravan), aracı duvarın SAĞINA ~40 cm koy.\n"
        "Etrafında en az 3 metre boş yer olsun.")
    if not guvenlik("Duvar hazır, etrafı boş mu ve BİR ARKADAŞIN şalterin başında mı (araç yerde gidecek)?"):
        return False
    return duvar_takibi(0.5, "Yerde")


PI_KAPATILDI = Path.home() / ".arac_pi_kapatildi"

STEPS = [
    ("kablo_robot", kablolama.a_kablo_robot), ("kablo_pi", kablolama.a_kablo_pi), ("guc", kablolama.a_guc_dogrula),
    ("yazilim", a_yazilim_testi), ("motor", a_motor), ("enkoder", a_enkoder), ("pid", a_pid),
    ("lidar", a_lidar_seri), ("odometri", a_odometri), ("yon", a_lidar_yon),
    ("sim", a_sim), ("hava", a_duvar_hava), ("yer", a_duvar_yer),
]


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "kablo":
        kablolama.tablo_goster()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "acil":
        f = ROOT / "docs" / "acil-durum.md"
        subprocess.run(["less", "-R", str(f)]) if shutil.which("less") else print(f.read_text(encoding="utf-8"))
        return
    say("\n  OTONOM ARAÇ — REHBERLİ ÇALIŞTIRMA", "c")
    say("  Her adımı sırayla yapacağız. Ctrl+C = o anki işi durdurur. Şalter = her zaman en güvenlisi.\n")
    st = load_state()
    done = set(st["done"])
    if PI_KAPATILDI.exists():
        PI_KAPATILDI.unlink()
        done.add("kablo_pi")
        say("Pi kablolaması tamamlandı sayıldı (Pi'yi kapatıp yeniden açtın).", "g")
    if done and len(done) < len(STEPS):
        say(f"Kaldığın yer hatırlandı: {len(done)}/{len(STEPS)} adım tamam.")
        if not ask_yn("Kaldığın adımdan devam edelim mi? ('h' = baştan)", "e"):
            done = set()
    elif len(done) == len(STEPS):
        say("Tüm adımlar daha önce tamamlanmış. 🎉")
        say("  1) Robotu duvar takibine çıkar (yerde)\n  2) Her şeyi baştan yap")
        c = input("Seçim [1/2]: ").strip()
        if c != "2":
            guvenlik("Duvar hazır, etrafı boş ve elin şalterde mi?") and duvar_takibi(0.5, "Yerde")
            return
        done = set()
    for key, fn in STEPS:
        if key in done:
            continue
        try:
            ok = fn()
        except KeyboardInterrupt:
            say("\nDurduruldu.", "y")
            ok = False
        if not ok:
            say("\nBu adım tamamlanmadı. Düzelttikten sonra:  arac", "y")
            st["done"] = sorted(done)
            save_state(st)
            sys.exit(1)
        done.add(key)
        st["done"] = sorted(done)
        save_state(st)
    baslik("TEBRİKLER — tüm adımlar tamam 🎉")
    say("Robotu tekrar duvar takibine çıkarmak için:  arac  → 1")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nÇıkıldı.")
