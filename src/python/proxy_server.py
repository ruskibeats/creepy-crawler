from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import json

class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Forward the request to the API server
        url = f"http://localhost:8001{self.path}"
        print(f"Forwarding request to: {url}")
        
        try:
            response = urllib.request.urlopen(url)
            
            # Set response headers
            self.send_response(response.status)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Send response body
            self.wfile.write(response.read())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                "error": str(e),
                "status": "error"
            }
            self.wfile.write(json.dumps(error_response).encode())
            print(f"Error: {e}")

def run_server(port=8002):
    server_address = ('', port)
    httpd = HTTPServer(server_address, ProxyHTTPRequestHandler)
    print(f"Starting proxy server on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
