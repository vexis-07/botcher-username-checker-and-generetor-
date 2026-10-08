[app]
title = BOTCHER
package.name = botcher
package.domain = org.botcher
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy,httpx,certifi,openssl,android
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 31
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.debug_artifact = True

[app:android]
android.presplash_color = #0a1520

[buildozer]
log_level = 2
warn_on_root = 1
