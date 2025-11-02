from flask import Flask, request, jsonify
import os, requests, json

app = Flask(__name__)
TEXTGEN_URL = os.environ.get("TEXTGEN_URL", "")
MCP_RPC_URL  = os.environ.get("MCP_RPC_URL", "http://mcp.example.com:3000/rpc")
AGENT_AUTH   = os.environ.get("AGENT_AUTH", "")

ALLOWED_METHODS = {
  "partidos.list","partidos.get","partidos.resultados",
  "jugador.list","jugador.get","jugador.by_team",
  "equipo.list","equipo.get","localidad.list","localidad.get"
}

def llm_generate(prompt, max_tokens=256):
    if not TEXTGEN_URL:
        raise RuntimeError("TEXTGEN_URL no configurado")
    resp = requests.post(TEXTGEN_URL, json={"prompt": prompt, "max_length": max_tokens}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # compatibilidad con diferentes respuestas
    return data.get("text") or (data.get("results") and data["results"][0].get("text")) or str(data)

def call_mcp(method, params, id=1):
    payload = {"jsonrpc":"2.0","method":method,"params":params or {}, "id": id}
    r = requests.post(MCP_RPC_URL, json=payload, headers={"Content-Type":"application/json"}, timeout=30)
    r.raise_for_status()
    return r.json()

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/api/ask")
def ask():
    if AGENT_AUTH:
        token = request.headers.get("Authorization","")
        if token != AGENT_AUTH:
            return jsonify({"error":"unauthorized"}), 401

    body = request.get_json() or {}
    prompt = body.get("prompt","")
    if not prompt:
        return jsonify({"error":"missing prompt"}), 400

    instruction = (
      "Devuelve SOLO un JSON con campos: method (string), params (object). "
      "Ejemplo: {\"method\":\"partidos.list\",\"params\":{}}. Usuario: " + prompt
    )

    try:
      text = llm_generate(instruction, max_tokens=256)
    except Exception as e:
      return jsonify({"error":"llm_error","message": str(e)}), 500

    try:
      j = text[text.index("{"): text.rindex("}")+1]
      spec = json.loads(j)
      method = spec.get("method")
      params = spec.get("params", {})
      if not method:
        raise ValueError("no method")
    except Exception:
      return jsonify({"error":"LLM output not parseable","raw": text}), 500

    if method not in ALLOWED_METHODS:
      return jsonify({"error":"method_not_allowed","method": method}), 403

    try:
      result = call_mcp(method, params, id=42)
      return jsonify({"ok": True, "rpc": result})
    except Exception as e:
      return jsonify({"error":"mcp_call_failed","message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",3001)))