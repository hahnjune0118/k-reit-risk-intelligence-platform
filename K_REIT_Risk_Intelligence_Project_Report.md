# K-REIT Risk Intelligence Platform 개발 중간점검 보고서

> 삼일회계법인 Digital 전형 자기소개서·면접·Notion·GitHub 설명용 정리본  
> 프로젝트 성격: 공시자료·거시경제·시장가격·부동산 자산 데이터를 연결한 상장리츠 조기위험 식별 플랫폼

---

## 1. 프로젝트 한 줄 요약

**K-REIT Risk Intelligence Platform**은 상장리츠의 DART 공시, 리츠 투자보고서, ECOS 거시경제 지표, KRX 시장가격, 한국부동산원/공시가격 데이터를 연결하여 금리·cap rate·차입만기·임대위험·보유세 부담이 리츠의 **NAV, FFO, 배당여력, 시가총액, 감사위험, 세무위험, Deals 의사결정**에 어떻게 전이되는지 분석하는 Streamlit 기반 리스크 인텔리전스 플랫폼이다.

핵심 차별점은 단순히 공시자료를 보여주는 것이 아니라, **공시자료가 의미하는 위험을 사용자별 관점에서 해석한다는 점**이다.

---

## 2. 프로젝트의 출발점과 방향 전환

### 2.1 초기 아이디어: 개별 상업용 부동산 임차인/임대료 분석

초기 프로젝트는 개별 상업용 부동산의 임차인, 추정 임대료, 시장 임대료 benchmark, 차입 구조를 활용해 다음을 분석하는 방향이었다.

- 임차인별 임대료 premium/discount
- 자산별 NOI 추정
- market benchmark 대비 임대료 괴리
- DSCR, LTV, refinancing risk
- 자산별 수익성과 위험도

이 방향은 상업용 부동산 DD와 valuation 관점에서 직관적이었지만, 실제 구현 과정에서 중요한 한계가 확인되었다.

### 2.2 확인된 한계

개별 상업용 부동산 임차인과 실제 임대료 정보를 신뢰성 있게 수집하기 어려웠다. 공개 데이터는 제한적이었고, OpenUp 등 외부 자료도 대략적 추정치에 가까워 회계법인 면접이나 포트폴리오에서 설명하기에는 검증가능성이 부족했다.

특히 다음 문제가 있었다.

- 임차인별 실제 임대료 데이터 부족
- 자산별 NOI 산정의 불확실성
- 수동 추출에 따른 재현성 저하
- 데이터 출처의 감사가능성 부족
- 상업용 부동산 실거래/임대차 데이터의 공개 범위 제한

따라서 프로젝트의 방향을 **개별 비상장 부동산 추정 모델**에서 **상장리츠 공시 기반 분석 모델**로 전환했다.

### 2.3 수정된 방향: Disclosure-Based K-REIT Risk Intelligence Platform

상장리츠는 다음 데이터가 상대적으로 공개되어 있다.

- DART 사업보고서 및 분기보고서
- 리츠 투자보고서
- Annual Report / IR 자료
- 자산별 평가액, 임대율, WALE, cap rate 정보
- 차입금 만기 및 금리 정보
- KRX 주가 및 시가총액
- ECOS 기준금리, 국고채, 회사채 금리
- 한국부동산원/공시가격 데이터

따라서 프로젝트는 다음 질문에 답하는 방향으로 발전했다.

> 거시경제 변화가 상장리츠의 자산가치, 현금흐름, 배당여력, 시장가격, 감사위험, 세무위험, Deals 의사결정에 어떤 경로로 전이되는가?

---

## 3. 기존 리츠정보시스템과의 차별점

국토교통부 리츠정보시스템, DART, ECOS, KRX, 한국부동산원 API는 각각 중요한 원천 데이터를 제공한다. 그러나 이들은 주로 **정보 조회 시스템** 또는 **원천 데이터 제공 시스템**에 가깝다.

이 프로젝트가 제공하고자 하는 가치는 다음과 같다.

| 구분 | 기존 시스템 | 본 프로젝트 |
|---|---|---|
| 목적 | 공시·통계·가격 데이터 조회 | 데이터 간 연결과 위험 해석 |
| 데이터 단위 | 문서, 통계표, 종목별 정보 | 리츠별 통합 분석 단위 |
| 사용자 행동 | 사용자가 직접 읽고 판단 | 앱이 위험 경로와 점검 포인트 제시 |
| 핵심 가치 | 접근성 | 의사결정 가능성 |
| 결과물 | 원천 자료 | 감사위험, 세무위험, 가치평가, 자문 포인트 |

