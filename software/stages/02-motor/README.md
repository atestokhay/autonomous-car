# Aşama 2 — Motor

**Tekerlekler yerden kesilmiş, araç sabit, acil güç kesme hazır.**

```bash
python stages/02-motor/run.py --side left  --duty 0.3
python stages/02-motor/run.py --side right --duty 0.3
python stages/02-motor/run.py --side both  --duty 0.3
```
Her yön için Enter beklenir. Duty en fazla 0.6 kabul edilir.

## Yön kontrolü
"İLERİ" komutunda tekerlek aracın ileri yönünde dönmüyorsa `config/pins.yaml` içinde o motorun `invert` değerini çevir (kablo söküp takma). Sağ motor ayna montajlı olduğu için `invert: true` ile başlıyor.

## Bitti sayılır
- Sol ve sağ tekerlek ileri komutunda ileri, geri komutunda geri dönüyor.
- Düşük duty'de (0.2–0.3) hangisi hiç dönmüyor not et (aşama 4'te ölü bölge olarak ölçülecek).
- Motor durma komutunda duruyor, L298N ısınmıyor.

## Olası sorunlar
→ `notes/sorun-giderme.md` ("Aşama 2" bölümü)
