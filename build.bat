@echo off
echo 开始打包应用...

echo 清理旧的构建文件...
rmdir /s /q dist 2>nul
rmdir /s /q build 2>nul

echo 安装依赖...
npm install

echo 构建应用...
npm run build

echo 打包完成！
echo 安装文件位于 dist 目录下
pause 