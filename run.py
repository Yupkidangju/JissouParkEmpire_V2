# -*- coding: utf-8 -*-
"""
실장석 공원 제국 - 서버 실행 진입점 (run.py)
[v1.8.9] 개발 서버 실행. Gunicorn에서도 app 객체 직접 사용 가능.

사용법:
    venv/bin/python run.py                  # 가상환경 내 개발 서버 기동 (또는 venv 활성화 후 python3 run.py)
    gunicorn --bind 127.0.0.1:8000 "run:app"  # Nginx 뒤에서 사용하는 프로덕션 서버
"""
import os
import sys

# Windows 콘솔 인코딩 문제 방지
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

if __name__ == '__main__':
    # [v1.8.9] 개발 서버 직접 실행 진입점인 경우, zero-setup 퀵스타트 편의성을 위해
    # 기본적으로 루프백 IP(127.0.0.1) 바인딩인 상황에 한정해서 개발용 시크릿 키를 자동으로 사전 주입합니다.
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    is_loopback = host in ('127.0.0.1', 'localhost', '::1')

    if is_loopback:
        os.environ.setdefault('DEBUG', 'true')
        os.environ.setdefault('SECRET_KEY', 'dev-secret-key-stable-jissou-desu')
    else:
        # 외부 바인딩(0.0.0.0 등) 시에는 안전하지 않은 개발용 고정 키의 무단 사용을 방지하고
        # 디버거 노출을 원천 제어하기 위해 명시적인 위험 수용과 커스텀 시크릿 키 입력을 강제합니다.
        allow_unsafe = os.environ.get('ALLOW_UNSAFE_DEV_SERVER', 'false').lower() in ('true', '1', 'yes')
        if not allow_unsafe:
            raise ValueError(
                "CRITICAL SECURITY ERROR: 외부 바인딩(FLASK_RUN_HOST가 루프백이 아님) 감지! "
                "LAN 대역 디버거 노출 및 백도어 위협을 차단하기 위해 안전 실패(Fail-Closed) 상태로 진입합니다. "
                "외부 바인딩 개발 테스트를 진행하려면 ALLOW_UNSAFE_DEV_SERVER=1 환경변수를 명시적으로 opt-in 하십시오."
            )

        current_secret = os.environ.get('SECRET_KEY') or os.environ.get('FLASK_SECRET_KEY')
        if not current_secret or current_secret == 'dev-secret-key-stable-jissou-desu':
            raise ValueError(
                "CRITICAL SECURITY ERROR: 외부 바인딩 상태에서는 기본 고정 개발용 시크릿 키(dev-secret-key-stable-jissou-desu)를 사용할 수 없습니다! "
                "로컬 세션 위조 공격 및 중간자 공격 노출을 예방하기 위해 실제 고유한 SECRET_KEY를 수동 주입해 주십시오."
            )

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("  Jissou Park Empire v1.8.9")
    print("  http://localhost:5000")
    print("=" * 60)

    # 외부 바인딩인 경우에는 디버그 모드를 강제 비활성화(False) 처리하여,
    # 웹 디버거 콘솔 및 백도어 조작 공격 표면을 즉각 소멸시킵니다.
    run_debug = True
    if not is_loopback:
        run_debug = False

    app.run(host=host, port=5000, debug=run_debug)
