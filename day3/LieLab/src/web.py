"""Local video analysis UI. Run: python -m src.web"""
import concurrent.futures
import json
import tempfile
import threading
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .common import config
from .predict import predict

ROOT = Path(__file__).resolve().parents[1]
MODELS = {'svm': 'C_SVM.joblib', 'gru': 'GRU.pt', 'minirocket': 'MiniRocket.joblib'}
JOBS = {}
LOCK = threading.Lock()
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=1)
MAX_BYTES = 100 * 1024 * 1024


def analyze(job, path, temporary, model):
    try:
        c = config()
        # All uploaded videos and extracted AU data live in this temporary directory.
        c['paths'] = dict(c['paths'], openface=Path(temporary.name)/'au')
        c['paths']['openface'].mkdir()
        result = predict(path, ROOT/'models'/MODELS[model], c)
        with LOCK:
            JOBS[job] = dict(status='done', result=result)
    except Exception:
        with LOCK:
            JOBS[job] = dict(status='error', message='動画を解析できませんでした。顔が映っている別の動画をお試しください。')
    finally:
        temporary.cleanup()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT/'site/dist'), **kwargs)

    def send_json(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urlparse(self.path).path
        if route == '/api/health':
            return self.send_json(dict(ready=True, models=list(MODELS)))
        if route.startswith('/api/jobs/'):
            with LOCK:
                state = JOBS.get(route.rsplit('/', 1)[-1])
            return self.send_json(state or dict(message='結果が見つかりません'), 200 if state else 404)
        return super().do_GET()

    def do_POST(self):
        route = urlparse(self.path).path
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'):
            return self.send_json(dict(message='この画面から解析してください'), 403)
        model = route.removeprefix('/api/analyze/')
        if not route.startswith('/api/analyze/') or model not in MODELS:
            return self.send_json(dict(message='不明なモデルです'), 404)
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            size = 0
        if not 0 < size <= MAX_BYTES:
            return self.send_json(dict(message='100MB以下の動画を選んでください'), 413)
        suffix = self.headers.get('X-Video-Suffix', '').lower()
        if suffix not in ('.mp4', '.mov', '.avi', '.wmv', '.webm', '.mkv'):
            return self.send_json(dict(message='対応していない動画形式です'), 400)
        with LOCK:
            if any(s['status'] == 'running' for s in JOBS.values()):
                return self.send_json(dict(message='別の解析が実行中です。完了後にお試しください'), 409)
            # Keep only recent result metadata in memory.
            if len(JOBS) >= 30:
                JOBS.pop(next(iter(JOBS)))
            job = uuid.uuid4().hex
            JOBS[job] = dict(status='running')
        temporary = tempfile.TemporaryDirectory(prefix='lie-lab-')
        path = Path(temporary.name)/('video'+suffix)
        self.connection.settimeout(60)
        try:
            with path.open('wb') as f:
                remaining = size
                while remaining:
                    chunk = self.rfile.read(min(1024*1024, remaining))
                    if not chunk:
                        raise ValueError('Incomplete upload')
                    f.write(chunk)
                    remaining -= len(chunk)
        except Exception:
            temporary.cleanup()
            with LOCK:
                JOBS[job] = dict(status='error', message='アップロードに失敗しました')
            return self.send_json(dict(message='アップロードに失敗しました'), 400)
        POOL.submit(analyze, job, path, temporary, model)
        self.send_json(dict(job=job), 202)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Lie Lab: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == '__main__':
    main()
