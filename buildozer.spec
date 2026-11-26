[app]

# (str) Title of your application
title = Agrio

# (str) Package name
package.name = agrio

# (str) Package domain (needed for android/ios packaging)
package.domain = org.adrian.agrio

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,wav,mp3,ogg

# (str) Application versioning (method 1)
version = 0.1.0

# (list) Application requirements
# (comma separated e.g: requirements = sqlite3,kivy)
requirements = python3,kivy==2.2.1,pyjnius,urllib3,idna,certifi,gtts

# (str) Custom source folders for requirements
# requirements.source.kivy = ../../kivy

# (str) Presplash of the application
# presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
# icon.filename = %(source.dir)s/data/icon.png

# (list) Supported orientations
# Valid options are: landscape, portrait, all
orientation = portrait

# (list) List of service to declare
# services = NAME:ENTRYPOINT_TO_PY

#
# OSX Specific
#

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for android toolchain)
# Supported formats are: #RRGGBB #AARRGGBB or one of the following names:
# red, blue, green, black, white, gray, cyan, magenta, yellow, lightgray,
# darkgray, grey, lightgreen, lightcyan, lightmagenta, lightyellow, purple,
# orange, olive, pink, brown, maroon, navy, teal, silver, lime, gold, indigo, violet
android.presplash_color = #000000

# (string) Presplash animation effect on show (see try / except in _android.py)
# android.presplash_animation = fade

# (string) Presplash animation effect on hide (see try / except in _android.py)
# android.fade_animation = fade

# (list) Permissions
android.permissions = INTERNET,RECORD_AUDIO,MODIFY_AUDIO_SETTINGS

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 24

# (int) Android SDK version to use
# android.sdk = 20

# (str) Android NDK version to use
android.ndk = 28c

# (int) Android NDK API to use. This is the minimum API you want your APP to support,
# specifiying the value here will override android.minapi
# android.ndk_api = 21

# (bool) Use --private data storage (True) or --dir public storage (False)
# android.private_storage = True

# (str) Android entry point, default is ok for Kivy-based app
# android.entrypoint = org.kivy.android.PythonActivity

# (list) Full names of packages to add to android manifest application tag
# android.add_activities = com.example.ExampleActivity

# (list) Android application meta-data to set (key=value format)
# android.meta_data =

# (list) Android library project to add (will be added to the
# project.properties automatically.)
# android.add_libs_aar =

# (list) Android prebuilt libraries to add
# android.add_libs_arm64_v8a =
# android.add_libs_armeabi_v7a =
# android.add_libs_x86 =
# android.add_libs_x86_64 =

# (bool) Copy library instead of making a libpymodules.so
# android.copy_libs = 1

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) XML file for custom backup rules (see android.allow_backup)
# android.backup_rules =

# (str) If you need to insert variables into your AndroidManifest.xml
# You can do this with the manifestPlaceholders property
# android.manifest_placeholders =

# (bool) forces Android to start the application from the launcher
# android.force_start = False

# (bool) disables the built-in Android keyboard dictation
# android.disable_keyboard_dictation = False

#
# Python for android (p4a) specific
#

# (str) python-for-android version to use
# p4a.version =

# (str) python-for-android fork to use, if empty defaults to upstream
# p4a.fork =

# (str) python-for-android branch to use, if empty defaults to master
# p4a.branch =

# (str) python-for-android specific commit to use
# p4a.commit =

# (str) python-for-android git clone directory (if empty, it will be automatically cloned from github)
# p4a.source_dir =

# (list) Directory to copy into android project
# p4a.add_dir =

# (list) str ignored by p4a (--ignore-path)
# p4a.ignore_path =

# (str) bootstrap to use for android
# p4a.bootstrap = sdl2

# (int) port number to specify an explicit port to use for p4a server
# p4a.port =

# (bool) Indicate if the application should be compiled with debug mode
# android.debug = True

# (str) The format used to package the app for release mode (aab or apk or aar)
# android.release_artifact = aab

# (str) The format used to package the app for debug mode (aab or apk or aar)
# android.debug_artifact = apk

#
# iOS specific
#

# (str) Path to a custom Xcode project
# ios.codesign.debug = "iPhone Developer: <Name> (<ID>)"

# (str) Path to a custom Xcode project
# ios.codesign.release = "iPhone Distribution: <Name> (<ID>)"

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if run as root (0 = no, 1 = yes)
warn_on_root = 1

# (str) Path to build directory (if empty, it will be automatically defaults to ./buildozer)
# build_dir = ./.buildozer

# (str) Path to bin directory (if empty, it will be automatically defaults to ./bin)
# bin_dir = ./bin

#    -----------------------------------------------------------------------------
#    List as sections
#
#    You can define any number of custom sections here
#    (they will be handled by the custom buildozer command/hook)
#    -----------------------------------------------------------------------------
