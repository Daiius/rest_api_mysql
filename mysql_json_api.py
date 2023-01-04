# Concept tests for MySQL REST API Server
#
# Using MySQL database like REST API server,
# with basic authentication
#
# Memo:
#   Account and session management:
#     if header has authentication information, this program use it in pymysql.connect.
#     if not, read only account is used.
#     however, pymysql.connection is reused in this program to use transaction functions,
#     which means thrid persion using the same username can access DB without password
#     after true user entering password and establishing connection.
#
#     To avoid this, this program caches hash of authentication information
#     just after successful authentication from database.
#     When wrong information is set in request header, 401 is returned.
#
#     Session management is additional option, but it might lead too many connections
#     and timeout-disconnect controling...

import http.server
import http.cookies
import socketserver
import urllib.parse

import json
import pymysql
import pymysql.cursors

import hashlib

import server_info

PORT = 8000
ADDRESS = ("", PORT)

READONLY_USER = "test_user"
READONLY_PASS = "test_user"

def default_proc(obj):
    return str(obj)

class ApiHTTPRequiestHandler(http.server.BaseHTTPRequestHandler):

    # connection pools
    # connections[username] = (connection, cached_auth_info)
    connections = {}

    @staticmethod
    def connect(username, password):
        return pymysql.connect(
            host=server_info.host, user=username, passwd=password,
            database=server_info.database, autocommit=True
        )


    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        decoded_query = urllib.parse.unquote(parsed_path.query)

        if decoded_query == "":
            # No response to empty query
            return
    
        # Authentication
        auth = self.headers["Authentication"]
        if auth:
            auth_data = auth.replace('Basic: ', '').decode('utf-8')
            [username, password] = auth_data.split(":")
        else:
            username = READONLY_USER
            password = READONLY_PASS

        hasher = haslib.sha256()
        hasher.update(username)
        hasher.update(password)
        hashed_auth_info = hasher.hexdigest()

        # Establishing / Using cached connection
        if connections[username] is None:
            # new connection
            try:
                new_connection = ApiHTTPRequiestHandler.connect(
                    READONLY_USER, READONLY_PASS
                )
                ApiHTTPRequiestHandler.connections[username] = (new_connection, hashed_auth_info)
                connection = new_connection
            except Exception as e:
                status_code = 500
                data_to_send = json.dumps(str(e)).encode('utf-8')
        else:
            cached_connection, cached_auth_info = ApiHTTPRequiestHandler.connections[username]
            if hashed_auth_info == auth_info:
                connection = cached_connection
            else:
                # User sending request is using wrong authentication information!
                status_code = 401 # Set status code Unauthorized, and ensure connection is None

        if connection is not None:
            for iretry in range(MAX_RETRY_COUNT):
                try:
                    with connection:
                        with connection.cursor() as cursor:
                            cursor.execute(decoded_query)
                            result = cursor.fetchall()
                    data_to_send = json.dumps(result, default=default_proc).encode('utf-8')
                    status_code = 200
                    break # Exit retry loop
                except pymysql.err.ProgrammingError as e:
                    # SQL syntax error
                    status_code = 400
                    data_to_send = json.dump(str(e)).encode('utf-8')
                    break # Exit retry loop
                except Exception as e:
                    # Errors including old connection timeout
                    
                    # Replace connection to new one
                    new_connection = ApiHTTPRequiestHandler.connect(username, password)
                    connections[username] = (new_connection, hashed_auth_info)
                    connection = new_connection
                    status_code = 500
                    data_to_send = json.dumps(str(e)).encode('utf-8')
                    # Entering retry loop

        self.send_response(status_code)
        self.send_header('Content-Type', 'text/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(data_to_send)

with socketserver.TCPServer(ADDRESS, ApiHTTPRequiestHandler) as httpd:
    print("serving at a port", PORT)
    httpd.serve_forever()

