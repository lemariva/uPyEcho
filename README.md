# uPyEcho
Emulated Belkin WeMo device that works with Amazon Echo using a MicroPython 

About the repository
---------
This repository is based on [makermusings/fauxmo](https://github.com/makermusings/fauxmo) and it was ported to work on MicroPython.
This code emulates one or more Belkin WEMO type devices in software, and allows you to control them using an Amazon Echo. The code was tested on a ESP32 (WeMos board). You do not need to use AWS Lambda, or ngrok or open a port on your router. Amazon Echo searches for Belkin WEMO devices on the local network and using this code the WeMos board responds to the search request. For more information, please read [this article](https://goo.gl/ccpGhL).

Video
---------
[![PoC](https://img.youtube.com/vi/kkF3HfXV59I/0.jpg)](http://www.youtube.com/watch?v=kkF3HfXV59I)

Requirements
---------
* [WeMos (ESP32 - working on this board)](https://www.banggood.com/WeMos-WiFi-Bluetooth-Battery-ESP32-Development-Tool-p-1164436.html?p=QW0903761303201409LG)
* [NodeMcu Lua WIFI ESP8266 (next release -not tested yet)](https://www.banggood.com/D1-Mini-NodeMcu-Lua-WIFI-ESP8266-Development-Board-p-1044858.html?p=QW0903761303201409LG)
* [INR18650 3.7v Battery](https://www.banggood.com/4PCS-Samsung-INR18650-30Q-3000mAh-Unprotected-Button-Top-18650-Battery-p-1067185.html?p=QW0903761303201409LG)
* [WS2812B LED strip](https://www.banggood.com/5M-90W-300SMD-WS2812B-LED-RGB-Colorful-Strip-Light-Waterproof-IP65-WhiteBlack-PCB-DC5V-p-1035641.html?p=QW0903761303201409LG)
* [MicroPython for ESP32](http://micropython.org/download#esp32)

Instructions
---------
* Install MicroPython on the ESP32, you can use [this tutorial](https://lemariva.com/blog/2017/10/micropython-getting-started);
* Modify the following lines in the `boot.py`
  * ssid_ = `<your ssid>`
  * wp2_pass = `<your wpa2 password>` 
* Modify the `main.py` file if you want to:
  * The code line
  ```python
  ws2812_chain =  WS2812(ledNumber=ledNumber, brightness=100)
  ```
	defines the WS2812 LED strip. The argument `ledNumber` defines the size of the LED strip. In my case, I used 144 LEDs.
  * The code lines
  ```python
    devices = [
        {"description": "white led",
         "port": 12340,
         "handler": rest_api_handler((255,255,255), 50)}, 
         ... ]
    ```
	define the devices that are going to be found by Amazon Echo. Please read [this article](https://goo.gl/ccpGhL) for more information;
* Upload the code to the WeMos board;
* Connect the LED strip and restart the board;
* Start a device search from Amazon Echo. You can use the Alexa application, or just say, "echo/alexa, search for new devices" and wait;
* Say, "echo/alexa, turn on the <your device name>", it should work.

Changelog
---------
* Revision: 1.0

License
--------
* Check files

Credits
--------
* [makermusings/fauxmo](https://github.com/makermusings/fauxmo)

More Info:
---------
* [MicroPython for ESP32](http://micropython.org/download#esp32)
* [MicroPython Tutorial](https://lemariva.com/blog/2017/10/micropython-getting-started)
* [Universal Plug&Play](https://en.wikipedia.org/wiki/Universal_Plug_and_Play)
* [Node-red WEMO Emulator](http://flows.nodered.org/node/node-red-contrib-wemo-emulator)
* Chris(derossi) links:
  * [Amazon Echo & Home-Automation](http://www.makermusings.com/2015/07/13/amazon-echo-and-home-automation/)
  * [How to Make Amazon Echo Control Fake Wemo Devices](http://hackaday.com/2015/07/16/how-to-make-amazon-echo-control-fake-wemo-devices/)
  * [Virtual Wemo Code for Amazon Echo](http://www.makermusings.com/2015/07/18/virtual-wemo-code-for-amazon-echo)
  * [Home Automation with Amazon Echo Apps, Part 1](http://www.makermusings.com/2015/07/19/home-automation-with-amazon-echo-apps-part-1/)
* [Alexa Skills Kit](https://developer.amazon.com/appsandservices/solutions/alexa/alexa-skills-kit)
* [Flask-Ask: A New Python Framework for Rapid Alexa Alexa Skills Kit Development](https://developer.amazon.com/blogs/post/Tx14R0IYYGH3SKT/Flask-Ask-A-New-Python-Framework-for-Rapid-Alexa-Skills-Kit-Development)