정리하면 다음과 같다.

> 리츠정보시스템이 “데이터 도서관”이라면, 이 프로젝트는 “리츠 리스크 해석 엔진”이다.

---

## 4. 개발 과정에서 발생한 주요 오류와 해결 방법

### 4.1 `NameError: rate_shock_bp is not defined`

#### 발생 상황

v2 단계에서 금리 충격 시나리오를 계산하는 과정에서 다음 오류가 발생했다.

```python
NameError: name 'rate_shock_bp' is not defined
```

#### 원인

Streamlit sidebar slider에서 `rate_shock_bp` 변수를 생성하기 전에 해당 변수를 이용해 stress table을 먼저 계산하고 있었다. 즉, 코드 실행 순서가 꼬여 있었다.

#### 해결 방법

- `rate_shock_bp`, `refinancing_share_pct`, `ffo_haircut_pct`, `cap_rate_shock_bp` 등 사용자 입력 slider를 먼저 선언
- 그 이후에 `build_custom_stress_table()`과 scenario 계산 함수 실행
- Streamlit의 top-down 실행 구조에 맞게 코드 순서 재배치

#### 배운 점

Streamlit은 일반 웹 프레임워크처럼 이벤트 기반이 아니라, 입력값 변경 시 스크립트 전체를 위에서 아래로 다시 실행한다. 따라서 **변수 선언 순서와 sidebar 입력값 생성 위치**가 매우 중요하다.

---

### 4.2 `StreamlitDuplicateElementId`

#### 발생 상황

v2 수정 과정에서 slider를 여러 번 생성하면서 다음 오류가 발생했다.

```python
StreamlitDuplicateElementId
```

#### 원인

동일한 label 또는 동일한 내부 element id를 가진 Streamlit widget이 중복 생성되었다. 특히 같은 이름의 slider가 sidebar와 본문 또는 중복 코드 블록에서 반복 생성되면서 문제가 발생했다.

#### 해결 방법

- 중복 slider 제거
- 각 widget에 명시적 `key` 부여

예시:

```python
st.slider("Interest-rate shock", 0, 400, 100, key="onepage_rate_shock_bp")
```

#### 배운 점

Streamlit에서 widget은 label만으로도 id가 생성될 수 있으므로, 동일한 유형의 widget을 여러 곳에서 사용할 경우 **고유 key를 명시하는 것이 안전하다.**

---

### 4.3 `TypeError: positive() got an unexpected keyword argument 'upper'`

#### 발생 상황

v3의 risk score decomposition 계산 과정에서 다음 오류가 발생했다.

```python
TypeError: positive() got an unexpected keyword argument 'upper'
```

#### 원인

scalar 또는 Series 처리 과정에서 `.clip(upper=100)`을 부적절하게 사용했다. `sum()` 이후 scalar가 된 값에 pandas Series 방식의 clip을 적용하면서 오류가 발생했다.

#### 해결 방법

다음 방식으로 scalar 값을 명확히 처리했다.

```python
score = min(float(raw_score), 100.0)
```

#### 배운 점

pandas Series, numpy scalar, Python float는 비슷해 보여도 메서드 적용 방식이 다르다. risk score처럼 최종적으로 단일 숫자를 출력하는 값은 **명시적으로 float 변환 후 min/max 처리**하는 것이 안정적이다.

---

### 4.4 ECOS API 인증키 입력이 반영되지 않는 문제

#### 발생 상황

v6에서 ECOS API 인증키를 sidebar text input에 입력하고 Enter를 눌러도 API 연결이 되지 않는 문제가 있었다.

#### 원인

Streamlit `text_input`은 Enter만으로 값이 확정되지 않는 경우가 있다. 특히 한글 IME, 브라우저, PowerShell 실행 환경에서는 사용자가 입력했다고 생각해도 session_state에 안정적으로 반영되지 않을 수 있다.

#### 해결 방법

- ECOS 인증키 입력창을 `st.form()` 구조로 변경
- `ECOS 지표 불러오기` 버튼을 추가
- 버튼 클릭 시 `st.session_state`에 API key 저장
- API key가 없으면 fallback 예시값으로 실행되도록 처리

#### 배운 점

API 인증키처럼 명시적으로 적용되어야 하는 입력값은 단순 text input보다 **form + submit button 구조**가 사용자 경험과 안정성 측면에서 적합하다.

---

### 4.5 `NameError: name 'os' is not defined`

#### 발생 상황

ECOS API key를 환경변수에서도 불러오도록 구현한 후 다음 오류가 발생했다.

```python
NameError: name 'os' is not defined
```

