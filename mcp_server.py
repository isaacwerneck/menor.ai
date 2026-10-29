"""Servidor HTTP JSON-RPC local e somente leitura para ferramentas MCP simples.
Por segurança, não expõe escrita, exclusão nem execução de comandos remotamente.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import secrets
import file_ops
from middleware import pesquisar_web

HOST = "127.0.0.1"
PORT = int(os.getenv("MENOR_MCP_PORT", "8765"))
TOKEN = os.getenv("MENOR_MCP_TOKEN", "").strip()
MAX_BODY = 128 * 1024

TOOLS = [
    {"name": "list_files", "description": "Lista arquivos dentro da raiz do projeto Menor.AI.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "recursive": {"type": "boolean"}}, "required": []}},
    {"name": "read_file", "description": "Lê arquivo de texto não sensível dentro do projeto.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "search_files", "description": "Pesquisa texto nos arquivos do projeto.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "web_search", "description": "Pesquisa na web se ddgs estiver instalado.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[MCP] " + fmt % args)

    def send_json(self, status: int, obj: dict | None = None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8") if obj is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok", "server": "Menor.AI MCP readonly"})
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.client_address[0] not in {"127.0.0.1", "::1"}:
            return self.send_json(403, {"error": "localhost only"})
        if TOKEN and not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + TOKEN):
            return self.send_json(401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.send_json(400, {"error": "invalid content length"})
        if length < 1 or length > MAX_BODY:
            return self.send_json(413, {"error": "request too large or empty"})
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return self.send_json(400, {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None})
        if not isinstance(req, dict) or req.get("jsonrpc") != "2.0":
            return self.send_json(400, {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": None})

        method, ident, params = req.get("method"), req.get("id"), req.get("params") or {}

        if ident is None and str(method).startswith("notifications/"):
            return self.send_json(204, None)

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "Menor.AI read-only MCP", "version": "3.2"},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                if name == "list_files":
                    out = file_ops.listar_arquivos(args.get("path", "."), args.get("recursive", True))
                elif name == "read_file":
                    if "path" not in args:
                        raise ValueError("Parâmetro obrigatório ausente: 'path'")
                    out = file_ops.ler_arquivo(args["path"])
                elif name == "search_files":
                    if "query" not in args:
                        raise ValueError("Parâmetro obrigatório ausente: 'query'")
                    out = file_ops.pesquisar_arquivos(args["query"])
                elif name == "web_search":
                    if "query" not in args:
                        raise ValueError("Parâmetro obrigatório ausente: 'query'")
                    out = pesquisar_web(args["query"])
                else:
                    return self.send_json(200, {"jsonrpc": "2.0", "id": ident, "error": {"code": -32602, "message": "Unknown/read-write tool disabled"}})
                result = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False) if not isinstance(out, str) else out}]}
            except Exception as exc:
                result = {"content": [{"type": "text", "text": f"Ferramenta falhou: {type(exc).__name__}: {exc}"}], "isError": True}
        else:
            return self.send_json(200, {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "Method not found"}})

        self.send_json(200, {"jsonrpc": "2.0", "id": ident, "result": result})


def main():
    if not TOKEN:
        print("Aviso: MCP está restrito a localhost, mas MENOR_MCP_TOKEN não foi definido.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Menor MCP read-only em http://{HOST}:{PORT}; escrita/execução remotas desativadas.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
