[app]
title = Agrio
package.name = agrio
package.domain = org.adrian.agrio
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,wav,mp3,ogg
version = 0.1.0
requirements = python3,kivy==2.2.1,pyjnius,gtts
orientation = portrait
fullscreen = 0
android.presplash_color = #000000
android.permissions = INTERNET,RECORD_AUDIO,MODIFY_AUDIO_SETTINGS
android.api = 33
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