#### 원인

`os.getenv("ECOS_API_KEY", "")`를 사용했지만, 파일 상단에 `import os`가 누락되어 있었다.

#### 해결 방법

import 영역에 다음을 추가했다.

```python
import os
```

#### 배운 점

작은 import 누락도 전체 앱 실행을 막을 수 있다. API key, 환경변수, 파일 경로 등 OS 관련 기능을 사용할 때는 import dependency를 반드시 확인해야 한다.

---

### 4.6 `requests` 패키지 누락 문제

#### 발생 상황

ECOS, DART, KRX 등 외부 API 연결 기능을 추가하면서 사용자의 로컬 환경에 `requests` 패키지가 설치되어 있지 않으면 API 호출이 불가능했다.

#### 해결 방법

`requirements.txt`에 다음을 추가했다.

```text
requests
```

설치 명령어는 다음과 같이 안내했다.

```powershell
py -m pip install -r requirements.txt
```

#### 배운 점

API 기반 프로젝트는 코드뿐 아니라 **requirements.txt와 실행환경 재현성**이 중요하다. GitHub 제출용 프로젝트에서는 반드시 의존성 파일을 포함해야 한다.

---

### 4.7 KRX API endpoint 및 승인 상태 불확실성

#### 발생 상황

KRX API 인증키를 확보했더라도 실제 endpoint, 활용승인 상태, 응답 schema가 사용자별로 다를 수 있었다.

#### 원인

KRX Open API는 서비스별 활용신청 및 endpoint 구조가 다를 수 있고, 인증키만으로 모든 서비스가 즉시 호출되는 것은 아닐 수 있다.

#### 해결 방법

v9에서 KRX API 직접 연결 외에 CSV fallback 업로드 기능을 추가했다.

- KRX API key 입력
- KRX endpoint 입력
- 종목코드 입력
- API 호출 실패 시 CSV 업로드 가능
- CSV로도 주가, 시가총액, P/NAV, NAV 할인율 분석 가능

#### 배운 점

외부 API는 인증·승인·schema·장애 가능성이 있으므로, 실무형 앱에서는 항상 **API fallback path**가 필요하다.

---

### 4.8 기준금리 변화율 표시의 혼란

#### 발생 상황

ECOS 시계열 기반으로 기준금리 변화를 계산하면서 소수점이 많은 숫자가 표시되었다.

예시:

```text
기준금리 변화률: 0.273849%
```

#### 문제점

기준금리는 일반적으로 수익률처럼 “변화율”로 해석하기보다 **변화폭(bp)** 으로 해석해야 한다. 특히 한국은행 기준금리는 통상 25bp 단위로 조정되는 경우가 많기 때문에, 소수점이 많은 변화율 표시는 사용자에게 혼란을 준다.

#### 해결 방법

v10에서 표시 방식을 다음과 같이 수정했다.

```text
기준금리 수준: 2.50%
기준금리 변화폭: +25bp / -25bp
```

정책금리는 25bp 단위로 반올림 표시하고, 국고채·회사채 등 시장금리는 소수점 표시를 유지했다.

#### 배운 점

금융 데이터는 숫자를 가져오는 것보다 **사용자가 어떤 단위와 개념으로 해석해야 하는지 설계하는 것**이 더 중요하다.

---

## 5. 버전별 프로젝트 발전 과정

### v1: 기본 REIT Risk Screener

초기 버전은 SK리츠 데이터를 기반으로 다음 기능을 제공했다.

- 리츠 개요
- 포트폴리오 및 임대위험
- 차입금 만기와 refinancing pressure
- FFO, NAV, leverage 등 핵심 KPI
- source & data model 설명

이 단계에서는 아직 기능이 탭별로 분리되어 있었고, 분석보다는 대시보드 형태에 가까웠다.

---

### v2: Management Watchlist 및 DD 질문 추가

v2에서는 단순 지표 나열에서 벗어나, 실무자가 던질 수 있는 질문을 추가했다.

- Management Watchlist
- DD question bank
- tenant exposure
- asset concentration
- source confidence summary

이 단계에서 프로젝트가 단순 모니터링 도구에서 **실사 질문 생성 도구**로 확장되기 시작했다.

---

### v3: Risk Score Decomposition

v3에서는 리츠 레벨과 자산 레벨의 위험 점수를 분해하는 기능을 추가했다.

- REIT-level risk score
- asset-level risk score
- risk contribution by category

이 단계에서 “어떤 항목 때문에 위험한가?”를 설명할 수 있게 되었다.

---

### v4: Interactive Scenario Simulator

v4에서는 사용자가 시나리오를 직접 조정할 수 있게 했다.

