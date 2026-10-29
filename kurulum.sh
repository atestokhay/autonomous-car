#!/usr/bin/env bash
# Otonom araç: tek komutla kurulum (Raspberry Pi 5, Ubuntu 24.04).
#   bash kurulum.sh            -> kurulumu yapar (yaklaşık 20-40 dk, internet gerekir)
#   bash kurulum.sh --deneme   -> hiçbir şey kurmadan sadece ne yapacağını yazar
# Güvenle tekrar çalıştırılabilir: yarım kalırsa aynı komutu yine çalıştır, kaldığı yerden devam eder.
# Kayıt dosyası: ~/kurulum_log.txt  (hata olursa bunu öğretmene gönder)

DENEME=0; [ "${1:-}" = "--deneme" ] && DENEME=1
LOG="$HOME/kurulum_log.txt"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOFT="$REPO_DIR/software"
WS="$HOME/ros2_ws"


renk() { printf '\n\033[1;%sm%s\033[0m\n' "$1" "$2"; }
adim() { renk 36 "[$1] $2"; echo "[$1] $2" >> "$LOG"; }
tamam() { renk 32 "   ✓ $1"; }
uyari() { renk 33 "   ! $1"; echo "UYARI: $1" >> "$LOG"; }
dur()  { renk 31 "   ✗ HATA: $1"; echo "HATA: $1" >> "$LOG"
         echo "   Kayıt dosyası: $LOG  (öğretmene gönder). Düzeltince 'bash kurulum.sh' ile tekrar çalıştır."; exit 1; }

calistir() {   # calistir "açıklama" komut...
  local aciklama="$1"; shift
  echo "   → $aciklama"
  echo "\$ $*" >> "$LOG"
  if [ "$DENEME" = 1 ]; then echo "     (deneme) $*"; return 0; fi
  "$@" >> "$LOG" 2>&1 || return 1
}

echo "Kurulum başladı $(date)" >> "$LOG"
renk 35 "OTONOM ARAÇ KURULUMU — bu pencereyi kapatma, internet bağlantısı kesilmesin."
[ "$DENEME" = 1 ] && renk 33 "DENEME MODU: hiçbir şey kurulmayacak."

# ---------- 1. Ön kontroller ----------
adim 1/8 "Bilgisayar kontrol ediliyor"
. /etc/os-release 2>/dev/null
[ "${VERSION_ID:-}" = "24.04" ] || dur "Ubuntu 24.04 gerekli (bulunan: ${PRETTY_NAME:-bilinmiyor}). SD karta Ubuntu Server 24.04 LTS 64-bit yaz."
[ "$(uname -m)" = "aarch64" ] || uyari "İşlemci aarch64 değil ($(uname -m)); bu betik Raspberry Pi 5 için hazırlandı."
[ "$DENEME" = 1 ] || [ "$(id -u)" -ne 0 ] || dur "Betiği root olarak çalıştırma. Normal kullanıcıyla: bash kurulum.sh"
[ -d "$SOFT" ] || dur "software klasörü bulunamadı ($SOFT). Betiği repo içinden çalıştır."
if [ "$DENEME" != 1 ]; then
  sudo -v || dur "sudo parolası gerekli."
  ping -c1 -W3 8.8.8.8 >/dev/null 2>&1 || dur "İnternet yok. Wi-Fi/Ethernet bağlantısını kontrol et."
fi
tamam "Ubuntu 24.04, internet var"

# ---------- 2. Sistem güncelleme ----------
adim 2/8 "Sistem paketleri güncelleniyor (uzun sürebilir)"
calistir "paket listesi" sudo apt-get update || dur "apt update başarısız (internet/saat ayarı?)"
calistir "güncelleme" sudo DEBIAN_FRONTEND=noninteractive apt-get -y upgrade || uyari "Güncelleme tam bitmedi, devam ediliyor"
tamam "Sistem güncel"

# ---------- 3. Temel paketler ----------
adim 3/8 "Temel paketler kuruluyor"
calistir "python/gpio/seri paketleri" sudo DEBIAN_FRONTEND=noninteractive apt-get -y install \
  git curl tmux software-properties-common python3-pip python3-yaml python3-serial python3-numpy \
  python3-matplotlib python3-lgpio gpiod || dur "Temel paketler kurulamadı"
calistir "vcgencmd (isteğe bağlı)" sudo DEBIAN_FRONTEND=noninteractive apt-get -y install libraspberrypi-bin \
  || uyari "vcgencmd kurulamadı (güç kontrolü komutu çalışmayabilir, kurulum devam ediyor)"
tamam "Temel paketler tamam"

