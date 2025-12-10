#!/bin/bash
git clone https://github.com/DMTF/Redfish-Tacklebox
cd Redfish-Tacklebox
git checkout 4faf7b377e38f370cee016d233915078c071924f
git apply rf_bios_settings.py.patch
sudo apt-get update
sudo apt-get install -y python3-venv
python3 -m venv .venv
nohup ssh 'sdp@sdp_10288' 'sleep 60' &
sleep 5
echo `pwd`
source .venv/bin/activate
pip install setuptools
sleep 5
rf_bios_settings.py -u sdp -p "\$harktank2Go" -r https://192.168.9.3 -l https://localhost:10443 --attribute OEMSSSTR00B OEMSSSTR00BEnabled
rf_bios_settings.py -u sdp -p "\$harktank2Go" -r https://192.168.9.3 -l https://localhost:10443 --attribute OEMSSSTR014 OEMSSSTR014Enabled
rf_bios_settings.py -u sdp -p "\$harktank2Go" -r https://192.168.9.3 -l https://localhost:10443 | grep "OEMSSSTR00B"
rf_bios_settings.py -u sdp -p "\$harktank2Go" -r https://192.168.9.3 -l https://localhost:10443 | grep "OEMSSSTR014"
sleep 30
nohup ssh 'sdp@sdp_10288' 'sudo shutdown -r -f now'
sleep 10
deactivate