- 금리 충격
- 차환 대상 부채 비중
- FFO operating downside
- cap rate expansion
- stressed FFO
- stressed ICR
- stressed NAV impact
- stressed LTV proxy

이 단계에서 프로젝트는 정적인 대시보드가 아니라 **시나리오 기반 분석 도구**가 되었다.

---

### v5: One-page Consulting View

v5에서는 6개 탭으로 흩어진 정보를 하나의 consulting-style one-page dashboard로 재구성했다.

- stress scenario는 sidebar로 이동
- 본문은 executive summary 중심으로 정리
- 차트와 표 크기 축소
- 부수 정보 제거
- source/data model은 하단 expander로 이동

이 단계에서 앱은 면접과 포트폴리오에서 설명하기 좋은 형태로 정리되었다.

---

### v6: ECOS 기반 Macro Scenario 추가

v6에서는 금리 충격을 사용자가 임의로 조정하는 방식에서 벗어나, ECOS API를 활용한 거시경제 기반 시나리오 구조를 추가했다.

- ECOS API key 입력
- 기준금리, 국고채 3년, 회사채 AA- 3년 등 금리 지표 연결
- 호황 / 중립 / 불황 시나리오
- macro-based interest rate shock
- macro-based cap rate stress

이 단계에서 프로젝트는 **공식 거시경제 지표와 리츠 리스크를 연결**하기 시작했다.

---

### v7: DART API 및 5년 시계열 분석 추가

v7에서는 DART API 입력칸과 최근 5년 재무제표 자동 수집 구조를 추가했다.

- DART API key 입력
- SK리츠 최근 5년 재무제표 수집
- 총자산, 총부채, 자본, 투자부동산, 영업수익, 영업이익, 순이익 등 수집
- DART 재무제표와 리츠 투자보고서 KPI 구분
- 5년 금리·NAV/자본·FFO/이익 흐름 시각화

이 단계에서 프로젝트는 **단일 시점 분석에서 5년 시계열 분석**으로 발전했다.

---

### v8: 사용자 모드 및 KRX API 추가

v8에서는 사용자 모드를 추가하고 KRX API 입력 구조를 만들었다.

초기 사용자 모드는 다음과 같았다.

- 대학생
- 상장리츠 투자자
- 리츠회사
- Deals
- Assurance

또한 KRX API를 통해 다음 데이터를 연결할 수 있게 했다.

- 주가
- 거래량
- 시가총액
- P/NAV
- NAV 할인율

이 단계에서 프로젝트는 **공시 NAV와 시장가격을 연결**하기 시작했다.

---

### v9: Macro-to-REIT-to-Market Transmission Engine

v9에서는 거시경제 → 리츠 재무지표 → 시장가격 전이 구조를 명확히 했다.

- 금리 → FFO/NAV → 시가총액 전이 진단
- P/NAV 할인율 분석
- 시장이 공시 NAV를 얼마나 할인하는지 분석
- KRX CSV fallback 업로드
- 단순 민감도 참고표
- 실제 시장가격과 공시지표 간 불일치 탐지

이 단계에서 프로젝트의 핵심 질문은 다음으로 정리되었다.

> 시장은 공시 NAV를 얼마나 믿고 있으며, 그 할인은 금리·차환·배당·자산가치 위험을 얼마나 반영하는가?

---

### v10: Assurance / Tax / Deals 전문가 모드

v10에서는 회계법인 실무 관점에 맞춰 사용자 모드를 재편했다.

- Assurance
- Tax
- Deals

각 모드는 다음 목적을 가진다.

#### Assurance 모드

- 리츠회사 재무제표 감사
- 내부회계관리제도 감사
- RMM 식별
- 중점 실사 자산 선정
- KAM 후보 제안
- 계속기업 관련 중요한 불확실성 검토 신호
- 내부통제 점검 포인트 도출

#### Tax 모드

초기 v10에서는 보유세와 양도 시 세금효과를 함께 다루었으나, 이후 보유세 분석으로 범위를 좁혔다.

#### Deals 모드

- Buy-side / sell-side 관점 가치평가
- NAV 기반 valuation
- FFO 기반 valuation
- 배당수익률 기반 valuation
- KRX 역사적 시가총액과 backtesting
- 시장가격이 공시가치를 얼마나 반영했는지 검증

---

### v10.1: General Info & Scenario 분리 및 보유세 심화 분석

v10.1에서는 사용자의 요청에 따라 전문가 모드 외의 공통 정보를 별도 모드로 분리했다.

최종 사용자 모드는 다음과 같다.

