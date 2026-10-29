# Aşama 4 — Hız PID (otomatik ayar)

**Tekerlekler havada, araç sabit, acil güç kesme hazır.** Önce aşama 2 ve 3 bitmiş olmalı
(yönler doğru, enkoder sayıyor). Ölçüm gönderip bekleme yok: kod kendini ayarlar.

## 1) Otomatik ayar (tek komut)
```bash
python stages/04-pid/autotune.py            # iki tekerlek, sırayla
python stages/04-pid/autotune.py --mock     # donanımsız deneme (dosya yazmaz)
```
Her tekerlek için sırayla:
1. **Süpürme:** duty basamaklarında hızı ölçer → `kff` (hız/duty eğimi) ve `deadband` (ölü bölge).
2. **Basamak cevabı:** 0.6 duty'de %63'e çıkış süresi → motor zaman sabiti `tau`.
3. **PI hesabı:** `kp`, `ki` modelden hesaplanır (kapalı çevrim yumuşak seçilir).
4. **Doğrulama:** hesaplanan ayarla 15 rad/s'lik hedefi kapalı çevrimde dener.
   Aşım ≤ %8, kalıcı hata ≤ %3, oturma ≤ 1,5 sn değilse ayarı yumuşatıp 3 kereye kadar tekrar dener.

Sonuç `config/tuned.yaml`'a yazılır ve `pid.yaml`'ın üstüne biner. Doğrulama geçmezse
**hiçbir şey yazılmaz**, mevcut değerler korunur. `tuned.yaml`'ı silmek varsayılana döndürür.

Hata/uyarı mesajları ne yapılacağını söyler (ör. "hız NEGATİF → enkoder invert'ünü çevir",
"duty 0.85'te beklenmedik RPM → ticks_per_rev yanlış olabilir").

## 2) Adım testi ve log
```bash
python stages/04-pid/run.py --side both --targets 0,10,20,10,0
python tools/plot_log.py logs/pid_....csv
```
`sudo` ile çalıştırırsan gerçek zamanlı öncelik açılır. Çıktıdaki `dt_max_ms` ve `overruns` döngü düzgünlüğünü gösterir.

## 3) Yerde yeniden ayar
Havada ayarlanan değerler boşta motora göredir. Araç zemine konunca yük (ağırlık, sürtünme) değişir;
etrafında boş yer varken `autotune.py`'yi bir kez de yerde çalıştırmak daha doğru sonuç verir
(15 rad/s'de araç hızı = 15 × tekerlek yarıçapı; yarıçap ~3-4 cm ise ~0,5 m/s. Etrafında en az 3 m boş yer olsun).

## Güvenlik
- Hedef `max_speed_rad_s` (pid.yaml) üstüne çıkamaz.
- Tam gaz verip hız alınamazsa (enkoder ters / tekerlek sıkışık) kod 0,5 sn içinde motoru durdurur.
- Ctrl+C her zaman motorları durdurur.

## Bitti sayılır (iki tekerlek ayrı ayrı)
- `autotune.py` iki tekerlekte de "GEÇTİ" ile biter, `tuned.yaml` oluşur.
- `run.py` adım testinde iki tekerlek aynı hedefte aynı hıza ±%3 içinde ulaşıyor.
- `overruns` ihmal edilebilir seviyede, `dt_max_ms` < 20.

## İleri (manuel) araçlar
`identify.py` sadece süpürmeyi yapıp `kff`/`deadband` önerir (teşhis için). `kd` varsayılan 0 kalır
(enkoder ölçümü gürültülü).

## Olası sorunlar
→ `notes/sorun-giderme.md` ("Aşama 4" bölümü)
