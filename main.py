"""
EMR_AI_24clinic - 의사랑 EMR 보조 도구
실행: python main.py
"""
import subprocess
import sys
import webbrowser
import time
import threading

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8080")

if __name__ == "__main__":
    print("EMR_AI_24clinic 시작 중...")
    print("브라우저: http://localhost:8080")
    print("종료: Ctrl+C\n")

    threading.Thread(target=open_browser, daemon=True).start()

    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app.server:app",
        "--host", "127.0.0.1",
        "--port", "8080",
        "--reload"
    ])
