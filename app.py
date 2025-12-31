from flask import Flask, jsonify, request, Response
from CFSession import cfSession, cfDirectory
import threading, os, logging

CACHE_DIR = os.path.join(os.getcwd(), "cache")
WEB_TARGET = "https://multimovies.golf/"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Renewer:
    def __init__(self, target):
        self.renewing = False
        self.target = target
        self._thread = None

    def _renew_backend(self, session):
        self.renewing = True
        try:
            resp = session.get(self.target)
            logger.info(f"Renewed cookie: {resp.status_code}")
        except Exception as e:
            logger.error(str(e))
        finally:
            self.renewing = False

    def renew(self, session):
        if self.renewing:
            return {"status": False, "reason": "Already renewing"}

        resp = session.session.get(self.target)
        if resp.status_code == 200:
            return {"status": False, "reason": "Cookie already valid"}

        self._thread = threading.Thread(
            target=self._renew_backend,
            args=(session,)
        )
        self._thread.start()
        return {"status": True, "reason": "Renewing cookie"}

def reverse_proxy(path):
    url = WEB_TARGET + path
    if request.query_string:
        url += "?" + request.query_string.decode()

    res = session.get(url)
    return Response(res.content, status=res.status_code)

@app.before_request
def before():
    if session.session.get(WEB_TARGET).status_code != 200:
        renewer.renew(session)

@app.route("/getcookie")
def getcookie():
    return jsonify(renewer.renew(session))

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path):
    return reverse_proxy(path)

if __name__ == "__main__":
    session = cfSession(directory=cfDirectory(CACHE_DIR), headless_mode=True)
    renewer = Renewer(WEB_TARGET)
    app.run(host="0.0.0.0", port=8080)
