// API配置
const config = {
    // API基础地址
    apiUrl: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000'  // 本地开发环境
        : 'http://47.113.144.26:8000',  // 生产环境
        
    // WebSocket地址
    wsUrl: window.location.hostname === 'localhost'
        ? 'ws://localhost:8000/ws'  // 本地开发环境
        : 'ws://47.113.144.26:8000/ws',  // 生产环境
    
    // API端点
    klineUrl: '/api/klines',
    startTradingUrl: '/api/start',
    stopTradingUrl: '/api/stop'
}; 