- General Info & Scenario
- Assurance
- Tax
- Deals

Tax 모드는 양도세를 제거하고 보유세 분석에 집중하도록 수정했다.

추가 기능은 다음과 같다.

- 보유세 계산 공식 expander
- 과세표준 계산 기초 설명
- 토지 시가표준액 = 개별공시지가 × 토지면적
- 건물 시가표준액 입력
- 공정시장가액비율 적용
- 별도합산 토지분 재산세 계산
- 건축물분 재산세 계산
- 도시지역분, 지방교육세 계산
- 한국부동산원/공시가격 API 입력 구조
- API 실패 시 CSV fallback
- 최근 5년 공시지가/기준시가 변화에 따른 보유세 추이 분석

이 단계에서 Tax 모드는 **신고용 세액계산기**가 아니라, 리츠 보유자산별 보유세 부담 증가 위험을 조기에 파악하는 **holding tax risk module**로 재정의되었다.

---

## 6. 최종 제품의 현재 구조

현재 final product는 다음 4개 모드로 구성된다.

### 6.1 General Info & Scenario

공통 정보를 보여주는 모드다.

주요 기능:

- SK리츠 개요
- 핵심 KPI
- 거시경제 시나리오
- 금리, cap rate, FFO downside, refinancing stress
- NAV/FFO/시장가격 전이 구조
- 5년 시계열 요약
- source & data basis 설명

### 6.2 Assurance 모드

재무제표 감사 및 내부회계관리제도 감사 관점의 모드다.

주요 기능:

- 자산별 감사 우선순위
- 투자부동산 공정가치 평가위험
- cap rate 민감도
- 차입금 만기와 계속기업 검토 신호
- RMM mapping
- KAM 후보 자동 제안
- 내부회계관리제도 핵심 통제 포인트

활용 예시:

> 금리 상승에도 특정 자산의 평가액이 유지되고 있고, cap rate 민감도가 크며, 리츠 전체 NAV에서 차지하는 비중이 높다면 해당 자산은 투자부동산 공정가치 평가 관련 RMM 검토 대상이 될 수 있다.

### 6.3 Tax 모드

리츠 보유자산의 보유세 부담을 분석하는 모드다.

주요 기능:

- 한국부동산원/공시가격 API 입력
- 실제 공시가격/기준시가 기반 과세표준 산정 구조
- CSV fallback
- 별도합산 토지분 재산세 추정
- 건축물분 재산세 추정
- 도시지역분, 지방교육세 반영
- 최근 5년 보유세 증가 추이
- 자산별 보유세 부담 ranking

활용 예시:

> 특정 오피스 자산의 개별공시지가가 최근 5년간 빠르게 상승했다면, 해당 자산은 회계상 공정가치뿐 아니라 보유세 부담 증가 측면에서도 FFO와 배당여력에 영향을 줄 수 있다.

### 6.4 Deals 모드

리츠회사 buy-side / sell-side 관점의 가치평가 및 시장가격 검증 모드다.

주요 기능:

- NAV 기반 가치평가
- FFO 기반 가치평가
- 배당수익률 기반 가치평가
- KRX 실제 시가총액과 모델 추정가치 비교
- P/NAV discount 분석
- buy-side / sell-side 해석 문장

활용 예시:

> 공시 NAV 대비 시가총액이 큰 폭으로 할인되어 있지만 FFO가 안정적이고 배당여력이 유지된다면 buy-side 관점에서는 저평가 기회일 수 있다. 반대로 차환위험과 cap rate 민감도가 큰 경우에는 단순 저평가가 아니라 risk premium으로 해석해야 한다.

---

## 7. 데이터 구조 및 API 설계

### 7.1 주요 데이터 소스

| 데이터 소스 | 역할 |
|---|---|
| DART API | 재무제표, 사업보고서, 손익/재무상태 데이터 |
| ECOS API | 기준금리, 국고채, 회사채 등 거시경제 지표 |
| KRX API | 주가, 거래량, 시가총액, 시장가격 |
| 리츠 투자보고서 | FFO, NAV, WALE, 임대율, 자산별 KPI |
| Annual Report / IR | 포트폴리오 설명, 자산별 cap rate, 차입구조 |
| 한국부동산원/공시가격 API | 개별공시지가, 공시가격, 기준시가 기반 보유세 분석 |
| CSV fallback | API 실패 또는 승인 지연 시 재현성 확보 |

### 7.2 데이터 신뢰도 구분

앱에서는 숫자를 다음과 같이 구분하는 방향으로 설계했다.

