@echo off
cd /d D:\APKbuild\InsuranceConvertTool
echo 初始化Git仓库...
git init
git add .
git commit -m "Initial commit - APK build project"

echo.
echo 添加远程仓库...
git remote add origin https://github.com/yxyjhkl/InsuranceConvertTool.git

echo.
echo 推送到GitHub...
git push -u origin main

echo.
echo ========================================
echo 构建APK:
echo 1. 打开 https://github.com/yxyjhkl/InsuranceConvertTool
echo 2. 点击 "Actions" 标签
echo 3. 查看构建进度
echo 4. 构建完成后下载 APK 文件
echo ========================================
pause