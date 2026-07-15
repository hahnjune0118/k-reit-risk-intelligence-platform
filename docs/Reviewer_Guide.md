# Reviewer Guide

## 1. 3분 리뷰 순서

1. `README.md`에서 프로젝트 목적과 현재 v14.1 범위를 확인합니다.
2. 앱을 실행하고 사이드바가 `분석 모드 → 분석 대상회사 → 시나리오 → 데이터 연결 상태` 순서로 보이는지 확인합니다.
3. 활성 모드가 일반 정보, Tax, Assurance, Methodology 네 가지인지 확인합니다.
4. 비-SK 리츠를 선택하고 `Tax: 보유세 분석`에서 Tax Summary부터 Export까지 표시되는지 확인합니다.
5. `Assurance: 감사위험 분석`에서 source/scope banner와 회사 단위 proxy 표가 선택 회사 기준으로 표시되는지 확인합니다.
6. `분석 방법론 및 데이터 출처`에서 v14.1 metric definition, source lineage, source_type taxonomy를 확인합니다.

## 2. 공개 앱에서 확인할 화면

활성 모드는 정확히 네 가지입니다.

- 일반 정보 및 시나리오
- Tax: 보유세 분석
- Assurance: 감사위험 분석
- 분석 방법론 및 데이터 출처

공개 UI에서는 다음 항목이 보이면 안 됩니다.

- Deals 모드
- KRX API 입력 또는 KRX 연결 상태
- 외부 데이터 인증값 입력 필드
- 인증값의 전체 또는 일부
- 사이드바의 공시 기준일 선택기
- 별도 종목코드 입력 필드

## 3. v14.1에서 특히 볼 부분

Tax 화면은 다음 순서로 표시됩니다.

1. 화면 제목 및 선택 회사
2. source/scope banner
3. Tax 분석 가정
4. Tax Summary
5. 보유세 추정 브리지
6. Tax Issue Matrix
7. 보유세 정합성 검토
8. FFO proxy 현금유출 스트레스
9. Tax Request List
10. Tax Review Memo Draft
11. Export Tax Review Pack
12. 데이터 검증 및 한계
13. source/raw data expanders

비-SK 리츠를 선택했을 때 정상적으로 보여야 하는 항목:

- Tax Summary
- `회사 전체 추정` / `회사 전체` fallback 행
- 보유세 추정 브리지
- Tax Issue Matrix
- 보유세 정합성 검토
- FFO proxy 현금유출 스트레스
- Issue 기반 요청자료 리스트
- Tax Review Memo 초안
- Memo, Issue Matrix, Reconciliation, Request List export
- source_type, source_note, 한국어 source label, 신뢰수준

비-SK 리츠 화면에는 SK리츠의 자산명, 임차인명, Cap rate, 차입금 만기 상세가 표시되면 안 됩니다.

## 4. Memo 확인

Tax Review Memo 초안에는 항상 다음 6개 섹션이 포함되어야 합니다.

1. 검토 대상
2. 핵심 수치 요약
3. 주요 Tax 이슈
4. 요청자료
5. 실무적 시사점
6. 제한 및 유의사항

제한 및 유의사항에는 신고 목적의 확정 세액이나 법률의견이 아니라는 문구, 원자료 확인과 세무 전문가 검토가 필요하다는 문구가 있어야 합니다. 추정 또는 sample 데이터가 사용된 경우 회사 전체 Snapshot 기반 추정값이라는 추가 문구도 표시되어야 합니다.

## 5. 데이터 해석 시 유의사항

이 앱은 예비 분석 도구입니다. 다음 결론을 직접 제공하지 않습니다.

- 감사의견
- 세무신고 목적의 확정 세액
- 투자추천
- 법률 자문
- 정식 가치평가 의견

Snapshot 또는 예시 데이터는 공개 리뷰 안정성을 위해 포함되어 있으며, 공식 확정 데이터로 과도하게 해석하지 않아야 합니다.

v14.1에서는 FFO와 NAV를 다음처럼 해석해야 합니다.

- FFO proxy: 공식 공시 FFO가 아니라 확보 가능한 공시 계정과 Snapshot을 이용한 비교 목적 proxy
- 장부기준 NAV proxy: 총자산 - 총부채 기준의 장부가액 proxy이며 시가평가 NAV가 아님
- 총자산 기준 차입비율: 이자부 차입부채 / 총자산이며 담보가치 기준 LTV가 아님. 충당부채는 분자에서 제외

## 6. 테스트

```powershell
py -m pip install -r requirements-dev.txt
py -m compileall -q . -x "(\.git|\.venv|venv|__pycache__|\.cache|\.vscode)"
py -m pytest -q
```

## 7. 주요 파일

- `app.py`: Streamlit 진입점
- `config.py`: 버전과 화면 라벨
- `data_source_policy.py`: source_type taxonomy
- `calculations_holding_tax_bridge.py`: 보유세 추정 bridge
- `tax_validation.py`: Tax 입력 검증
- `tax_request_mapping.py`: 요청자료 매핑
- `calculations_tax_review_pack.py`: Tax Review Pack 산출물 생성
- `tax_data_loader.py`: Tax Snapshot 및 fallback 데이터 로딩
- `data_availability.py`: 회사별 상세 데이터 가용성 및 fallback 범위 판정
- `red_flag_engine.py`: Red Flag 평가
- `ui_tax.py`: Tax 화면
- `ui_assurance.py`: Assurance 화면
- `ui_methodology.py`: 방법론 화면
