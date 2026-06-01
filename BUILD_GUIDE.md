# 빌드 & 배포 가이드 (BUILD_GUIDE.md)

## 빠른 시작 (로컬 개발)

### 1. 사전 요구사항
- Python 3.9 이상
- pip (Python 패키지 관리자)

### 2. 설치 & 실행

```bash
# 저장소 클론
git clone <your-repo-url>
cd JissouParkEmpire

# 가상환경 생성 및 활성화
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 가상환경(venv) 활성화 상태에서 서버 실행
python run.py

# 또는 가상환경 외부에서 직접 절대경로로 실행
venv/bin/python run.py
```

3. 브라우저에서 `http://localhost:5000` 접속

---

## 라즈베리파이 배포 가이드

### 1. 환경 준비

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python3 및 pip 설치 확인
sudo apt install -y python3 python3-pip python3-venv

# 프로젝트 디렉토리 생성
sudo mkdir -p /opt/jissou-park
sudo chown $USER:$USER /opt/jissou-park
```

### 2. 프로젝트 배포

```bash
# 프로젝트 복사 (scp 또는 git clone)
cd /opt/jissou-park
git clone <your-repo-url> .

# 가상환경 생성 및 의존성 설치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Gunicorn 설치 (프로덕션 WSGI 서버)
pip install gunicorn
```

### 3. 환경 변수 설정

```bash
# .env 파일 생성 (직접 생성해야 함)
cat > /opt/jissou-park/.env << 'EOF'
FLASK_ENV=production
SECRET_KEY=여기에_랜덤_시크릿키_입력_데스
TURN_INTERVAL=600
EOF
```

> **중요**: `SECRET_KEY`는 `python3 -c "import secrets; print(secrets.token_hex(32))"` 로 생성하세요.

### 4. systemd 서비스 등록

```bash
# 서비스 파일 생성
sudo tee /etc/systemd/system/jissou-park.service << 'EOF'
[Unit]
Description=Jissou Park Empire - 실장석 공원 제국
After=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/jissou-park
Environment="PATH=/opt/jissou-park/venv/bin"
EnvironmentFile=/opt/jissou-park/.env
ExecStart=/opt/jissou-park/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --access-logfile /opt/jissou-park/logs/access.log \
    --error-logfile /opt/jissou-park/logs/error.log \
    "run:app"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

```bash
# 로그 디렉토리 생성
mkdir -p /opt/jissou-park/logs

# 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable jissou-park
sudo systemctl start jissou-park

# 상태 확인
sudo systemctl status jissou-park
```

#### Gunicorn에 맞게 run.py 수정 필요

```python
# run.py 끝에 추가 (Gunicorn이 app 객체를 인식하도록)
app = create_app()
```

### 5. Nginx 리버스 프록시 설정

```bash
# Nginx 설치
sudo apt install -y nginx

# 사이트 설정 파일 생성
sudo tee /etc/nginx/sites-available/jissou-park << 'EOF'
server {
    listen 80;
    server_name _;  # 또는 실제 도메인명

    # 정적 파일 직접 서빙 (성능 향상)
    location /static/ {
        alias /opt/jissou-park/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 애플리케이션 프록시
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 지원 (향후 실시간 기능용)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
```

```bash
# 사이트 활성화
sudo ln -sf /etc/nginx/sites-available/jissou-park /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 검증 및 재시작
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 6. 방화벽 설정

```bash
# ufw 사용 시
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

---

## 운영 명령어

```bash
# 서비스 상태 확인
sudo systemctl status jissou-park

# 서비스 재시작
sudo systemctl restart jissou-park

# 로그 확인
journalctl -u jissou-park -f
tail -f /opt/jissou-park/logs/access.log
tail -f /opt/jissou-park/logs/error.log

# 코드 업데이트 후 재배포
cd /opt/jissou-park
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart jissou-park
```

---

## 성능 최적화 및 DB 이주 지침 (라즈베리파이)

| 항목 | 설정 | 설명 |
|------|------|------|
| **Gunicorn Workers** | 2 | RPi는 코어 수가 적고 SQLite 쓰기 경합을 방지하기 위해 2개로 제한(Max 2)하여 sync 모델로 기동합니다. |
| **SQLite WAL 모드** | PRAGMA 자동 적용 (Engine 리스너) | `PRAGMA journal_mode=WAL` 및 `PRAGMA busy_timeout=5000` 주입으로 쓰기 대기를 최적화합니다. |
| **정적 파일** | Nginx 직접 서빙 | Gunicorn 부하 감소 |
| **턴 간격** | 600초 (10분) | CPU 부하 분산 |
| **DB 백업** | `cp instance/game.db backup/` | 주기적 백업 권장 |

### ⚠️ SQLite + Gunicorn 다중 워커 (Multi-Worker) 제한 지원 및 PostgreSQL 전환 기준 (Accepted Risk)
기본 설정인 SQLite 파일 DB를 다중 워커(Gunicorn) 환경에서 운영할 때, 아키텍처 특성상 다중 프로세스 동시 쓰기 레이스로 인해 `Database Locked` (busy_timeout 초과) 오류가 발생할 수 있습니다.
본 가이드에서는 다음 조건 하에 이 구성을 제한적 수용 위험(Accepted Risk, 책임자: Eunho Lim)으로 정의하며, 한계를 초과할 경우 **즉시 PostgreSQL로의 이주**를 진행해야 합니다.

