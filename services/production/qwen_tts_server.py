"""Local HTTP endpoint that runs each Qwen3-TTS inference in a short-lived process."""
from __future__ import annotations
import json, os, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA_ROOT=Path("/app/data").resolve()
MODEL_ID=os.environ.get("QWEN_TTS_MODEL","Qwen/Qwen3-TTS-12Hz-0.6B-Base")
LOCK=threading.Lock()

def data_path(raw):
    path=Path(raw).resolve()
    if DATA_ROOT not in path.parents:
        raise ValueError("Las rutas deben estar dentro de /app/data.")
    return path

class Handler(BaseHTTPRequestHandler):
    def respond(self,status,payload):
        body=json.dumps(payload,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path=="/healthz":
            self.respond(200,{"status":"ok","provider":"qwen3-tts-local","model":MODEL_ID})
        else:
            self.respond(404,{"error":"not_found"})

    def do_POST(self):
        if self.path!="/synthesize":
            self.respond(404,{"error":"not_found"}); return
        temp_path=None
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size<=0 or size>1_000_000: raise ValueError("Solicitud inválida.")
            payload=json.loads(self.rfile.read(size).decode("utf-8"))
            payload["text"]=str(payload.get("text","")).strip()
            payload["reference_text"]=str(payload.get("reference_text","")).strip()
            payload["language"]=str(payload.get("language","Spanish")).strip() or "Spanish"
            payload["reference_audio"]=str(data_path(str(payload.get("reference_audio",""))))
            payload["output"]=str(data_path(str(payload.get("output",""))))
            payload["model"]=MODEL_ID
            if not payload["text"] or not payload["reference_text"] or not Path(payload["reference_audio"]).is_file():
                raise ValueError("Se requieren texto, audio de referencia y transcripción.")
            Path(payload["output"]).parent.mkdir(parents=True,exist_ok=True)
            Path("/app/data/temp").mkdir(parents=True,exist_ok=True)
            with LOCK:
                with tempfile.NamedTemporaryFile("w",encoding="utf-8",suffix=".json",
                        prefix="qwen-request-",dir="/app/data/temp",delete=False) as request_file:
                    json.dump(payload,request_file,ensure_ascii=False)
                    request_file.flush()
                    temp_path=request_file.name
                result=subprocess.run([sys.executable,"/app/qwen_tts_infer.py",temp_path],
                    capture_output=True,text=True,timeout=1800,env=os.environ.copy())
            if result.returncode:
                raise RuntimeError((result.stderr or result.stdout or "Error de inferencia")[-2500:])
            output=Path(payload["output"])
            if not output.is_file() or output.stat().st_size<44:
                raise RuntimeError("Qwen3-TTS no produjo un WAV válido.")
            self.respond(200,{"status":"ok","model":MODEL_ID,"size":output.stat().st_size})
        except (ValueError,TypeError,json.JSONDecodeError) as exc:
            self.respond(400,{"error":str(exc)})
        except subprocess.TimeoutExpired:
            self.respond(504,{"error":"Qwen3-TTS excedió el tiempo máximo de síntesis."})
        except Exception as exc:
            self.respond(500,{"error":f"{type(exc).__name__}: {exc}"})
        finally:
            if temp_path:
                try: os.unlink(temp_path)
                except FileNotFoundError: pass

    def log_message(self,fmt,*args):
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}",flush=True)

if __name__=="__main__":
    ThreadingHTTPServer(("0.0.0.0",8092),Handler).serve_forever()