# ---------- 4. GPIO ve seri port izinleri ----------
adim 4/8 "GPIO ve LiDAR portu izinleri ayarlanıyor"
calistir "gpio grubu" sudo groupadd -f gpio || dur "Grup oluşturulamadı"
calistir "kullanıcıyı gruplara ekle" sudo usermod -aG dialout,gpio "$USER" || dur "Kullanıcı gruba eklenemedi"
if [ "$DENEME" != 1 ]; then
  echo 'SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"' | sudo tee /etc/udev/rules.d/99-gpio.rules >/dev/null
  sudo udevadm control --reload-rules >> "$LOG" 2>&1; sudo udevadm trigger >> "$LOG" 2>&1
fi
tamam "İzinler ayarlandı (etkili olması için kurulum sonunda yeniden başlatılacak)"

# ---------- 5. ROS 2 Jazzy ----------
adim 5/8 "ROS 2 Jazzy kuruluyor (en uzun adım)"
if [ -f /opt/ros/jazzy/setup.bash ] && dpkg -s ros-jazzy-slam-toolbox >/dev/null 2>&1; then
  tamam "ROS 2 zaten kurulu, atlanıyor"
else
  calistir "universe deposu" sudo add-apt-repository -y universe || dur "universe deposu eklenemedi"
  calistir "ROS anahtarı" sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg || dur "ROS anahtarı indirilemedi (internet?)"
  if [ "$DENEME" != 1 ]; then
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu ${UBUNTU_CODENAME} main" \
      | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
  fi
  calistir "paket listesi" sudo apt-get update || dur "ROS deposu okunamadı"
  calistir "ROS paketleri" sudo DEBIAN_FRONTEND=noninteractive apt-get -y install \
    ros-jazzy-ros-base ros-dev-tools ros-jazzy-slam-toolbox ros-jazzy-nav2-map-server \
    ros-jazzy-tf2-ros ros-jazzy-teleop-twist-keyboard || dur "ROS paketleri kurulamadı"
  tamam "ROS 2 kuruldu"
fi

# ---------- 6. LiDAR sürücüsü ----------
adim 6/8 "LiDAR sürücüsü (sllidar_ros2) derleniyor"
if [ "$DENEME" != 1 ]; then
  . /opt/ros/jazzy/setup.bash
fi
if [ -f "$WS/install/setup.bash" ] && [ -d "$WS/install/sllidar_ros2" ]; then
  tamam "sllidar_ros2 zaten derlenmiş, atlanıyor"
else
  calistir "çalışma alanı" mkdir -p "$WS/src" || dur "Klasör oluşturulamadı"
  [ -d "$WS/src/sllidar_ros2" ] || calistir "sürücü indiriliyor" git clone https://github.com/Slamtec/sllidar_ros2.git "$WS/src/sllidar_ros2" \
    || dur "sllidar_ros2 indirilemedi (internet/GitHub?)"
  if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    calistir "rosdep başlat" sudo rosdep init || uyari "rosdep init atlandı"
  fi
  calistir "rosdep güncelle" rosdep update || uyari "rosdep update başarısız"
  calistir "bağımlılıklar" bash -c "cd '$WS' && rosdep install --from-paths src --ignore-src -y" || uyari "rosdep install uyarı verdi"
  calistir "derleme (5-15 dk)" bash -c "cd '$WS' && source /opt/ros/jazzy/setup.bash && colcon build --symlink-install" \
    || dur "sllidar_ros2 derlenemedi. kurulum_log.txt'nin son satırlarına bak."
  tamam "LiDAR sürücüsü derlendi"
fi

# ---------- 7. Ortam ayarları ----------
adim 7/8 "Terminal ayarları (.bashrc) yapılıyor"
ekle() { grep -qxF "$1" "$HOME/.bashrc" 2>/dev/null || { [ "$DENEME" = 1 ] || echo "$1" >> "$HOME/.bashrc"; }; }
ekle "source /opt/ros/jazzy/setup.bash"
ekle "source $WS/install/setup.bash"
ekle "export ROS_DOMAIN_ID=7"
tamam ".bashrc güncellendi"

# ---------- 8. Test ----------
adim 8/8 "Yazılım testi çalıştırılıyor (motor HAREKET ETMEZ)"
if [ "$DENEME" != 1 ]; then
  if (cd "$SOFT" && python3 -m unittest discover -s tests >> "$LOG" 2>&1); then
    tamam "Yazılım testleri geçti"
  else
    dur "Yazılım testleri başarısız. kurulum_log.txt'nin son satırlarına bak."
  fi
fi

renk 32 "KURULUM TAMAMLANDI ✓"
cat <<'MSG'

Sıradaki adımlar:
  1) Pi'yi yeniden başlat (izinlerin etkili olması için ŞART):   sudo reboot
  2) Yeniden bağlanınca:  cd ~/autonomous-car/software && python3 menu.py
  3) Rehber:              software/OGRENCI-REHBERI.md  (ADIM 2'den devam et)
MSG
echo "Kurulum bitti $(date)" >> "$LOG"
