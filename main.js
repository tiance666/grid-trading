const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    // 加载本地 HTML 文件
    mainWindow.loadFile('src/server/dist/index.html');

    // 打开开发者工具（可选）
    // mainWindow.webContents.openDevTools();
}

function startPythonServer() {
    // 启动 Python 后端服务
    const pythonPath = 'python'; // 或者使用具体的 Python 路径
    pythonProcess = spawn(pythonPath, ['-m', 'uvicorn', 'src.server.app:app', '--host', '0.0.0.0', '--port', '8001']);

    pythonProcess.stdout.on('data', (data) => {
        console.log(`Python stdout: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python stderr: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
    });
}

app.whenReady().then(() => {
    startPythonServer();
    createWindow();

    app.on('activate', function () {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    // 关闭 Python 进程
    if (pythonProcess) {
        pythonProcess.kill();
    }
}); 