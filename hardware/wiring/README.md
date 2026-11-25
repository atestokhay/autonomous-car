# Wiring — Kablolama ve Pin Eşleşmeleri

Bu klasör, otonom aracın güç ve sinyal bağlantıları için referanstır.
Görsel şema: [`schematic.png`](schematic.png). Metin listesi: [`netlist.txt`](netlist.txt).
Pin numaralarının tek kaynağı `software/config/pins.yaml` dosyasıdır; bu belge onunla aynı tutulur.

## 1. Donanım

- Raspberry Pi 5
- 2 × JGA12-N20B 6 V 300 RPM enkoderli DC motor (manyetik enkoder, motor milinde)
- 1 × TB6612FNG çift kanallı motor sürücü (A kanalı = sol, B kanalı = sağ)
- RPLIDAR S3 ve USB adaptörü
- BNO055 9 eksen IMU (I2C, adres 0x28)
- 3S LiPo batarya (11,1 V nominal, 12,6 V tam dolu)
- Motorlar için XL4015 5 A buck regülatör (6,0 V'a ayarlı). Ayarlanmamış XL4015'in çıkışı girişe eşit olabilir;
  ters kutup koruması yoktur.
- Raspberry Pi için 5 V / 5 A USB-C DC-DC dönüştürücü
- LiDAR için MP1584EN buck regülatör (5,0 V)
- 10 A sigorta, ana şalter, güç dağıtım baraları (+11,1 V ve GND)

## 2. Güç bağlantıları

### Ana güç dağıtımı

`3S LiPo (+) → 10 A sigorta → Ana şalter → +11,1 V bara`

`3S LiPo (−) → GND bara`

Sigorta bataryaya en yakın elemandır; böylece şalter ve kablosu da korunur.
Baradan üç ayrı besleme kolu çıkar.

### A. Motor beslemesi (6 V)

`+11,1 V bara → Buck IN+`   `GND bara → Buck IN−`

`Buck OUT+ (6,0 V) → TB6612 VM`   `Buck OUT− → TB6612 VM tarafındaki GND`

Buck çıkışı yük bağlanmadan önce 5,8–6,2 V aralığına (hedef 6,0 V) ayarlanır.
**3S LiPo motorlara veya TB6612 VM girişine doğrudan bağlanmaz.** Batarya tam doluyken
12,6 V'tur; N20 motorlar 6 V'luktur. PWM kullanımı tek başına bu gerilimi güvenli hâle getirmez.

TB6612FNG kanal başına yaklaşık 1,2 A sürekli, 3,2 A tepe akım verir. Seçilen N20 modelinin
kilitlenme (stall) akımı bu sınırın altında kalmalıdır.

### B. Raspberry Pi 5 beslemesi

`+11,1 V bara → USB-C DC-DC IN+`   `GND bara → USB-C DC-DC IN−`

`DC-DC USB-C çıkışı → Raspberry Pi 5 USB-C güç girişi`

Pi aynı anda iki ayrı güç kaynağına (ör. duvar adaptörü + DC-DC) bağlanmaz.

### C. RPLIDAR S3 beslemesi

LiDAR, Raspberry Pi'nin USB 5 V hattından beslenmez.

`+11,1 V bara → MP1584EN IN+`   `GND bara → MP1584EN IN−`

`MP1584EN OUT+ (5,0 V) → LiDAR 5V`   `MP1584EN OUT− → LiDAR GND`

LiDAR beslemesi 4,9–5,2 V aralığında tutulur (hedef 5,00 V); çıkış LiDAR bağlanmadan önce ayarlanır.
LiDAR'ın veri hattı USB adaptörüne, adaptör de USB kablosuyla Pi'nin USB-A portuna gider.

**Geri besleme uyarısı:** Adaptör kendi USB 5 V'unu da LiDAR'a veriyorsa, MP1584EN ile paralel
iki kaynak oluşur. Adaptörün harici güç seçeneği (jumper/giriş) kullanılarak USB 5 V'un LiDAR'a
gitmediği multimetreyle doğrulanmalıdır.

## 3. Toprak (GND) düzeni

İki GND hattı vardır:

- **GND bara (güç):** batarya (−), üç regülatörün IN− uçları, motor buck OUT− ve TB6612 VM GND'si.
- **GND lojik hattı:** Pi pin 14, iki enkoder GND, BNO055 GND. TB6612 lojik GND'si Pi pin 6'ya bağlıdır.

TB6612 kartında VM GND ve lojik GND içeriden ortaktır. Bu yüzden:

- Motor buck OUT− ile GND bara arasında **kısa ve kalın** bir kablo bulunmalıdır. Motor dönüş akımı
  bu yoldan dönmelidir, Pi'nin ince GND kablolarından veya USB-C kablosundan değil.
- Pi GND'si (ör. pin 39) ile GND bara arasında da tek bir referans bağlantısı yapılması önerilir
  (yıldız nokta). İlk enerjilendirmede Pi GND ↔ GND bara arasında süreklilik ölçülmelidir.

## 4. Raspberry Pi GPIO eşleşmeleri

Pin numaraları BCM GPIO numarası ve fiziksel pin numarası olarak ayrı ayrı verilmiştir.

### TB6612FNG

| TB6612 pini | İşlev | BCM GPIO | Fiziksel pin |
|---|---|---:|---:|
| PWMA | Sol motor hız (PWM) | GPIO12 | 32 |
| AIN1 | Sol motor yön 1 | GPIO5 | 29 |
| AIN2 | Sol motor yön 2 | GPIO6 | 31 |
| PWMB | Sağ motor hız (PWM) | GPIO13 | 33 |
| BIN1 | Sağ motor yön 1 | GPIO20 | 38 |
| BIN2 | Sağ motor yön 2 | GPIO21 | 40 |
| STBY | Sürücü etkin (HIGH) | GPIO26 | 37 |
| VCC | Lojik besleme | 3V3 | 1 |
| GND | Lojik toprak | GND | 6 |

`STBY` LOW iken iki kanal da kapalıdır. Yazılım açılışta yön/PWM pinlerini 0'a çeker, sonra STBY'yi
HIGH yapar; kapanışta yeniden LOW yapar.

Sol motor M+ / M− → `AO1` / `AO2`. Sağ motor M+ / M− → `BO1` / `BO2`.
Motor yönü ters çıkarsa kablo değiştirilmez; `pins.yaml` içindeki `invert` çevrilir.

### Sol motor enkoderi

| Sinyal | BCM GPIO | Fiziksel pin |
|---|---:|---:|
| ENC A | GPIO17 | 11 |
| ENC B | GPIO27 | 13 |
| VCC | 3,3 V lojik hattı | 17 |
| GND | GND lojik hattı | 14 |

### Sağ motor enkoderi

| Sinyal | BCM GPIO | Fiziksel pin |
|---|---:|---:|
| ENC A | GPIO23 | 16 |
| ENC B | GPIO24 | 18 |
| VCC | 3,3 V lojik hattı | 17 |
| GND | GND lojik hattı | 14 |

### BNO055 IMU

| Sinyal | BCM GPIO | Fiziksel pin |
|---|---:|---:|
| SDA | GPIO2 (I2C1 SDA) | 3 |
| SCL | GPIO3 (I2C1 SCL) | 5 |
| VIN | 3,3 V lojik hattı | 17 |
| GND | GND lojik hattı | 14 |

IMU şu an yazılımda kullanılmıyor; I2C'nin açık olması (`dtparam=i2c_arm=on`) ve `i2cdetect -y 1`
çıktısında `28` görünmesi yeterli doğrulamadır.

**GPIO güvenliği:** Raspberry Pi GPIO girişleri 5 V toleranslı değildir. Enkoderler ve BNO055
3,3 V'tan beslendiği için çıkışları da 3,3 V seviyesindedir; enkoder kartında 5 V'a çeken bir
pull-up direnci olmadığı doğrulanmalıdır.

**Enkoder hızı:** N20 enkoderi motor milindedir; tekerlek turu başına 28 × dişli oranı kadar kenar
üretir (bizim 300 RPM JGA12-N20B: genelde 1:50 → ~1400; 300 RPM'de tekerlek başına ~7000 kenar/sn). Yüksek devirde Python kenar sayımı kaçırabilir; aşama 3'teki `eksik`
sayacı 0'dan büyükse bildirin.

## 5. İlk enerji verme sırası

1. Batarya çıkarılmışken polariteyi ve bağlantıları kontrol et.
2. Kısa devre kontrolü: + bara ↔ GND bara, TB6612 VM ↔ GND (bip olmamalı).
3. Motor buck çıkışını yüksüz ölç ve 6,0 V'a ayarla.
4. Pi DC-DC'nin 5 V çıkışını ölç.
5. MP1584EN çıkışını yükten önce 5,00 V'a ayarla.
6. LiDAR USB adaptöründe geri besleme olmadığını doğrula.
7. Pi, sensörler ve motorları aşamalı olarak test et.
8. Motor testlerinde tekerlekleri yerden kes ve aracı sabitle.

## İlgili dosyalar

- `netlist.txt` — bağlantıların metinsel listesi
- `schematic.png` — öğrencilerin kurduğu kablolamanın şeması
- `schematic.fzz` — Fritzing proje dosyası (**eski L298N düzenini gösterir, güncellenmeli**)
