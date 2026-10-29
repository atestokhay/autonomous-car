# Aşama 3 — Enkoder

**Önce güvenlik:** Enkoder VCC'si Pi'nin **3,3 V** pinine (pin 1 / 17) bağlı olmalı, **5 V'a değil** (`~/autonomous-car.v2/hardware/README.md` → "Jumper ve enkoder").
Enerji verince tekerleği elle çevirirken A ve B pinlerinde multimetreyle ölç: 3,3 V'u geçiyorsa hemen sök.

```bash
python stages/03-enkoder/run.py watch                 # elle çevir, sayıyı izle
python stages/03-enkoder/run.py calibrate --side left --turns 10
python stages/03-enkoder/run.py drive --duty 0.5 --seconds 5
```

1. **watch:** Tekerleği ileri çevirince sayı ARTMALI. Azalıyorsa `pins.yaml` → `encoders.<taraf>.invert` çevir (sağ tarafta ters çıkması beklenir).
2. **calibrate:** `robot.yaml`'daki `ticks_per_rev: 392` Jsumo ürün sayfasından (98 CPR/kanal, x4) alındı. Tekerleği elle tam 10 tur çevirip doğrula; çıkan sayı 392'ye yakın değilse (örn. 196 veya 98) çıkan değeri `robot.yaml`'a yaz. Her iki tekerlek için yap, farklıysa sorun var. Hatalı bırakılırsa aşama 4 otomatik ayarı RPM uyarısı verir.
3. **drive:** Motor dönerken tick/s ve RPM gösterilir. `eksik` sayacı artmamalı.

## Python mu C++ mı?
`drive` ile duty 0.8'de `eksik` artıyorsa veya Pi CPU'su (`top`) yüksekse kenarlar kaçıyor demektir; o zaman enkoder okumasını C++'a taşırız. `eksik` 0 kalıyorsa Python yeterli.

## Bitti sayılır
- İleri yönde sayı artıyor (iki tekerlek için).
- `ticks_per_rev` her iki tekerlekte tutarlı ve `robot.yaml`'da.
- `drive` 0.8 duty'de `eksik = 0`, RPM boşta yaklaşık 300–400 aralığında (L298N kaybı ve batarya durumuna göre).

## Olası sorunlar
→ `notes/sorun-giderme.md` ("Aşama 3" bölümü)
