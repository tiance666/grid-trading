<template>
  <div class="grid-trading">
    <div class="trading-params">
      <el-form :model="form" label-width="120px">
        <el-form-item label="交易对">
          <el-select v-model="form.symbol">
            <el-option label="BTC/USDT" value="BTCUSDT"/>
            <el-option label="ETH/USDT" value="ETHUSDT"/>
          </el-select>
        </el-form-item>
        
        <el-form-item label="网格数量">
          <el-input-number v-model="form.gridCount" :min="4" :max="50"/>
        </el-form-item>
        
        <el-form-item label="网格高度(%)">
          <el-input-number 
            v-model="form.gridHeight" 
            :min="0.1" 
            :max="10"
            :step="0.1"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="startTrading">
            开始交易
          </el-button>
          <el-button type="danger" @click="stopTrading">
            停止交易
          </el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <!-- 交易状态展示 -->
    <div class="trading-status">
      <el-table :data="activeOrders">
        <el-table-column prop="symbol" label="交易对"/>
        <el-table-column prop="side" label="方向"/>
        <el-table-column prop="price" label="价格"/>
        <el-table-column prop="amount" label="数量"/>
        <el-table-column prop="status" label="状态"/>
      </el-table>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'GridTrading',
  setup() {
    const form = reactive({
      symbol: 'BTCUSDT',
      gridCount: 10,
      gridHeight: 1.0,
      investment: 1000
    })
    
    const activeOrders = ref([])
    const isTrading = ref(false)
    
    const startTrading = async () => {
      try {
        const response = await fetch('/api/grid/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(form)
        })
        
        if (response.ok) {
          isTrading.value = true
          ElMessage.success('网格交易已启动')
          startOrdersPolling()
        } else {
          throw new Error('启动失败')
        }
      } catch (error) {
        ElMessage.error(`启动失败: ${error.message}`)
      }
    }
    
    const stopTrading = async () => {
      try {
        const response = await fetch('/api/grid/stop', {
          method: 'POST'
        })
        
        if (response.ok) {
          isTrading.value = false
          ElMessage.success('网格交易已停止')
          stopOrdersPolling()
        } else {
          throw new Error('停止失败')
        }
      } catch (error) {
        ElMessage.error(`停止失败: ${error.message}`)
      }
    }
    
    let pollInterval
    
    const startOrdersPolling = () => {
      pollInterval = setInterval(async () => {
        try {
          const response = await fetch('/api/grid/orders')
          if (response.ok) {
            activeOrders.value = await response.json()
          }
        } catch (error) {
          console.error('获取订单失败:', error)
        }
      }, 2000)
    }
    
    const stopOrdersPolling = () => {
      if (pollInterval) {
        clearInterval(pollInterval)
      }
    }
    
    return {
      form,
      activeOrders,
      isTrading,
      startTrading,
      stopTrading
    }
  }
}
</script>

<style scoped>
.grid-trading {
  padding: 20px;
}

.trading-params {
  max-width: 600px;
  margin-bottom: 20px;
}

.trading-status {
  margin-top: 20px;
}
</style> 