- 공시값: DART, 투자보고서, Annual Report 등에서 직접 추출
- API값: ECOS, KRX, 한국부동산원 API에서 수집
- 추정값: 앱 내부 계산식으로 산정
- proxy값: 직접 값이 없을 때 대체 지표로 계산

이 구분은 회계법인 면접에서 중요하다. 단순히 모델을 만들었다는 것보다, **데이터 basis를 구분하고 신뢰도를 관리했다는 점**이 Digital 전형에서 더 강한 메시지가 될 수 있다.

---

## 8. 핵심 분석 로직

### 8.1 NAV 전이 구조

```text
부동산 가치 ≈ NOI / Cap rate
NAV ≈ 부동산 가치 + 기타자산 - 부채
```

금리 상승은 cap rate 상승으로 이어질 수 있고, cap rate가 상승하면 동일한 NOI에서 부동산 가치가 하락한다. 이는 NAV 감소와 LTV 상승으로 연결된다.

### 8.2 FFO 전이 구조

```text
시나리오 후 FFO ≈ 현재 FFO - 영업 하락분 - 추가 이자비용 - 보유세 증가 부담
```

차입금리가 상승하면 이자비용이 증가하고, 보유세가 증가하면 임대수익이 안정적이어도 배당가능 현금흐름이 압박될 수 있다.

### 8.3 시장가격 전이 구조

```text
P/NAV = 시가총액 / NAV
NAV discount = 1 - P/NAV
```

공시 NAV가 유지되더라도 시가총액이 하락하면 시장은 공시 NAV에 discount를 적용하고 있는 것이다. 이 discount가 금리, 차환위험, cap rate, 배당여력, 자산가치 우려 중 무엇에 기인하는지 해석하는 것이 Deals 모드의 핵심이다.

### 8.4 Assurance RMM 구조

Assurance 모드는 다음 위험을 계정과 감사절차로 연결한다.

| 위험 신호 | 관련 계정/공시 | 감사상 고려사항 |
|---|---|---|
| cap rate 상승 | 투자부동산 | 공정가치 과대평가 위험 |
| 차입금 만기 집중 | 차입금, 계속기업 | 유동성 및 차환위험 |
| FFO 감소 | 배당, 현금흐름 | 배당 지속가능성 검토 |
| 임차인 집중 | 임대수익, 채권 | 수익 지속가능성 및 회수가능성 |
| 특수관계자 거래 | 주석 공시 | 거래조건 공정성 및 공시 충분성 |
| 보유세 증가 | 판매관리비/세금과공과 | 비용 완전성 및 예측 가능성 |

### 8.5 Tax 보유세 구조

Tax 모드는 다음 구조를 사용한다.

```text
토지 시가표준액 = 개별공시지가 × 토지면적
토지 과세표준 = 토지 시가표준액 × 공정시장가액비율
건물 과세표준 = 건물 시가표준액 × 공정시장가액비율
보유세 = 재산세 본세 + 도시지역분 + 지방교육세
```

이 구조를 통해 공시지가 상승이 리츠의 보유세 부담과 FFO에 미치는 영향을 분석한다.

---

## 9. 삼일회계법인 Digital 전형에서 강조할 포인트

### 9.1 문제정의 능력

초기 아이디어는 개별 상업용 부동산 임대료 분석이었지만, 데이터 신뢰도와 재현성의 한계를 발견하고 상장리츠 공시 기반 분석으로 방향을 전환했다.

면접에서 다음처럼 설명할 수 있다.

> 처음에는 개별 상업용 부동산의 임차인과 임대료를 추정하는 모델을 만들었지만, 공개 데이터의 한계로 인해 분석의 검증가능성이 낮다고 판단했습니다. 그래서 공시자료, DART, ECOS, KRX, 리츠 투자보고서처럼 출처가 명확한 데이터를 활용할 수 있는 상장리츠 분석으로 방향을 전환했습니다.

### 9.2 Digital 역량

다음 역량을 보여줄 수 있다.

- Streamlit 기반 interactive dashboard 구축
- API 연동 구조 설계
- DART, ECOS, KRX, 한국부동산원 데이터 통합
- CSV fallback 설계
- 시나리오 분석 엔진 구현
- 사용자 모드별 UI 분리
- 데이터 source/basis 관리
- 공시자료 기반 risk intelligence 설계

### 9.3 Assurance와 Digital의 연결

Assurance 모드는 재무제표 감사와 내부회계관리제도 감사에서 사용할 수 있는 risk assessment prototype이다.

강조할 수 있는 부분:

