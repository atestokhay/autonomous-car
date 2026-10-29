# Wiring — Kablolama ve Pin Eşleşmeleri

Bu klasör, otonom aracın güç ve sinyal bağlantıları için referanstır.

## 1. Donanım

- Raspberry Pi 5
- 2 × JSumo 12V 430RPM enkoderli DC motor
- 2 × L298N motor sürücü modülü
- RPLIDAR S3 ve USB adaptörü
- 4S LiPo batarya (14,8 V nominal, 16,8 V tam dolu)
- Raspberry Pi için 5 V USB-C DC-DC dönüştürücü
- LiDAR için MP1584EN buck converter
- Motor beslemesi için uygun gerilim sınırlama/dönüştürme düzeni
- Ana şalter, sigorta ve güç dağıtım bağlantıları

## 2. Güç bağlantıları

### Ana güç dağıtımı

Batarya pozitif hattı:

`4S LiPo (+) → Ana şalter → Ana sigorta → Güç dağıtım (+)`

Batarya negatif hattı:

`4S LiPo (-) → Güç dağıtım GND`

Güç dağıtımından üç ayrı besleme kolu oluşturulur.

### A. Motor beslemesi

`Güç dağıtım (+) → Motor beslemesi için uygun dönüştürücü → 12 V motor besleme hattı`

12 V motor besleme hattı:

- Sol L298N motor besleme girişine
- Sağ L298N motor besleme girişine

bağlanır.

Her iki L298N'in GND bağlantısı ortak toprak dağıtımına döner.

**4S LiPo batarya motorlara veya L298N motor besleme girişlerine
doğrudan bağlanmamalıdır.** Batarya tam doluyken 16,8 V'a ulaşır;
motorların nominal gerilimi 12 V'tur. PWM kullanımı tek başına
batarya geriliminin motorlara uygulanmasını güvenli hâle getirmez.

Motor beslemesi dönüştürücüsünün kapasitesi iki motorun çalışma ve
başlangıç/durma akımlarını karşılamalıdır.

### B. Raspberry Pi 5 beslemesi

`Güç dağıtım (+) → Pi DC-DC giriş (+)`

`Güç dağıtım GND → Pi DC-DC giriş (-)`

Dönüştürücünün regüle edilmiş çıkışı:

- `5 V → Raspberry Pi 5 USB-C güç girişi`
- `GND → Ortak toprak`

Raspberry Pi için 5 V / 5 A sağlayabilen uygun bir besleme hedeflenir.
Dönüştürücü ve USB-C bağlantısının bu çıkışı gerçekten sağlayabildiği
varsayılmamalı; modül özellikleri dikkate alınmalıdır.

### C. RPLIDAR S3 beslemesi

LiDAR, Raspberry Pi'nin 5 V hattından beslenmez.

`Güç dağıtım (+) → MP1584EN IN+`

`Güç dağıtım GND → MP1584EN IN-`

MP1584EN çıkışı:

- `OUT+ (5 V) → LiDAR USB adaptörünün harici güç girişindeki +5 V`
- `OUT- → LiDAR güç girişinin GND ucu`

LiDAR beslemesi 4,9–5,2 V aralığında tutulmalıdır. Hedef çıkış
yaklaşık 5,00 V'tur. Dönüştürücünün LiDAR'ın açılış akımını
karşılaması gerekir.

**USB bağlantısı veri içindir:** LiDAR USB adaptörü Raspberry Pi'ye
USB üzerinden bağlanır; LiDAR'ın çalışma gücü MP1584EN hattından
sağlanır. Adaptörün USB 5 V hattıyla harici 5 V beslemenin paralel
olmasına veya birbirini geri beslemesine izin verilmemelidir.

## 3. Ortak toprak (GND)

Aşağıdaki devrelerin referans toprakları ortak bir dağıtım noktasında
birleştirilir:

