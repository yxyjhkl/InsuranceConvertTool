@echo off
cd /d D:\APKbuild\InsuranceConvertTool
set ANDROID_SDK_ROOT=C:\Users\HP\AppData\Local\Android\Sdk
set ANDROID_HOME=C:\Users\HP\AppData\Local\Android\Sdk
set PATH=%PATH%;C:\Users\HP\AppData\Roaming\Python\Python38\Scripts
python -m buildozer android debug
pause