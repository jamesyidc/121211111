import websocket
import json
import time

ws_url = 'wss://ws.okx.com:8443/ws/v5/public'

def on_message(ws, message):
    data = json.loads(message)
    
    if 'data' in data:
        arg = data.get('arg', {})
        kline_data = data.get('data', [])
        
        print(f"\n收到K线数据:")
        print(f"  频道: {arg.get('channel')}")
        print(f"  币种: {arg.get('instId')}")
        print(f"  数据条数: {len(kline_data)}")
        
        for i, kline in enumerate(kline_data):
            print(f"  K线{i+1}: 时间={kline[0]}, 开={kline[1]}, 高={kline[2]}, 低={kline[3]}, 收={kline[4]}")
        
        if len(kline_data) > 10:
            print("  (数据过多，只显示前面部分)")

def on_error(ws, error):
    print(f"错误: {error}")

def on_close(ws):
    print("连接关闭")

def on_open(ws):
    print("WebSocket连接已建立")
    
    # 订阅BTC 5分钟K线
    subscribe_msg = {
        "op": "subscribe",
        "args": [{"channel": "candle5m", "instId": "BTC-USDT-SWAP"}]
    }
    
    ws.send(json.dumps(subscribe_msg))
    print("已订阅BTC-USDT-SWAP 5m K线")

ws = websocket.WebSocketApp(ws_url,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)
ws.on_open = on_open

# 运行15秒后自动关闭
import threading
def stop_after_timeout():
    time.sleep(15)
    ws.close()

threading.Thread(target=stop_after_timeout, daemon=True).start()

ws.run_forever()
