# photon_parser
npm i
# Download Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt update
# Install utilits
sudo apt install ./google-chrome-stable_current_amd64.deb xvfb fluxbox x11vnc novnc xdotool -y
# Download Phantom Wallet extension to crx format
# Unzip extension to the extensions folder
unzip phantom.crx -d ./extensions/phantom
# Start novnc script
sh start_novnc.sh
# Setting up your google account and auth of phantom wallet

