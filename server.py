import http.server
import socketserver
import json
import sqlite3
import hashlib
import os

PORT = 3000
DB_FILE = 'database.sqlite'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return hashed.hex(), salt

class APIHandler(http.server.SimpleHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_error_response(400, "Invalid JSON")
            return

        if self.path == '/api/register':
            self.handle_register(data)
        elif self.path == '/api/login':
            self.handle_login(data)
        elif self.path == '/api/reset-password':
            self.handle_reset_password(data)
        else:
            self.send_error_response(404, "Endpoint not found")

    def handle_reset_password(self, data):
        phone = data.get('phone')
        password = data.get('password')

        if not phone or not password:
            self.send_error_response(400, "Missing required fields")
            return

        password_hash, salt = hash_password(password)

        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET password_hash = ?, salt = ? WHERE phone = ?', (password_hash, salt, phone))
            if cursor.rowcount == 0:
                conn.close()
                self.send_error_response(404, "User not found")
                return
            conn.commit()
            conn.close()
            self.send_success_response({"message": "Password reset successful"})
        except Exception as e:
            self.send_error_response(500, str(e))

    def handle_register(self, data):
        username = data.get('username')
        phone = data.get('phone')
        password = data.get('password')

        if not username or not phone or not password:
            self.send_error_response(400, "Missing required fields")
            return

        password_hash, salt = hash_password(password)

        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, phone, password_hash, salt) VALUES (?, ?, ?, ?)',
                (username, phone, password_hash, salt)
            )
            conn.commit()
            conn.close()
            
            self.send_success_response({"message": "Registration successful"})
        except sqlite3.IntegrityError:
            self.send_error_response(409, "Username or phone already exists")
        except Exception as e:
            self.send_error_response(500, str(e))

    def handle_login(self, data):
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            self.send_error_response(400, "Missing required fields")
            return

        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, phone, password_hash, salt FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            conn.close()

            if user:
                user_id, db_username, db_phone, db_hash, db_salt = user
                test_hash, _ = hash_password(password, db_salt)
                
                if test_hash == db_hash:
                    self.send_success_response({
                        "id": user_id,
                        "username": db_username,
                        "phone": db_phone
                    })
                    return

            self.send_error_response(401, "Invalid username or password")
        except Exception as e:
            self.send_error_response(500, str(e))

    def send_success_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_response(self, status_code, message):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode('utf-8'))

    # Disable logging to keep console clean
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    init_db()
    with socketserver.TCPServer(("", PORT), APIHandler) as httpd:
        print(f"Server starting on port {PORT}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
