from flask import Flask, jsonify, request, Response
from CFSession import cfSession, cfDirectory
import threading
import os
import logging

# ================= CONFIG =================
CACHE_DIR = os.path.join(os.getcwd(), "cache")
WEB_TARGET = "https://multimovies.golf/"

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= GLOBAL SESSION (IMPORTANT) =================
session = cfSession(
    directory=cfDirectory(CACHE_DIR),
    headless_mode=True
)

# ================= RENEWER =================
class Renewer:
    def __init__(self, target: str):
        self.target = target
        self.renewing = False
        self._thread = None

    def _renew_backend(self):
        self.renewing = True
        try:
            resp = session.get(self.target)
            logger.info(f"Cookie renewed, status={resp.status_code}")
        except Exception as e:
            logger.error(f"Renew error: {e}")
        finally:
            self.renewing = False

    def renew(self):
        if self.renewing:
            return {"status": False, "reason": "Renew already running"}

        try:
            r = session.session.get(self.target, timeout=10)
            if r.status_code == 200:
                return {"status": False, "reason": "Cookie already valid"}
        except:
            pass

        self._thread = threading.Thread(
            target=self._renew_backend, daemon=True
        )
        self._thread.start()
        return {"status": True, "reason": "Cookie invalid, regenerating"}

renewer = Renewer(target=WEB_TARGET)

# ================= HELPERS =================
def isSiteValid(url):
    try:
        r = session.session.get(url, timeout=10)
        return r.status_code == 200
    except:
        return False

def reverse_proxy(path, params=None):
    if params:
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        target_url = f"{WEB_TARGET}{path}?{query}"
    else:
        target_url = WEB_TARGET + path

    res = session.get(target_url)
    return res.content

# ================= MIDDLEWARE =================
@app.before_request
def before_request():
    # 🔥 IMPORTANT: skip these to avoid crash
    if request.method == "HEAD":
        return
    if request.path in ("/getcookie", "/health"):
        return

    try:
        if not isSiteValid(WEB_TARGET):
            renewer.renew()
    except Exception as e:
        logger.error(f"before_request error: {e}")
        return  # NEVER break request

# ================= ROUTES =================
@app.route("/getcookie", methods=["GET"])
def getcookie():
    return jsonify(renewer.renew())

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path):
    content = reverse_proxy("/" + path, request.args)
    return Response(content, content_type="text/html")

# ================= LOCAL RUN ONLY =================
if __name__ == "__main__":
    app.run("0.0.0.0", port=8080)
