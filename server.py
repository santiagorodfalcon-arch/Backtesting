#!/usr/bin/env python3
import json, http.server, urllib.parse, os

try:
    import yfinance as yf
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable,'-m','pip','install','yfinance','--quiet'])
    import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {args[0]} {args[1]}")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        path = parsed.path

        if path == '/prices':
            sym = params.get('sym', [''])[0].upper()
            if not sym:
                self._json({'error': 'sym requerido'}, 400); return
            try:
                print(f"  Descargando {sym}...")
                ticker = yf.Ticker(sym)
                hist = ticker.history(period='15y', interval='1mo', auto_adjust=True)
                if hist.empty:
                    self._json({'error': f'Sin datos para {sym}'}, 404); return
                monthly = {}
                for ts, row in hist.iterrows():
                    key = ts.strftime('%Y-%m')
                    price = float(row['Close'])
                    if price > 0:
                        monthly[key] = round(price, 4)
                print(f"  {sym}: {len(monthly)} meses OK")
                self._json({'sym': sym, 'monthly': monthly})
            except Exception as e:
                self._json({'error': str(e)}, 500)

        elif path.endswith('.html') or path == '/':
            filename = path.lstrip('/') or 'backtesting_python.html'
            filepath = os.path.join(BASE_DIR, filename)
            if os.path.exists(filepath) and os.path.isfile(filepath):
                with open(filepath, 'rb') as f:
                    body = f.read()
                self.send_response(200)
                self._cors()
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(body))
                self.end_headers()
                self.wfile.write(body)
            else:
                self._json({'error': f'{filename} no encontrado'}, 404)
        else:
            self._json({'status': 'Backtesting server OK'})

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', '*')

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

# Railway usa la variable PORT, localmente usamos 7432
PORT = int(os.environ.get('PORT', 7432))
print(f"""
╔══════════════════════════════════════════╗
║   Backtesting Server — Puerto {PORT}
║   http://localhost:{PORT}/backtesting_python.html
║   Ctrl+C para detener
╚══════════════════════════════════════════╝
""")
with http.server.ThreadingHTTPServer(('', PORT), Handler) as srv:
    srv.serve_forever()
