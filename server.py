import http.server
import socketserver
import json
import sqlite3
import random
import time
import re
import urllib.parse
from datetime import datetime

PORT = 3000

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('demo.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            items TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS verification_codes (
            phone TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            expires_at INTEGER NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

class APIHandler(http.server.BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            body = {}
            
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/api/send-code':
            self.handle_send_code(body)
        elif path == '/api/login':
            self.handle_login(body)
        elif path == '/api/orders':
            self.handle_create_order(body)
        elif path == '/api/pay/callback':
            self.handle_pay_callback(body)
        else:
            self.send_error_response(404, "Not Found")

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path.startswith('/api/orders/'):
            user_id = path.split('/')[-1]
            self.handle_get_orders(user_id)
        else:
            self.send_error_response(404, "Not Found")
            
    def send_json_response(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
        
    def send_error_response(self, status, message):
        self.send_json_response(status, {"error": message})

    def handle_send_code(self, body):
        phone = body.get('phone')
        if not phone or not re.match(r'^1[3-9]\d{9}$', phone):
            return self.send_error_response(400, "Invalid phone number")
            
        code = str(random.randint(100000, 999999))
        expires_at = int(time.time()) + 300 # 5 minutes validity
        
        conn = sqlite3.connect('demo.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO verification_codes (phone, code, expires_at) VALUES (?, ?, ?)', (phone, code, expires_at))
        conn.commit()
        conn.close()
        
        print(f"\\n{'='*40}\\n[MOCK SMS] 您的验证码是: {code} (5分钟内有效)\\n{'='*40}\\n")
        self.send_json_response(200, {"message": "Code generated and printed to server console"})

    def handle_login(self, body):
        phone = body.get('phone')
        code = body.get('code')
        
        if not phone or not code:
            return self.send_error_response(400, "Phone and code are required")
            
        conn = sqlite3.connect('demo.db')
        c = conn.cursor()
        c.execute('SELECT code, expires_at FROM verification_codes WHERE phone = ?', (phone,))
        row = c.fetchone()
        
        if not row:
            conn.close()
            return self.send_error_response(400, "No code found for this phone")
            
        stored_code, expires_at = row
        
        if int(time.time()) > expires_at:
            conn.close()
            return self.send_error_response(400, "Code expired")
            
        if code != stored_code and code != "123456": # Allow 123456 for hardcoded test
            conn.close()
            return self.send_error_response(400, "Invalid code")
            
        # Clean up code
        c.execute('DELETE FROM verification_codes WHERE phone = ?', (phone,))
        
        # Get or create user
        c.execute('SELECT id FROM users WHERE phone = ?', (phone,))
        user_row = c.fetchone()
        
        if user_row:
            user_id = user_row[0]
        else:
            now_str = datetime.now().isoformat()
            c.execute('INSERT INTO users (phone, created_at) VALUES (?, ?)', (phone, now_str))
            user_id = c.lastrowid
            
        conn.commit()
        conn.close()
        
        self.send_json_response(200, {"id": user_id, "phone": phone})

    def handle_create_order(self, body):
        user_id = body.get('userId')
        items = body.get('items', [])
        
        if not user_id or not items:
            return self.send_error_response(400, "Missing user_id or items")
            
        total_amount = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
        
        now = datetime.now()
        date_str = now.strftime('%Y%m%d')
        order_id = f"#ORD-{date_str}{random.randint(1000, 9999)}"
        created_at = now.isoformat()
        
        conn = sqlite3.connect('demo.db')
        c = conn.cursor()
        c.execute('INSERT INTO orders (id, user_id, items, total_amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                  (order_id, user_id, json.dumps(items), total_amount, 'pending', created_at))
        conn.commit()
        conn.close()
        
        self.send_json_response(200, {
            "orderId": order_id,
            "totalAmount": total_amount,
            "qrCodeUrl": f"mock://pay?order={order_id}"
        })

    def handle_pay_callback(self, body):
        order_id = body.get('orderId')
        status = body.get('status')
        
        if not order_id or status != 'SUCCESS':
            return self.send_error_response(400, "Invalid callback data")
            
        conn = sqlite3.connect('demo.db')
        c = conn.cursor()
        c.execute('UPDATE orders SET status = ? WHERE id = ?', ('paid', order_id))
        rows_affected = c.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            print(f"\\n[PAYMENT CALLBACK] Order {order_id} marked as PAID.\\n")
            self.send_json_response(200, {"message": "Success"})
        else:
            self.send_error_response(404, "Order not found")

    def handle_get_orders(self, user_id):
        if not user_id.isdigit():
            return self.send_error_response(400, "Invalid user ID")
            
        conn = sqlite3.connect('demo.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        rows = c.fetchall()
        conn.close()
        
        orders = []
        for row in rows:
            orders.append({
                "id": row['id'],
                "date": row['created_at'].replace('T', ' ').split('.')[0],
                "items": json.loads(row['items']),
                "total": row['total_amount'],
                "status": "已付款" if row['status'] == 'paid' else "待付款"
            })
            
        self.send_json_response(200, orders)

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), APIHandler) as httpd:
        print(f"\\n后端服务已启动，正在监听端口 {PORT}...\\n")
        httpd.serve_forever()
