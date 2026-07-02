# Codex Handoff - K-REIT Risk Intelligence Platform

현재 안정 공개 버전: **v11 - Tax & Assurance 중심 버전**

## 현재 범위

v11은 한국어 사용자를 기준으로 정리한 Tax & Assurance 중심 공개 포트폴리오 버전입니다. 활성 Streamlit 화면은 다음 네 가지입니다.

1. 일반 정보 및 시나리오
2. Assurance: 감사위험 분석
3. Tax: 보유세 분석
4. 분석 방법론 및 데이터 출처

공개 앱에서는 Deal 모드와 KRX API 런타임 의존성을 제외했습니다. 관련 코드는 향후 KRX 기반 가치평가 또는 Deal 분석 모듈을 위해 archive/roadmap 성격으로만 유지합니다.

## 실행 진입점

Streamlit 진입점은 `app.py`입니다.

```powershell
py -m streamlit run app.py
```

## 주요 파일

- `config.py`: 앱 버전, 제목, 표시 라벨, endpoint 상수
- `api_manager.py`: 안전한 API Key 로딩과 마스킹
- `ui_layout.py`: 공개 모드 선택과 첫 화면 설명
- `ui_sidebar.py`: ECOS, DART, V-World / 공시가격 API 설정
- `ui_general.py`: 일반 정보 및 Scenario 분석
- `ui_assurance.py`: 감사위험 분석 workflow
- `ui_tax.py`: 보유세 분석 workflow
- `ui_methodology.py`: 분석 방법론 및 데이터 출처

## 보안

API Key를 Streamlit widget의 `value=`에 넣거나 화면에 표시하면 안 됩니다. API Key는 `api_manager.get_api_key()`로 로드하고, 화면에 표시될 수 있는 API 응답이나 상태 문구는 `api_manager.sanitize_secret_text()`로 마스킹합니다.

## 버전 관리

중요 기능이 추가되는 경우 v12, v13처럼 순차적으로 버전을 올립니다. `VERSION`, `CHANGELOG.md`, `config.py`를 함께 맞춥니다.