- 투자부동산 공정가치 평가위험 식별
- cap rate 민감도 기반 자산 우선순위 선정
- 차입금 만기 집중과 계속기업 검토 신호 탐지
- KAM 후보 자동 제안
- 내부통제 점검 포인트 제시

### 9.4 Deals와 Digital의 연결

Deals 모드는 단순 valuation 계산기가 아니라 시장가격과 공시가치의 괴리를 분석한다.

강조할 수 있는 부분:

- NAV 기반 valuation
- FFO 기반 valuation
- KRX 시가총액 backtesting
- 시장의 NAV discount 해석
- buy-side / sell-side별 자문 포인트 도출

### 9.5 Tax와 Digital의 연결

Tax 모드는 리츠 보유자산별 보유세 부담을 공시가격/기준시가 기반으로 분석한다.

강조할 수 있는 부분:

- 보유세 부담이 FFO와 배당여력에 미치는 영향
- 개별공시지가 상승에 따른 5년 보유세 증가 추이
- 한국부동산원/공시가격 API 활용 구조
- 자산별 tax burden ranking

---

## 10. GitHub README 구성 제안

GitHub에는 다음 구조로 올리는 것이 좋다.

```text
reits_analysis_app/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   ├── sk_reit_latest_kpis.csv
│   ├── sk_reit_asset_metrics.csv
│   ├── sk_reit_debt_schedule_20260331.csv
│   ├── sk_reit_parent_direct_assets_20260331.csv
│   └── sk_reit_data_dictionary.csv
├── docs/
│   ├── project_report.md
│   ├── screenshots/
│   └── data_dictionary.md
└── examples/
    ├── krx_price_sample.csv
    └── holding_tax_sample.csv
```

README에는 다음을 포함하는 것이 좋다.

1. Project Overview
2. Problem Statement
3. Why REITs?
4. Key Features
5. User Modes
6. Data Sources
7. Methodology
8. Screenshots
9. How to Run
10. Limitations
11. Future Roadmap

---

## 11. Notion 페이지 구성 제안

Notion에는 GitHub보다 더 설명형으로 구성하는 것이 좋다.

추천 구조:

```text
1. 프로젝트 요약
2. 문제의식: 기존 리츠정보시스템과의 차이
3. 개발 과정: 아이디어 전환
4. 버전별 발전 과정
5. 현재 제품 구조
6. 사용자 모드별 기능
7. 오류 해결 및 개발 중 배운 점
8. 삼일회계법인 Digital 직무와의 연결
9. 데모 화면 캡처
10. 향후 개선 로드맵
```

Notion에서는 코드를 길게 붙이는 것보다, 화면 캡처와 해석 문장을 많이 넣는 것이 좋다.

---

## 12. 향후 개발 로드맵

### Phase 1: SK리츠 고도화

현재 진행 중인 단계다.

목표:

- SK리츠 단일 케이스 완성
- Assurance / Tax / Deals 모드 안정화
- ECOS, DART, KRX, 한국부동산원 API 연결 안정화
- 5년 시계열과 backtesting 강화

### Phase 2: 상장리츠 전체 확장

목표:

- 롯데리츠, 신한알파리츠, ESR켄달스퀘어리츠 등 peer comparison
- P/NAV, FFO payout, leverage, WALE, 차입만기 비교
- 상장리츠 risk ranking

### Phase 3: 지역별·자산군별 분석

목표:

- CBD, GBD, YBD, 판교, 물류권역별 exposure 분석
- 오피스, 물류, 리테일, 호텔 등 자산군별 변화 분석
- 기관투자자형 상업용 부동산 자본흐름 map 구축

### Phase 4: 공시 텍스트 기반 조기경보

목표:

- DART 및 투자보고서 텍스트에서 위험 키워드 탐지
- 차입금, 임차인, 감정평가, 특수관계자, 계속기업 문구 분석
- Assurance/Deals risk flag 자동 생성

### Phase 5: 면접 및 포트폴리오 정리

목표:

- README 정리
- Notion page 구성
- demo screenshot 정리
- 자기소개서용 project narrative 작성
- GitHub 공개용 코드 정리

---

## 13. 면접용 60초 설명 스크립트

