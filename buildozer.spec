[app]

title = 金尊分红演示
package.name = jinzunfenhong
package.domain = com.insurance

source.dir = .
source.include_exts = py,png,jpg,kv,json
source.include_patterns = data/*,assets/*

version = 2.0.0

requirements = python3,kivy,pdfplumber,pdfminer.six,openpyxl,pillow

orientation = portrait
fullscreen = 1

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 31
android.minapi = 24
android.ndk = 25c

android.arch = arm64-v8a
android.allow_backup = True
android.presplash_color = #FFFFFF
android.logcat_filters = *:S python:D

ios.kivy_ios = False

[buildozer]
log_level = 2
warn_on_root = 1