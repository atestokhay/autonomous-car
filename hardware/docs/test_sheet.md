# Test Kayıt Sayfası

Her satıra **ölçtüğün değeri** ve sonucu yaz. "Geçti" yazmak yerine sayıyı yaz. Başarısız bir adımda dur:
`docs/emergency.md` → Bölüm B.

Tarih: ____  Kişi: ____  Batarya gerilimi (başlangıç): ____ V

## 0. Enerjisiz (batarya ÇIKARILMIŞ)
| Kontrol | Beklenen | Ölçülen | Geçti |
|---|---|---|---|
| Güç dağıtım (+) ↔ GND arası süreklilik | **Bip YOK** | | |
| Ortak GND: Pi GND ↔ sol L298N GND | Bip VAR | | |
| Ortak GND: Pi GND ↔ sağ L298N GND | Bip VAR | | |
| Ortak GND: Pi GND ↔ MP1584EN OUT− | Bip VAR | | |
| Ortak GND: Pi GND ↔ enkoder GND (her ikisi) | Bip VAR | | |
| Kablolar `netlist.txt` ile aynı (her biri etiketli) | Evet | | |
| Sigorta takılı, değeri | 7,5–10 A | | |
| ENA jumper'ları (2 L298N) | ÇIKARILMIŞ | | |

## 1. Güç (tekerlekler havada, yük bağlı değil)
| Ölçüm noktası | Beklenen | Ölçülen | Geçti |
|---|---|---|---|
| Batarya | 14,0–16,8 V | | |
| Motor regülatörü çıkışı | ≈ 12,0 V | | |
| Pi regülatörü çıkışı | 5,0–5,2 V | | |
| MP1584EN çıkışı (LiDAR bağlı DEĞİL) | 5,00 V (4,9–5,2) | | |
| MP1584EN çıkışı (LiDAR bağlı, dönerken) | 4,9–5,2 V | | |
| Pi `vcgencmd get_throttled` | 0x0 | | |

## 2. GPIO / enkoder seviyesi
| Kontrol | Beklenen | Ölçülen | Geçti |
|---|---|---|---|
| Enkoder VCC kaynağı | Pi **3,3 V** (pin 1 veya 17) | | |
| Tekerlek elle dönerken A pini gerilimi | 0 ↔ 3,3 V (**3,3 V'u geçmez**) | | |
| Tekerlek elle dönerken B pini gerilimi | 0 ↔ 3,3 V | | |

## 3. Yazılım aşamaları
| Aşama | Ölçüm | Değer | Geçti |
|---|---|---|---|
| 1 | `python3 -m unittest discover -s tests` | | |
| 2 | Sol ileri/geri doğru yön, sağ ileri/geri doğru yön | | |
| 3 | Tur başına tick (sol / sağ) | / | |
| 4 | Autotune sol/sağ sonucu | / | |
| 5 | LiDAR sağlık, `/scan` Hz | | |
| 6 | 1 m itme: ölçülen x / dönüş açısı | / | |
| 7 | Duvara oturma mesafesi (hedef 0,40 m) | | |

## 4. Entegre (tekerlekler havada → yerde)
| Kontrol | Beklenen | Gözlem | Geçti |
|---|---|---|---|
| 10 dk açık, motorlar çalışırken reset yok | Evet | | |
| Aşırı ısınma yok (L298N, regülatörler) | Elle 2 sn tutulabilir | | |
| Kablo hareket ederken kopma/temas sorunu | Yok | | |
