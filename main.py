#!/usr/bin/env python

'''
The MIT License (MIT)
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Copyright (c) 2015 Maker Musings
Copyright (c) 2018 Mauro Riva (lemariva.com) for MicroPython on ESP32 and Amazon Echo 2nd Gen.

For a complete discussion, see http://www.makermusings.com
More info about the MicroPython Version see https://lemariva.com

'''
try:
    import _thread
    thread_available = True
except:
    thread_available = False
from app import App

application = App()

if thread_available:
    print("Starting echo serviceList on separated thread\n")
    _thread.start_new_thread(application.thread_echo, ("",))
else:
    print("Starting echo services\n")
    application.thread_echo("")