# Aşama 1 — Pi kurulumu ve güç doğrulaması

Bağlantı ve ölçümler: `hardware/` (önce oradaki enerji verme öncesi kontrol listesi). Burada yazılım tarafı.

## Adımlar
1. Raspberry Pi Imager ile microSD'ye **Ubuntu 24.04 LTS (64-bit)** yaz (ROS 2 Jazzy bu sürüm içindir; sonradan değiştirme).
2. Kurulum, paketler ve ROS 2 → **`notes/kurulum-ubuntu-ros.md`** (adım adım).
3. Yazılımı indir: `git clone <repo-adresi> && cd autonomous-car/software`
4. Testleri çalıştır: `python3 -m unittest discover -s tests` → `OK`
5. GPIO çipi: `pins.yaml` içinde `gpiochip: auto` (kendisi bulur). Kontrol: `gpiodetect` çıktısında `pinctrl-rp1` görünmeli.

## Güç kontrolü
```bash
vcgencmd get_throttled              # throttled=0x0 olmalı
dmesg | grep -i -E "under-?volt"    # çıktı olmamalı
```
`vcgencmd` yoksa: `sudo apt install libraspberrypi-bin`.

3 A'lik Pi modülü kullanılıyorsa USB aygıtlara akım sınırlama uyarısı görülebilir. LiDAR ayrı hattan beslendiği için
genelde sorun olmaz; sürerse `notes/sorun-giderme.md` → "Pi'de düşük voltaj uyarısı".

## Bitti sayılır
- [ ] Pi 10 dk bataryadan açık kaldı, kendiliğinden reset olmadı.
- [ ] `vcgencmd get_throttled` = `0x0` (çıktıyı `hardware` test sayfasına kaydet).
- [ ] `python3 -m unittest discover -s tests` → `OK`.
- [ ] `gpiodetect` içinde `pinctrl-rp1` var.

## Olası sorunlar
→ `notes/sorun-giderme.md` ("Aşama 1" bölümü)
