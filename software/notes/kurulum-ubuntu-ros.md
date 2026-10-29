# Kurulum: Ubuntu 24.04 + ROS 2 Jazzy (Raspberry Pi 5)

Her komutu sırayla, hata çıkarsa **durup** hata satırını kaydet. İnternet bağlantısı gerekir.

## 1) İşletim sistemi
Raspberry Pi Imager → "Other general-purpose OS → Ubuntu → Ubuntu Server 24.04 LTS (64-bit)".
Imager ayarlarından kullanıcı adı, parola, Wi-Fi ve **SSH'ı** etkinleştir. İlk açılışta birkaç dakika bekle.
```bash
ssh <kullanici>@<pi-adresi>
sudo apt update && sudo apt -y upgrade
sudo reboot
```

## 2) Temel paketler
```bash
sudo apt install -y git python3-pip python3-yaml python3-serial python3-numpy python3-matplotlib \
    python3-lgpio gpiod libraspberrypi-bin
sudo usermod -aG dialout,gpio $USER      # çıkış yapıp tekrar gir
```
Kontrol: `gpiodetect` çıktısında `pinctrl-rp1` olmalı. (`RPi.GPIO` Pi 5'te ÇALIŞMAZ; kod `lgpio` kullanır.)

## 3) ROS 2 Jazzy
```bash
sudo apt install -y software-properties-common curl
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list
sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-dev-tools \
    ros-jazzy-slam-toolbox ros-jazzy-nav2-map-server ros-jazzy-tf2-ros \
    ros-jazzy-teleop-twist-keyboard
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
ros2 --help        # çalışıyorsa tamam
```
(Bu adımlar ROS'un resmi Jazzy kurulum belgesine dayanır; adres değişmişse `docs.ros.org` → Jazzy → Installation.)

## 4) LiDAR sürücüsü (sllidar_ros2)
```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/Slamtec/sllidar_ros2.git
cd ~/ros2_ws
rosdep init 2>/dev/null; rosdep update
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
ls $(ros2 pkg prefix sllidar_ros2)/share/sllidar_ros2/launch
```
Son komut S3 için bir launch dosyası göstermeli (beklenen: `sllidar_s3_launch.py`). **Adı farklıysa**
`ros/launch/bringup.launch.py` içindeki `sllidar_s3_launch.py` yazısını o dosya adıyla değiştir.

## 5) Yazılım
```bash
cd ~ && git clone <repo-adresi>
cd autonomous-car/software
python3 -m unittest discover -s tests       # OK
```
Ardından `stages/01-...`'den başla.

## Önerilen: sürekli bağlantı için
- `~/.bashrc` içine `export ROS_DOMAIN_ID=7` ekle (aynı ağda başka robot varsa karışmasın).
- Tüm komutları `tmux` içinde çalıştır (SSH kopsa da süreç yaşar): `sudo apt install tmux`.
  **Uyarı:** robot sürerken SSH kopmasına karşı hız komutları 0,5 sn içinde kesilince araç durur; yine de araç başında kal.
