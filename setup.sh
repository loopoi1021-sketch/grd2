#!/bin/bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
git clone https://github.com/loopoi1021-sketch/grd2.git
cd grd2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium
