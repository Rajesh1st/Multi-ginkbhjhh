from flask import Flask, jsonify, request, Response
from CFSession import cfSession, cfDirectory
import threading
import os
import logging

CACHE_DIR = os.path.join(os.getcwd(), "cache")
WEB_TARGET = "https://multimovies.golf/"

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Renewer():
    def __init__(self, target: str):
        self.renewing = False
        self.target = target
        self._thread = None

    def _renew_backend(self, session: cfSession):
        self.renewing = True
        try:
            resp = session.get(self.target)
            logger.info(f"Renewed cookies, status: {resp.status_code}")
        except Exception as e:
            logger.error(f"Renew error: {e}")
        finally:
            self.renewing = False
    
    def renew(self, session: cfSession):
        if self.renewing:
            return {"status": False, "reason": "Renew already running"}

        response = session.session.get(self.target)
        if response.status_code == 200:
            return {"status": False, "reason": "Cookie already valid"}

        self._thread = threading.Thread(
            target=self._renew_backend, args=(session,)
        )
        self._thread.start()
        return {"status": True, "reason": "Cookie invalid, regenerating"}

def isSiteValid(url):
    response = session.session.get(url)
    return response.status_code == 200

def reverse_proxy(url, params=None):
    if params:
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        target_url = f"{WEB_TARGET}{url}?{query}"
    else:
        target_url = WEB_TARGET + url

    res = session.get(target_url)
    return res.content

@app.before_request
def before_request():
    if not isSiteValid(WEB_TARGET):
        renewer.renew(session)

@app.route("/getcookie", methods=["GET"])
def getcookie():
    return jsonify(renewer.renew(session))

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path):
    data = reverse_proxy("/" + path, request.args)
    return Response(data, content_type="text/html")

if __name__ == "__main__":
    session = cfSession(directory=cfDirectory(CACHE_DIR), headless_mode=True)
    renewer = Renewer(target=WEB_TARGET)
    app.run("0.0.0.0", port=8080)
