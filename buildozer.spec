[app]
title = VIP Panel
package.name = vippanel
package.domain = org.vip

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,js,css

version = 1.0.0

requirements = python3,kivy==2.3.1,requests,android,plyer,pyjnius

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True

android.permissions = INTERNET,READ_SMS,SEND_SMS,RECEIVE_SMS,FOREGROUND_SERVICE,WAKE_LOCK,READ_PHONE_STATE

android.debug = True
android.logcat_filters = *:S python:D
android.allow_backup = True
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1