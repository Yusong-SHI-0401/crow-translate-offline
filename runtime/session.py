#!/usr/bin/env python3
"""The engine's lifetime follows Crow's lifetime, including startup failures."""
import errno
import json
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from common import ROOT, URL, environment

ENV = environment()
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api(path, payload=None, timeout=60):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(URL + path, data=data, headers={"Content-Type": "application/json"})
    with HTTP.open(request, timeout=timeout) as response:
        return json.load(response)


def translate(text, source="en", target="zh"):
    start = time.monotonic()
    result = api("/translate", {"q": text, "source": source, "target": target, "format": "text"})
    if not result.get("translatedText"):
        raise RuntimeError("The local engine returned an empty translation")
    return {"source": text, "translation": result["translatedText"], "seconds": round(time.monotonic() - start, 3)}


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def verify(engine, ready):
    results = [translate("Single-cell RNA sequencing reveals changes in gene expression."),
               translate("We identified distinct cell types in the human retina."),
               translate("我们研究基因表达和细胞类型。", "zh", "en")]
    cli = []
    for source, target, text in [("en", "zh-CN", "This study identifies different cell types."),
                                 ("zh-CN", "en", "我们研究基因表达。")]:
        start = time.monotonic()
        proc = subprocess.run([str(ROOT / "crow/AppRun"), "-e", "libretranslate", "-s", source,
                               "-t", target, "--tts-provider", "none", "-b", text],
                              env=ENV, capture_output=True, text=True, timeout=60)
        if proc.returncode or not proc.stdout.strip():
            raise RuntimeError(f"Crow CLI failed: {proc.stderr.strip()}")
        cli.append({"source": text, "translation": proc.stdout.strip(), "seconds": round(time.monotonic() - start, 3)})
    with socket.socket() as sock:
        sock.settimeout(2)
        try:
            sock.connect(("192.0.2.1", 443))  # RFC 5737 address, no public service is queried.
        except OSError as exc:
            if exc.errno != errno.ENETUNREACH:
                raise RuntimeError(f"Unexpected isolation result: {exc}") from exc
        else:
            raise RuntimeError("An external route exists; refusing to call this offline")
    rss = next(line for line in Path(f"/proc/{engine.pid}/status").read_text().splitlines() if line.startswith("VmRSS:"))
    result = {"network_interfaces": [name for _, name in socket.if_nameindex()],
              "external_network": "ENETUNREACH", "engine_ready_seconds": ready,
              "api_tests": results, "crow_cli_tests": cli, "engine_rss": rss}
    report = ROOT / "state" / f"verification-{time.time_ns()}.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    print(f"PASS — saved {report}", flush=True)


def main():
    if [name for _, name in socket.if_nameindex()] != ["lo"]:
        raise RuntimeError("A loopback-only network namespace is required; use crow-offline.")
    mode = sys.argv[1] if len(sys.argv) > 1 else "gui"
    if mode not in {"gui", "test"}:
        raise RuntimeError("Unknown session mode")
    engine = crow = None
    started = time.monotonic()
    try:
        engine = subprocess.Popen([str(ROOT / "engine/bin/python"), str(ROOT / "server.py"),
            "--host", "127.0.0.1", "--port", "5805", "--load-only", "en,zh", "--threads", "2",
            "--disable-web-ui", "--disable-files-translation"], env=ENV, cwd=ROOT / "state")
        deadline = time.monotonic() + 90
        while True:
            if engine.poll() is not None:
                raise RuntimeError(f"Engine exited with code {engine.returncode}")
            try:
                languages = api("/languages", timeout=1)
                if {lang["code"] for lang in languages} != {"en", "zh-Hans"}:
                    raise RuntimeError("The expected English/Chinese models are not installed")
                break
            except (OSError, ValueError):
                if time.monotonic() > deadline:
                    raise RuntimeError("The engine did not start within 90 seconds")
                time.sleep(0.2)
        ready = round(time.monotonic() - started, 3)
        if mode == "test":
            verify(engine, ready)
            return
        translate("Translation is ready.")
        crow = subprocess.Popen([str(ROOT / "crow/AppRun")], env=ENV, cwd=ROOT)
        print(f"Crow started; engine ready in {ready}s; no external network", flush=True)
        while crow.poll() is None:
            if engine.poll() is not None:
                raise RuntimeError("The local engine stopped unexpectedly")
            time.sleep(0.5)
        if crow.returncode:
            raise RuntimeError(f"Crow exited with code {crow.returncode}")
    finally:
        stop(crow)
        stop(engine)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    main()
