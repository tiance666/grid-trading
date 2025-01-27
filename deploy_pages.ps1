# 设置变量
$GITHUB_USERNAME = "tiance666"
$REPO_NAME = "grid-trading"

# 创建临时目录
New-Item -ItemType Directory -Force -Path "temp_pages"

# 复制前端文件
Copy-Item "src/server/dist/*" -Destination "temp_pages/" -Recurse

# 初始化git仓库
Set-Location temp_pages
git init
git checkout -b gh-pages

# 添加文件
git add .
git config --global user.email "deploy@example.com"
git config --global user.name "Deploy Bot"
git commit -m "Deploy to GitHub Pages"

# 推送到GitHub
git remote add origin "https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
git push -f origin gh-pages

# 清理
Set-Location ..
Remove-Item -Recurse -Force temp_pages 