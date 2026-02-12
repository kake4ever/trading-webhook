"""
SPY/QQQ Trading Alert Webhook Server
Receives alerts from TradingView and sends to Telegram

Requirements:
pip install flask requests
"""

from flask import Flask, request, jsonify
import json
from datetime import datetime
import requests

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION - YOUR CREDENTIALS
# ═══════════════════════════════════════════════════════════════════════════

# Telegram Settings
TELEGRAM_BOT_TOKEN = "8528037605:AAHozFFwqn43lN2F4mWP908dxAWXhM64X9E"
TELEGRAM_CHAT_ID = "822044818"

# ═══════════════════════════════════════════════════════════════════════════
# TELEGRAM NOTIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def send_telegram(message: str) -> bool:
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            print(f"✅ Telegram message sent!")
            return True
        else:
            print(f"❌ Telegram failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# FORMAT TRADING SIGNAL
# ═══════════════════════════════════════════════════════════════════════════

def format_signal(data: dict) -> str:
    """Format trading signal for Telegram"""
    
    ticker = data.get('ticker', 'UNKNOWN')
    signal = data.get('signal', 'UNKNOWN')
    price = data.get('price', '0.00')
    confidence = data.get('confidence', 0)
    strike = data.get('strike', 0)
    rsi = data.get('rsi', 0)
    volume_ratio = data.get('volume_ratio', 0)
    vix = data.get('vix', 0)
    expiration = data.get('expiration', 'This Week')
    timeframe = data.get('timeframe', '1D')
    
    # Determine emoji and action
    if signal in ['BULLISH', 'CALL']:
        emoji = "🚀"
        action = "CALLS"
        signal = "BULLISH"
    else:
        emoji = "🔻"
        action = "PUTS"
        signal = "BEARISH"
    
    # Calculate strike if not provided
    if not strike or strike == 0:
        try:
            current_price = float(price)
            rounding = 5 if ticker == "QQQ" else 1
            
            if signal == "BULLISH":
                strike = round(current_price / rounding) * rounding + rounding
            else:
                strike = round(current_price / rounding) * rounding - rounding
        except:
            strike = "N/A"
    
    # Estimate premium
    try:
        if 'DTE' in str(expiration) or expiration == "TODAY":
            premium_est = "$0.50-$1.50 (0DTE)"
        elif 'Week' in str(expiration):
            premium_est = "$1.50-$3.50 (weekly)"
        else:
            premium_est = "$3.00-$6.00 (longer)"
    except:
        premium_est = "Check chain"
    
    # VIX context
    try:
        vix_num = float(vix)
        if vix_num < 15:
            vix_context = "LOW (cheap premiums) ✅"
        elif vix_num < 20:
            vix_context = "NORMAL (fair premiums)"
        elif vix_num < 25:
            vix_context = "ELEVATED (expensive) ⚠️"
        else:
            vix_context = "HIGH (very expensive) ⚠️"
    except:
        vix_context = str(vix)
    
    # Format message
    message = f"""{emoji} <b>{ticker} {action} SIGNAL</b> {emoji}

<b>Direction:</b> {signal}
<b>Confidence:</b> {confidence}/10 {'🔥' if confidence >= 9 else '✅' if confidence >= 8 else '⚠️'}

<b>💰 OPTIONS SETUP:</b>
<b>Strike:</b> ${strike} (1 strike OTM)
<b>Expiration:</b> {expiration}
<b>Est. Premium:</b> {premium_est}

<b>📊 TECHNICALS:</b>
<b>Current Price:</b> ${price}
<b>RSI:</b> {round(float(rsi), 1) if rsi else 'N/A'}
<b>Volume:</b> {round(float(volume_ratio), 2) if volume_ratio else 'N/A'}x average
<b>VIX:</b> {vix} ({vix_context})

<b>✅ TRADE PLAN:</b>
1. Review chart on TradingView
2. Check bid/ask spread (&lt; $0.10 for SPY, &lt; $0.20 for QQQ)
3. Enter if spread is tight
4. Target: +50% (T1), +100% (T2)
5. Stop: -30% or 1 day before exp

<b>⏰ Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    return message.strip()


# ═══════════════════════════════════════════════════════════════════════════
# FLASK WEBHOOK SERVER
# ═══════════════════════════════════════════════════════════════════════════

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Receive TradingView webhook alerts"""
    
    try:
        # Get JSON data from TradingView
        data = request.get_json()
        
        if not data:
            # Try to parse from text if JSON fails
            data = request.get_data(as_text=True)
            if data:
                print(f"📥 Received text data: {data}")
                # Send as-is to Telegram
                send_telegram(f"<b>Trading Signal:</b>\n\n{data}")
                return jsonify({"status": "success", "message": "Text alert sent"}), 200
            else:
                return jsonify({"status": "error", "message": "No data received"}), 400
        
        print(f"\n{'='*60}")
        print(f"🔔 NEW SIGNAL RECEIVED: {datetime.now()}")
        print(f"{'='*60}")
        print(json.dumps(data, indent=2))
        
        # Format and send signal
        signal_message = format_signal(data)
        send_telegram(signal_message)
        
        return jsonify({
            "status": "success",
            "message": "Signal processed and sent to Telegram",
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/test', methods=['GET'])
def test():
    """Test endpoint to verify server is running"""
    return jsonify({
        "status": "online",
        "message": "SPY/QQQ Webhook Server is running! ✅",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/test-signal', methods=['POST', 'GET'])
def test_signal():
    """Test endpoint to send a sample signal"""
    
    test_data = {
        "ticker": "SPY",
        "signal": "CALL",
        "price": "582.50",
        "confidence": 9,
        "strike": 584,
        "rsi": 55.3,
        "volume_ratio": 2.1,
        "vix": 16.8,
        "expiration": "This Week",
        "timeframe": "1H",
        "time": datetime.now().isoformat()
    }
    
    signal_message = format_signal(test_data)
    success = send_telegram(signal_message)
    
    if success:
        return jsonify({
            "status": "success",
            "message": "Test signal sent to Telegram! Check your phone 📱",
            "data": test_data
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to send test signal"
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  SPY/QQQ Trading Alert Webhook Server                     ║")
    print("║  Ready to receive TradingView alerts!                     ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    # Get port from environment (for cloud deployment) or use 5001 for local
    port = int(os.environ.get('PORT', 5001))
    
    print(f"\n🚀 Server starting on port {port}")
    print(f"📡 Webhook endpoint: /webhook")
    print(f"🧪 Test endpoint: /test")
    print(f"📱 Telegram: ENABLED")
    print(f"   Bot: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"   Chat: {TELEGRAM_CHAT_ID}")
    print(f"\n⏳ Waiting for signals...\n")
    
    # Run Flask server
    # Note: debug=False for production deployment
    app.run(host='0.0.0.0', port=port, debug=False)
