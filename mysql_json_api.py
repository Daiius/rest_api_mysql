import http.server
import socketserver

import urllib.parse
import json
import pymysql
import pymysql.cursors

import server_info

PORT = 8000
ADDRESS = ("", PORT)

#KEEP_RUNNING = True
#def keep_running():
#    return KEEP_RUNNING

class ApiHTTPRequiestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"path: {self.path}")
        parsed_path = urllib.parse.urlparse(self.path)
        print(f"parsed url: {parsed_path}")
        decoded_query = urllib.parse.unquote(parsed_path.query)
        print(f"decoded query: {decoded_query}")

        connection = pymysql.connect(
            host=server_info.host, user=server_info.user, passwd=server_info.passwd,
            database=server_info.database
        )
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(decoded_query)
                result = cursor.fetchall()
            connection.commit()
            

            print(result)
        

        self.send_response(200)
        self.send_header('Content-Type', 'text/json; charset=utf-8')
        self.end_headers()
        #self.wfile.write(f"{{ 'test': '{decoded_query}'}}".encode("utf-8"))
        self.wfile.write(json.dumps(result).encode('utf-8'))

with socketserver.TCPServer(ADDRESS, ApiHTTPRequiestHandler) as httpd:
    print("serving at a port", PORT)
    httpd.serve_forever()
#    while keep_running():
#        httpd.handle_request()
