from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

app = FastAPI()

# 挂载静态文件目录
app.mount("/docs", StaticFiles(directory="docs"), name="docs")
app.mount("/dist", StaticFiles(directory="dist"), name="dist")

@app.get("/")
async def root():
    return FileResponse("docs/index.html")

@app.get("/download")
async def download():
    installer_path = "dist/网格交易系统 Setup 1.0.0.exe"
    if not os.path.exists(installer_path):
        raise HTTPException(status_code=404, detail="安装程序文件未找到")
    return FileResponse(
        installer_path,
        filename="网格交易系统 Setup 1.0.0.exe",
        media_type="application/octet-stream"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080) 