> 이 프로젝트는 상장리츠의 공시자료, 거시경제 지표, 시장가격, 자산별 정보를 연결하여 리츠의 조기위험을 식별하는 Streamlit 기반 분석 플랫폼입니다.  
> 처음에는 개별 상업용 부동산의 임대료와 NOI를 추정하는 모델로 시작했지만, 공개 데이터의 신뢰성과 재현성에 한계를 느꼈고, DART, 리츠 투자보고서, ECOS, KRX처럼 출처가 명확한 상장리츠 데이터로 분석 대상을 전환했습니다.  
> 현재 앱은 General Info & Scenario, Assurance, Tax, Deals 모드로 구성되어 있습니다. Assurance 모드에서는 투자부동산 공정가치, 차입금 만기, 계속기업, KAM 후보 등 감사위험을 식별하고, Tax 모드에서는 공시가격과 기준시가 기반으로 보유세 부담 변화를 분석합니다. Deals 모드에서는 NAV, FFO, 배당수익률 기반 가치평가와 실제 KRX 시가총액을 비교해 시장이 공시가치를 얼마나 할인하고 있는지 검증합니다.  
> 단순한 공시 조회가 아니라, 공시 데이터가 어떤 리스크로 전이되는지 해석하고 사용자별 의사결정 포인트를 제시한다는 점에서 Digital Assurance와 Deals 업무에 연결될 수 있는 프로젝트라고 생각합니다.

---

## 14. 자기소개서용 핵심 문장

### 문장 1

저는 상장리츠의 공시자료, 거시경제 지표, 시장가격 데이터를 연결하여 리츠의 재무위험과 감사위험을 조기에 식별하는 Streamlit 기반 분석 플랫폼을 개발했습니다.

### 문장 2

초기에는 개별 상업용 부동산의 임대료와 NOI를 추정하는 모델을 구상했지만, 데이터 신뢰성과 재현성의 한계를 확인하고 DART, ECOS, KRX, 리츠 투자보고서 등 공식 데이터 기반의 상장리츠 분석 모델로 방향을 전환했습니다.

### 문장 3

이 과정에서 단순한 데이터 시각화가 아니라, 금리와 cap rate 변화가 NAV, FFO, 배당여력, 시가총액, 감사위험으로 전이되는 경로를 구조화하고 사용자별로 다른 의사결정 포인트를 제시하는 데 집중했습니다.

### 문장 4

특히 Assurance 모드에서는 투자부동산 공정가치 평가위험, 차입금 만기와 계속기업 검토 신호, KAM 후보, 내부회계관리제도 통제 포인트를 자동으로 정리하도록 설계했습니다.

### 문장 5

이 프로젝트를 통해 회계·부동산·금융 데이터에 대한 이해를 바탕으로 문제를 정의하고, API와 대시보드를 활용해 실무형 digital solution으로 구현하는 경험을 쌓았습니다.

---

## 15. 프로젝트의 현재 한계

현재 버전은 prototype이므로 다음 한계가 있다.

- SK리츠 단일 케이스 중심
- DART 재무제표와 리츠 투자보고서 KPI 간 basis 차이 존재
- FFO, NAV, WALE 등은 DART API만으로 완전히 자동 추출되기 어려움
- KRX API endpoint는 사용자 승인 상태에 따라 달라질 수 있음
- 한국부동산원/공시가격 API는 실제 endpoint와 파라미터가 서비스별로 다를 수 있음
- Tax 모드는 신고용 계산기가 아니라 preliminary risk estimator임
- Deals valuation은 정식 valuation opinion이 아니라 screening model임
- Assurance 모드는 감사결론을 대체하지 않고 감사계획 단계의 risk identification을 보조함

이 한계는 오히려 면접에서 장점으로 설명할 수 있다. 중요한 것은 모델이 모든 것을 완벽하게 해결한다고 주장하는 것이 아니라, **데이터의 한계와 basis를 인식하고 통제 가능한 방식으로 설계했다는 점**이다.

---

## 16. 최종 결론

이 프로젝트는 단순 리츠 대시보드가 아니라, 공시자료와 시장·거시경제 데이터를 연결해 리츠의 위험이 어디에서 발생하고 어떻게 전이되는지 분석하는 **REIT Risk Intelligence Platform**으로 발전하고 있다.

현재 제품은 다음 가치를 제공한다.

- 학생에게는 리츠 구조와 금리 민감도를 이해하는 교육 도구
- 투자자에게는 시장가격과 공시 NAV의 괴리를 해석하는 도구
- Assurance 실무자에게는 RMM, KAM, 계속기업, 내부통제 위험을 조기에 식별하는 도구
- Tax 실무자에게는 보유세 부담 증가가 FFO와 배당여력에 미치는 영향을 분석하는 도구
- Deals 실무자에게는 buy-side/sell-side valuation과 시장가격 검증을 지원하는 도구

삼일회계법인 Digital 전형에서는 이 프로젝트를 통해 **회계 지식, 부동산/리츠 산업 이해, 데이터 수집·정제, API 연동, 대시보드 구현, 실무형 문제정의 능력**을 함께 보여줄 수 있다.