1. **Gunicorn 운영 규격**: Gunicorn workers는 최대 2개로 제한하고, `--threads` 옵션을 배제한 단일 스레드 sync worker 모델을 사용하십시오.
2. **PostgreSQL 전환 트리거**:
   - 일일 동시 활성 사용자(DAU)가 100명을 초과하는 경우.
   - 피크 시간대 초당 평균 DB 쓰기 트랜잭션이 10회 이상 발생하는 경우.
   - `Database Locked`로 인한 서비스 일시 실패가 주 3회 이상 시스템 저널 로그에 감지되는 경우.
3. **이주 방법 요약**:
   - PostgreSQL 데몬 설치 및 데이터베이스 생성.
   - `.env`에 `DATABASE_URL=postgresql://user:password@localhost:5432/jissou_db` 연결 문자열 구성. (SQLAlchemy가 이주 설계를 통해 `with_for_update()` canonical row-lock을 자동으로 가동하여 교착 상태가 예방된 안전한 동시 처리를 수행합니다.)

---

## 트러블슈팅

### 서비스가 시작되지 않을 때
```bash
journalctl -u jissou-park --no-pager -n 50
```

### DB 파일 권한 문제
```bash
sudo chown pi:pi /opt/jissou-park/instance/game.db
chmod 664 /opt/jissou-park/instance/game.db
```

### 포트 충돌
```bash
sudo lsof -i :8000
sudo lsof -i :80
```

---

## 안드로이드 APK 빌드 (추후 개발)

> **상태**: Phase 9 — 추후 개발 예정

### 빌드 방식: Kivy/BeeWare (Python 네이티브)

```
[재사용 대상 — 변경 없이 이식]
  game_engine.py    (1200줄) → 행동/턴/자원 로직
  battle_engine.py  (240줄)  → 전투 시뮬레이션
  npc_engine.py     (140줄)  → NPC AI 5종
  dialogues.py      (620줄)  → 대사 시스템
  config.py         (240줄)  → 밸런스 상수
  models.py         (340줄)  → SQLAlchemy ORM (SQLite)
  lang/*.json       (258키×5) → 다국어

[재작성 대상]
  UI 계층           → Kivy 위젯 (레트로 터미널 감성)
  인증 계층         → 제거 (로컬 싱글 프로필)
  교역/외교         → NPC 자동화

[도구]
  Buildozer         → Kivy APK 빌드 자동화
  python-for-android → Android용 Python 패키징
```

### 솔플 전환 변경점

| 현재 (웹 멀티) | APK (솔플) |
|---------------|-----------|
| Flask 라우트 기반 | Kivy Screen 기반 |
| User 인증 (로그인/가입) | 로컬 프로필 (자동 시작) |
| 교역 (플레이어 간) | NPC 자동교역 |
| 외교 (동맹/적대 요청) | NPC 자동외교 |
| 랭킹 (플레이어 포함) | NPC끼리 랭킹 |
| APScheduler (서버 턴) | 로컬 타이머 (온디맨드) |
| 브라우저 UI | Kivy 네이티브 UI |

### 예상 스펙

| 항목 | 값 |
|------|-------------|
| APK 크기 | ~30~50MB (Python 런타임 포함) |
| 최소 Android | 5.0 (API 21) |
| 스토어 | Google Play (무료) |
| 타겟 | 일본/중국/한국 실장석 팬층 |
| 개발 기간 | 1~2주 (UI 재작성) |


## 수동 품질 게이트 및 자가 진단 운영 지침 (CI 부재 보완)

본 프로젝트는 경량형 환경 및 로컬 실행의 이점을 극대화하기 위해 원격 CI/CD 파이프라인을 의도적으로 적용하지 않고, **강력한 수동 품질 게이트(Manual Quality Gate) 및 자가 진단 절차**를 운영 표준으로 삼습니다. 모든 코드를 원격 저장소(`master` 브랜치)에 머지 또는 푸시하기 전, 개발자는 아래의 프로세스를 수동으로 집행하고 검증을 완수해야 합니다.

### 1. 수동 검증 프로세스 및 명령 목록

개발자는 변경 사항을 원격 master 저장소에 반영하기 직전, 아래 명령 스위트를 clean 터미널 환경에서 반드시 순차적으로 실행하여 모두 성공(`exit 0`)해야 합니다.

| 단계 | 수행 명령 | 목적 및 검증 대상 |
|---|---|---|
| **1. 단위 및 회귀 테스트** | `venv/bin/python -m pytest -q -W error` | pytest 테스트 전원 그린 패스 및 경고의 에러 격상 검증 |
| **2. 화이트스페이스 검사** | `git diff --check` | 작업 트리 상의 불필요한 공백문자 및 빈 라인 누출 차단 |
| **3. 캐시 공백 검사** | `git diff --cached --check` | index(Staged)에 등록된 커밋 대상 파일의 공백 검증 |
| **4. 문법 정적 분석** | `venv/bin/python -m py_compile app/*.py run.py tests/*.py` | 파이썬 소스 코드의 AST 문법 정합성 분석 |

### 2. 운영 책임자 및 실행 주기

- **운영 책임 총괄**: Project Lead Architect / Eunho Lim (이은호)
- **실행 주기**:
  - **매 커밋(Commit) 전**: `git diff --check` 및 `git diff --cached --check`를 상시 실행하여 형상 관리 규격을 유지합니다.
  - **매 원격 푸시(Push) 및 이주(Migration) 전**: `venv/bin/python -m pytest -q -W error`를 필수 가동하여 모든 비즈니스 로직 및 동시성 락, XSS 보안 회귀 테스트 통과를 강제합니다.
  - **정기 품질 감사**: 2주 단위로 프로젝트 총괄 책임자의 검토 하에 전체 로컬 수동 품질 게이트를 일괄 점검 및 아카이빙합니다.