- Raspberry Pi DC-DC çıkış GND'si
- Motor besleme dönüştürücüsü GND'si
- Sol L298N GND'si
- Sağ L298N GND'si
- MP1584EN çıkış GND'si
- Sol ve sağ enkoder GND'si
- LiDAR harici besleme GND'ssi

Motor akımlarının Raspberry Pi'nin ince GND kablolarından geçmesine
izin verilmemelidir. Yüksek akımlı motor dönüş yolları uygun kesitli
kablolarla güç dağıtımına dönmelidir.

## 4. Raspberry Pi GPIO eşleşmeleri

Pin numaraları BCM GPIO numarası ve fiziksel pin numarası olarak
ayrı ayrı verilmiştir.

### Sol L298N

| İşlev | BCM GPIO | Fiziksel pin |
|---|---:|---:|
| ENA / PWM | GPIO12 | 32 |
| IN1 | GPIO5 | 29 |
| IN2 | GPIO6 | 31 |
| GND | GND | Örn. 6 |

Sol motorun iki güç kablosu sol L298N'in `OUT1` ve `OUT2`
terminallerine bağlanır.

### Sağ L298N

| İşlev | BCM GPIO | Fiziksel pin |
|---|---:|---:|
| ENA / PWM | GPIO13 | 33 |
| IN1 | GPIO16 | 36 |
| IN2 | GPIO20 | 38 |
| GND | GND | Örn. 9 |

Sağ motorun iki güç kablosu sağ L298N'in `OUT1` ve `OUT2`
terminallerine bağlanır.

### Sol motor enkoderi

| Sinyal | BCM GPIO | Fiziksel pin |
|---|---:|---:|
| A | GPIO17 | 11 |
| B | GPIO27 | 13 |
| VCC | Doğrulanmış besleme | Uygun 3,3 V kaynağı, yalnızca enkoder destekliyorsa |
| GND | GND | Ortak toprak |

### Sağ motor enkoderi

| Sinyal | BCM GPIO | Fiziksel pin |
|---|---:|---:|
| A | GPIO22 | 15 |
| B | GPIO23 | 16 |
| VCC | Doğrulanmış besleme | Uygun 3,3 V kaynağı, yalnızca enkoder destekliyorsa |
| GND | GND | Ortak toprak |

**GPIO güvenliği:** Raspberry Pi GPIO girişleri 5 V toleranslı değildir.
Enkoder çıkışları Pi GPIO pinlerine ulaşmadan önce 3,3 V sınırına
uygun olmalıdır. Gerekirse uygun seviye dönüştürücü kullanılmalıdır.

## 5. L298N jumper notları

- `ENA` jumperi, ENA pininden PWM kontrolü kullanılacaksa çıkarılır.
- `5V-EN` farklı bir işlev görür; ENA jumperiyle karıştırılmamalıdır.
- Lojik besleme ve `5V-EN` düzeni kullanılan kartın bağlantı
  şemasına uygun olmalıdır.
- Kartın 5 V terminaline doğrulanmamış bir harici besleme bağlanmamalıdır.

## 6. İlk enerji verme sırası

1. Batarya kapalıyken polariteyi ve bağlantıları kontrol et.
2. Kısa devre kontrolünü yap.
3. Motor besleme dönüştürücüsünün çıkış gerilimini ölç.
4. Pi dönüştürücüsünün 5 V çıkışını ölç.
5. MP1584EN çıkışını yükten önce yaklaşık 5,00 V'a ayarla.
6. LiDAR besleme hattının akım kapasitesini ve USB veri bağlantısını
   ayrı ayrı kontrol et.
7. Pi, sensörler ve motorları aşamalı olarak test et.
8. Motor testlerinde tekerlekleri yerden kes ve aracı sabitle.

## İlgili dosyalar

- `netlist.txt` — bağlantıların metinsel listesi
- `schematic.fzz` — düzenlenebilir bağlantı şeması
- `schematic.png` — şemanın dışa aktarılmış görüntüsü
