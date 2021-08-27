# Copyright [2017] [Mauro Riva <lemariva@mail.com> <lemariva.com>]

# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# boot.py -- run on boot-up

import json
credentials = json.loads('ap_credentials.json')
# wlan access
SSID = credentials.get('ssid')
WPA2_PASS = credentials.get('password')

ssid_ = SSID
wpa2_pass = WPA2_PASS


def do_connect():
    import network

    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(ssid_, wpa2_pass)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())


do_connect()

# ftp_server = ftpserver()
# ftp_server.start_thread()
