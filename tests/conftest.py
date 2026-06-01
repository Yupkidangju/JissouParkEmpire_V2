# -*- coding: utf-8 -*-
"""
실장석 공원 제국 - 회귀 테스트 설정 (conftest.py)
[v1.8.9] 회귀 테스트를 위한 Flask 및 SQLAlchemy 테스트 픽스처 구축 (audit_report_62.md [DBG-F002])
- 모든 주석은 엄격하게 한국어로만 기술됩니다.
"""
import os
# [v1.8.9] 임포트 타임 평가 전 환경변수를 강제 설정하여 실제 파일 DB 접근을 차단하고 인메모리 격리를 유지
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret-key-stable-desu'
os.environ['DEBUG'] = 'true'
os.environ['TESTING'] = 'true'

import pytest
from app import create_app
from app.models import db, Park

@pytest.fixture
def app():
    # Flask 앱 팩토리를 테스트 모드로 구동
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',  # 테스트 격리를 위해 메모리 DB 사용
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })

    with app.app_context():
        # 데이터베이스 스키마 생성 및 초기화
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db_session(app):
    with app.app_context():
        yield db.session
