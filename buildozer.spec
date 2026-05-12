[app]

title = 金尊分红演示
package.name = jinzunfenhong
package.domain = com.insurance

source.dir = .
source.include_exts = py,png,jpg,kv,json,ttf,ttc,json
source.include_patterns = data/*,assets/*,src/*,controllers/*,screens/*

version = 2.0.0

requirements = python3,kivy,pdfplumber,pdfminer.six,openpyxl,Pillow

orientation = portrait
fullscreen = 0

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 26

android.arch = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.presplash_color = #1890ff
android.logcat_filters = *:S python:D
android.accept_sdk_license = True

ios.kivy_ios = False

[buildozer]
log_level = 2
warn_on_root = 0
build_dir = ./.buildozer
bin_dir = ./bin