[app]

title = Agrio
package.name = agrio
package.domain = org.adriancorte

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,env

version = 1.0.0

requirements = python3,kivy==2.2.1,pyjnius,urllib3,idna,certifi,gtts

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,RECORD_AUDIO,WAKE_LOCK,ACCESS_NETWORK_STATE

android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
