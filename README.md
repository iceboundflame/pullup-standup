# Pullup Standup

## Architecture

[Crossbar](http://crossbar.io) (configured in `.crossbar/config.json`)
- Runs a Web server on port 8080:
  - WebSocket connection allows access to a real-time message bus,
    events are published from Python backend and the JS UI can make RPC calls to the backend.
  - Also serves UI, static files in `web/build/`.

Python Twisted server (`main.py`)
- handles talking with proximity sensor (ADC), GPIO for RFID module.
- maintains state of the service
- maintains user and pullup record database
- provides a series of RPC functions exposed via Crossbar. These RPC methods are called from the UI.
  - get_state
  - enroll
  - end_set
  - signout
  - set_threshold
- publishes messages:
  - state updates

UI (React single-page webapp)
- web/src/App.js
  - rendering is driven by backend state


## Development workflow


Initial setup on dev host (laptop)

    # Set up "pullup" in .ssh/config with proper tunneling.
    <omitted>

    # Install npm packages for dev environment.
    (cd web && npm install)

    # Continually rsync into ~/sw
    watchman -- trigger ~/Dropbox/codex/pullup pullup -- bash -c "rsync -av --delete ~/Dropbox/codex/pullup/ pullup:sw/ --exclude pigpio --exclude users.json --exclude .*.swp"


Development environment:

    # FIRST, Make sure localhost:8080 proxies to rpi's 8080 (via ssh tunnel)
    #   .ssh/config:        LocalForward 8080 localhost:8080
    #   or command line:    -L8080:localhost:8080
    # because package.json "proxy" proxies /ws to localhost:8080

    # Start a dev server. Viewable on localhost:3000
    (cd web && npm start)


Deploy to device:

    # Build a prod build, will be rsynced by watchman
    (cd web && npm run build)


On-device setup:

    ssh pullup

    # Build & install pigpiod, then
    sudo systemctl enable pigpiod

    # crossbar is config'd by ~/sw/.crossbar/config.json
    # crossbar serves static files from ~/sw/web/dist
    # "pullup" : Python Twisted server - connects to crossbar.
    sudo cp /home/pi/sw/systemd/* /lib/systemd/system/

    sudo systemctl enable crossbar pullup pigpiod
    sudo systemctl start pullup

    # or run manually:
    sudo systemctl stop pullup
    python main.py

    vi .config/lxsession/LXDE-pi/autostart
    # add:
    @/home/pi/sw/start-kiosk



## BOM

- Raspberry Pi 3 + power adapter $50
- TFT touch screen (SPI) 4" 320x480 WaveShare SpotPear - $26 (ebay)
- Xceed ID XF1050-G Mini Mullion 125 kHz Wiegand Proximity HID® Card Reader - $17 (ebay)
- ADS1115 ADC 4 Channel 16Bit I2C PGA Low Power Arduino Raspberry Pi 2 - $5
- GP2Y0A21YK0F Sharp IR Analog Distance Sensor Distance 10-80CM Cable For Arduino - $5
- Prototyping board and headers - $11
- GoPro gooseneck mount
- GoPro mount adapter for IR sensor - 3D printed
- RPi enclosure - 3d printed
- section of CAT6 cable used for sensor
- Hose clamps to attach enclosure to pullup bar


## Initial bringup

Install OSXFUSE and fuse-ext2:

    https://github.com/gpz500/fuse-ext2/releases
    sudo sed -e 's/OPTIONS="local"/OPTIONS="local,rw+"/g' -i.orig /Library/Filesystems/fuse-ext2.fs/fuse-ext2.util

Used w.sh to set up Wi Fi: https://github.com/shamiao/raspi-wifi-blindscript

Setup timezone, locale (en-us.UTF8)
http://rohankapoor.com/2012/04/americanizing-the-raspberry-pi/


### OzzMaker PiScreen setup

Generally, follow http://ozzmaker.com/piscreenfaq/ EXCEPT:

    # /boot/config.txt:
    dtoverlay=piscreen,speed=32000000,rotate=180

    # .config/lxsession/LXDE-pi/autostart
    @lxpanel --profile LXDE-pi
    @pcmanfm --desktop --profile LXDE-pi
    @xscreensaver -no-splash
    @sudo /bin/sh /etc/X11/Xsession.d/xinput_calibrator_pointercal.sh
    # Really not sure why it's necessary. Xsession.d is not running automatically??
    @point-rpi
    @/home/pi/sw/start-kiosk

    # To recalibrate (crazy workaround):
    sudo rm /etc/pointercal.xinput
    sudo killall Xorg; sleep 2; sudo killall Xorg; sleep 2
    export XAUTHORITY=~/.Xauthority; export DISPLAY=:0
    xinput --set-prop 'ADS7846 Touchscreen' 'Evdev Axes Swap' 1
    sudo /etc/X11/Xsession.d/xinput_calibrator_pointercal.sh

    /etc/X11/Xsession.d/disableblank.sh


RFID Notes

    http://www.pagemac.com/projects/rfid/avrfid
    http://www.pagemac.com/projects/rfid/hid_data_formats


### WiFi dongle for 5GHz

4/11/2018
bought DWA-171 WiFi module w/5GHz support, since Pinterest Guest is no longer on 2.4GHz
Installer script: http://downloads.fars-robotics.net/wifi-drivers/install-wifi

It failed. Brings down the whole USB bus. Possible overcurrent?
