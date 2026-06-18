# Samsung Electronics Automated Trading System

**Financial Engineering Project — KIS Mock (Virtual) Trading Environment**

🇰🇷 한국어 보고서는 본 문서 하단의 [한국어](#한국어) 섹션을 참고하십시오.

## Abstract

This project implements an automated, polling-based trading agent for
Samsung Electronics (KRX: `005930`), built on the Korea Investment &
Securities (KIS) Open API. The system was deployed and tested against KIS's
official mock (virtual) trading environment to validate that an end-to-end
automated pipeline — market data retrieval, order submission, exchange
acceptance, fill detection, and real-time profit/loss evaluation — can
operate correctly without manual intervention. This report documents the
system design, trading methodology, and empirical results from a live test
run, along with the limitations of the current implementation.

## 1. Objective

The goal of this project is to demonstrate the construction of a working
automated trading system integrated with a real brokerage API, with the
following specific objectives:

1. Programmatically retrieve real-time market data from a brokerage REST API.
2. Programmatically submit, and have accepted, limit buy/sell orders
   compliant with exchange rules (e.g., KRX tick-size constraints).
3. Track account state (holdings, cash, sellable inventory) and detect
   order execution without manual checking.
4. Evaluate position performance (average cost, unrealized profit/loss) in
   real time.
5. Operate unattended within a defined trading window, with reasonable
   handling of network failures and exchange-side rejections.

## 2. System Architecture

The system is organized into independent modules, each responsible for one
concern:

| Module | Responsibility |
|---|---|
| `main.py` | Entry point; wires dependencies and starts the trading loop |
| `config.py` | Environment/credential loading; all tunable parameters; KIS API constants |
| `auth.py` | OAuth token issuance and same-day disk-cached reuse |
| `api_client.py` | HTTP transport layer: request headers, timeouts, retry/backoff, call throttling |
| `market_data.py` | Current price lookup |
| `account.py` | Account balance, holdings, and profit/loss lookup |
| `orders.py` | Buy/sell limit order submission, including tick-size compliance |
| `trader.py` | Trading-window control loop and execution verification logic |
| `logger.py` | Unified console + rotating file logging |

This separation allows each concern (networking, authentication, trading
logic) to be tested and modified independently, and keeps all
KIS-API-specific conventions (transaction IDs, field names) isolated in
`config.py`.

## 3. Trading Methodology

The implemented strategy is a **symmetric bracket order strategy**, used
here as a baseline to validate system mechanics rather than as an
optimized source of alpha:

On each polling cycle (default interval: 60 seconds), while within the
configured trading window (09:10–15:30):

1. Query the current market price *P* of `005930`.
2. Query current account holdings and sellable quantity.
3. Submit a limit **buy** order at `P − 1,000` KRW.
4. If sufficient sellable inventory exists, submit a limit **sell** order
   at `P + 1,000` KRW; otherwise skip the sell and log the reason.
5. After a short delay, re-query the account to check whether holdings or
   cash changed, indicating a fill.

**Limitation of this strategy.** The buy/sell offset is fixed and
independent of the position's actual average cost, and unfilled orders
from previous cycles are not cancelled before new ones are placed. This is
a deliberate simplification to validate the trading pipeline itself; it is
not presented as a profitable or risk-optimized strategy. Section 6
discusses what would be required to extend this into one.

## 4. Engineering Considerations Addressed

During testing against the live mock environment, the following
real-world constraints were identified and handled in the implementation,
which is relevant evidence that the system interacts correctly with actual
exchange-side rules rather than an idealized simulation:

- **KRX tick-size compliance.** Limit order prices must be a multiple of
  the official tick size for their price band (e.g., 500 KRW per tick in
  the 200,000–500,000 KRW range). Computed order prices are snapped to the
  nearest valid tick before submission (`orders.py`).
- **Exchange rate limiting and latency.** The mock server enforces a
  per-second call limit and exhibits higher latency on certain endpoints.
  The client throttles outgoing calls and uses a tuned timeout/retry policy
  (`api_client.py`).
- **Reserved-inventory awareness.** Total holdings (`hldg_qty`) include
  shares already reserved by the account's own unfilled sell orders. The
  system instead checks KIS's orderable-quantity field (`ord_psbl_qty`)
  before submitting a new sell order, preventing rejected orders caused by
  attempting to sell already-reserved shares.

## 5. Experimental Results

The system was run against the KIS mock-trading server on 2026-06-18
during the live trading window. Representative log evidence follows
(full log: [trading.log](trading.log)).

**5.1 Order submission and exchange acceptance.** Every order submitted by
the system was accepted by KIS and assigned a real (mock) order number:

```
13:55:04  Submitting buy order: qty=1 price=353000 stock=005930
13:55:11  buy order accepted, order_no=0000029840
13:55:11  Submitting sell order: qty=1 price=355000 stock=005930
13:55:13  sell order accepted, order_no=0000029843
```

**5.2 Order execution (fills).** Holdings were observed to change between
consecutive account snapshots, confirming that submitted orders were
actually matched on the exchange, not merely accepted:

```
13:55:04  holding_qty = 13
13:55:26  holding_qty = 14   (execution detected)
```

**5.3 Real-time position performance.** With the profit/loss fields wired
in, the system reports actual unrealized performance at every cycle,
computed by KIS from the account's real average cost basis:

```
2026-06-18 13:55:26  cash=10,000,000 KRW
                      holding_qty=14
                      avg_cost=353,753 KRW/share
                      unrealized_pnl=-3,548 KRW (-0.07%)
```

At the time of this snapshot, the position was at a small unrealized
loss of 0.07%, consistent with the market price oscillating within a
narrow band close to the position's average cost.

**5.4 Fault tolerance.** The system correctly avoided an invalid order
instead of crashing when no sellable inventory was available:

```
13:34:22  Skipping sell order: only 0 share(s) sellable, need 1.
```

## 6. Limitations and Future Work

- **No realized P&L or trade-level accounting.** Unrealized P&L is read
  directly from KIS's per-position evaluation, but the system does not
  independently log a per-trade ledger (entry price, exit price, holding
  duration) or compute aggregate realized returns.
- **No risk-adjusted performance metrics.** Metrics such as Sharpe ratio,
  maximum drawdown, or win rate are not computed; only point-in-time
  unrealized P&L is available.
- **No cost-aware order logic.** Sell prices are derived from the current
  market price rather than the position's average cost, so a fill is not
  guaranteed to be profitable.
- **No order lifecycle management.** Unfilled orders from previous cycles
  are never cancelled, so resting orders accumulate over the session.
- **No position sizing or stop-loss controls.** Order quantity is fixed at
  1 share regardless of account size or unrealized loss.

These would be the natural next steps to evolve this from a systems
validation exercise into a strategy evaluation.

## 7. Conclusion

The experimental results confirm that the implemented system correctly
performs the full automated trading cycle against a live brokerage test
environment: it retrieves real market data, submits exchange-compliant
orders that are accepted and filled, detects executions, tolerates
real-world error conditions (rate limits, inventory constraints) without
crashing, and reports real-time position performance computed from the
exchange's own account data. This validates the engineering objective of
the project. It should be read as a demonstration of a functioning
trading-system pipeline, not as evidence of a profitable trading strategy.

---

## Appendix A: Setup and Reproduction

Requires Python 3.9+.

```powershell
cd samsung_auto_trader
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Required environment variables

| Variable | Meaning |
|---|---|
| `GH_ACCOUNT` | Mock account number (`12345678-01`, `1234567801`, or `12345678`) |
| `GH_APPKEY` | KIS mock-trading app key |
| `GH_APPSECRET` | KIS mock-trading app secret |

Copy `.env.example` to `.env` and fill in real values, or set the variables
as OS environment variables (`$env:GH_ACCOUNT = "..."`, etc.). `.env` is
gitignored and never committed.

### Running

```powershell
python main.py
```

The agent waits for the trading window to open if launched early, and
exits immediately without trading if launched after 15:30. Press `Ctrl+C`
to stop at any time. Logs are written to console and `trading.log`.

## Appendix B: Project Structure

```
samsung_auto_trader/
    main.py            entry point
    config.py          configuration, constants, KIS tr_id/field names
    logger.py           logging setup
    auth.py              token issuance and caching
    api_client.py        HTTP transport layer
    market_data.py       current price lookup
    account.py            balance / holdings / P&L lookup
    orders.py              order submission
    trader.py               trading loop and execution logic
    .env                     credentials (gitignored, user-created)
    .env.example              credential template
    token_cache.json        runtime-generated (gitignored)
    trading.log               runtime-generated (gitignored)
    requirements.txt
    README.md
```

## Appendix C: Notes on KIS API Field Verification

Transaction IDs (`TR_ID_*` in `config.py`) were verified against the
official `koreainvestment/open-trading-api` repository's example scripts.
A small number of balance-response field names (`hldg_qty`, `pdno`,
`dnca_tot_amt`, `ord_psbl_qty`, `pchs_avg_pric`, `evlu_pfls_amt`,
`evlu_pfls_rt`) follow KIS's published specification but were validated
empirically against live responses during testing rather than against a
local copy of the documentation; they are isolated as named constants in
`config.py` for easy correction if KIS revises them.

## Safety Notes

- `config.BASE_URL` points exclusively to the KIS mock (virtual) trading
  domain. This must not be changed to the live trading domain without a
  full understanding of the consequences.
- Order quantity defaults to 1 share per order.
- The system uses REST polling only; no websocket or real-time streaming
  is used, by design.

---

# 한국어

**금융공학 프로젝트 — KIS 모의(가상)투자 환경**

## 초록 (Abstract)

본 프로젝트는 한국투자증권(KIS) Open API를 기반으로, 삼성전자(`005930`)
종목을 대상으로 한 폴링(polling) 방식의 자동매매 에이전트를 구현한
것입니다. 시세 조회, 주문 제출, 거래소 접수, 체결 감지, 실시간 손익
평가로 이어지는 전체 자동화 파이프라인이 사람의 개입 없이 정상적으로
동작하는지 검증하기 위해, KIS의 공식 모의투자(가상투자) 환경에 대해
시스템을 배포하고 테스트하였습니다. 본 보고서는 시스템 설계, 매매
방법론, 실제 실행을 통한 실증 결과, 그리고 현재 구현의 한계점을
기술합니다.

## 1. 연구 목적

본 프로젝트의 목적은 실제 증권사 API와 연동되는 자동매매 시스템을
구축하는 것이며, 구체적인 목표는 다음과 같습니다.

1. 증권사 REST API로부터 실시간 시세 데이터를 프로그램적으로 조회한다.
2. 거래소 규칙(예: KRX 호가단위 제약)을 준수하는 매수/매도 한도 주문을
   제출하고 정상적으로 접수받는다.
3. 계좌 상태(보유 수량, 예수금, 매도 가능 수량)를 추적하고, 사람의 확인
   없이 주문 체결 여부를 감지한다.
4. 포지션의 성과(평균 매입가, 평가손익)를 실시간으로 평가한다.
5. 정해진 거래 시간 내에서 무인으로 동작하며, 네트워크 장애 및 거래소
   측 주문 거부에 합리적으로 대응한다.

## 2. 시스템 구조

시스템은 각 모듈이 하나의 책임만 갖도록 구성되어 있습니다.

| 모듈 | 역할 |
|---|---|
| `main.py` | 진입점; 의존성을 연결하고 매매 루프를 시작 |
| `config.py` | 환경변수/인증정보 로딩, 조정 가능한 파라미터, KIS API 상수 |
| `auth.py` | OAuth 토큰 발급 및 당일 디스크 캐시 재사용 |
| `api_client.py` | HTTP 전송 계층: 요청 헤더, 타임아웃, 재시도, 호출 간격 제어 |
| `market_data.py` | 현재가 조회 |
| `account.py` | 예수금, 보유 수량, 손익 조회 |
| `orders.py` | 매수/매도 한도 주문 제출 (호가단위 준수 포함) |
| `trader.py` | 거래 시간대 제어 루프 및 체결 확인 로직 |
| `logger.py` | 콘솔 + 파일(rotating) 통합 로깅 |

이러한 모듈 분리를 통해 네트워크, 인증, 매매 로직 등 각 관심사를 독립적으로
테스트하고 수정할 수 있으며, KIS API 고유의 규약(거래ID, 필드명)은
`config.py`에 분리되어 있습니다.

## 3. 매매 방법론

구현된 전략은 **대칭형 브래킷(bracket) 주문 전략**으로, 수익을 최적화하기
위한 전략이 아니라 시스템의 동작을 검증하기 위한 기준선(baseline)으로
사용되었습니다.

매 폴링 주기(기본 60초)마다, 설정된 거래 시간(09:10–15:30) 내에서:

1. `005930`의 현재가 *P*를 조회한다.
2. 현재 보유 수량과 매도 가능 수량을 조회한다.
3. `P − 1,000`원에 매수 한도 주문을 제출한다.
4. 매도 가능한 수량이 충분하면 `P + 1,000`원에 매도 한도 주문을 제출하고,
   그렇지 않으면 매도 주문을 건너뛰고 그 이유를 기록한다.
5. 짧은 대기 후 계좌를 다시 조회하여 보유 수량/예수금 변화로 체결 여부를
   확인한다.

**전략의 한계.** 매수/매도 가격 차이는 고정값이며 포지션의 실제 평균
매입가와 무관하게 적용되고, 이전 주기의 미체결 주문은 새 주문을 내기 전에
취소되지 않습니다. 이는 매매 파이프라인 자체를 검증하기 위한 의도적인
단순화이며, 수익성이나 리스크가 최적화된 전략으로 제시하는 것은 아닙니다.
이를 실제 전략으로 발전시키기 위해 필요한 사항은 6절에서 다룹니다.

## 4. 다룬 엔지니어링 고려사항

실제 모의투자 환경을 대상으로 테스트하는 과정에서 다음과 같은 실제
제약사항을 확인하고 구현에 반영하였습니다. 이는 시스템이 이상화된
시뮬레이션이 아니라 실제 거래소 측 규칙과 정확히 상호작용하고 있다는
근거이기도 합니다.

- **KRX 호가단위 준수.** 한도 주문 가격은 가격대별 공식 호가단위의
  배수여야 합니다(예: 20만~50만원 구간은 500원 단위). 계산된 주문가격은
  제출 전에 가장 가까운 유효 호가단위로 조정됩니다(`orders.py`).
- **거래소 호출 제한 및 지연.** 모의투자 서버는 초당 호출 제한이 있고
  특정 엔드포인트에서 응답 지연이 더 큽니다. 클라이언트는 호출 간격을
  조절하고, 조정된 타임아웃/재시도 정책을 사용합니다(`api_client.py`).
- **예약된 재고 인지.** 총 보유 수량(`hldg_qty`)에는 계좌 자신의 미체결
  매도 주문에 이미 묶인 수량이 포함되어 있습니다. 시스템은 새 매도 주문을
  내기 전에 KIS의 매도가능수량 필드(`ord_psbl_qty`)를 확인함으로써, 이미
  예약된 수량을 매도하려다 거부되는 상황을 방지합니다.

## 5. 실험 결과

2026년 6월 18일 실제 거래 시간 동안 KIS 모의투자 서버를 대상으로 시스템을
실행하였습니다. 대표적인 로그 근거는 다음과 같습니다(전체 로그:
[trading.log](trading.log)).

**5.1 주문 제출 및 거래소 접수.** 시스템이 제출한 모든 주문은 KIS에
접수되어 실제(모의) 주문번호를 받았습니다.

```
13:55:04  매수 주문 제출: 수량=1 가격=353000 종목=005930
13:55:11  매수 주문 접수됨, 주문번호=0000029840
13:55:11  매도 주문 제출: 수량=1 가격=355000 종목=005930
13:55:13  매도 주문 접수됨, 주문번호=0000029843
```

**5.2 주문 체결.** 연속된 계좌 조회 사이에 보유 수량이 변화하는 것을
관찰하였으며, 이는 제출된 주문이 단순히 접수된 것이 아니라 거래소에서
실제로 체결되었음을 의미합니다.

```
13:55:04  보유 수량 = 13주
13:55:26  보유 수량 = 14주   (체결 감지됨)
```

**5.3 실시간 포지션 성과.** 손익 필드를 연동한 결과, 시스템은 매 주기마다
KIS가 계산한 실제 평균 매입가 기준의 평가손익을 보고합니다.

```
2026-06-18 13:55:26  예수금=10,000,000원
                      보유 수량=14주
                      평균 매입가=353,753원/주
                      평가손익=-3,548원 (-0.07%)
```

이 시점의 포지션은 약 -0.07%의 소폭 평가손실 상태였으며, 이는 시세가
포지션의 평균 매입가 근처의 좁은 범위에서 오르내리고 있었던 상황과
일치합니다.

**5.4 오류 허용성(Fault Tolerance).** 매도 가능한 재고가 없는 상황에서
시스템은 오류로 중단되지 않고 유효하지 않은 주문을 정확히 회피하였습니다.

```
13:34:22  매도 주문 건너뜀: 매도 가능 수량 0주, 필요 수량 1주.
```

## 6. 한계 및 향후 과제

- **실현손익(realized P&L) 및 거래 단위 회계 미구현.** 평가손익은 KIS가
  제공하는 포지션 단위 평가값을 그대로 사용하지만, 개별 거래(진입가,
  청산가, 보유 기간)에 대한 자체 거래 원장이나 누적 실현수익은 계산하지
  않습니다.
- **리스크 조정 성과지표 부재.** 샤프비율, 최대낙폭(MDD), 승률 등은
  계산되지 않으며, 특정 시점의 평가손익만 확인할 수 있습니다.
- **매입원가를 고려하지 않는 주문 로직.** 매도가격은 포지션의 평균
  매입가가 아닌 현재 시세를 기준으로 산출되므로, 체결이 곧 수익을
  보장하지는 않습니다.
- **주문 생애주기 관리 부재.** 이전 주기의 미체결 주문이 취소되지 않아,
  세션이 진행될수록 미체결 주문이 누적됩니다.
- **포지션 사이징 및 손절 로직 부재.** 주문 수량은 계좌 규모나 평가손실
  여부와 무관하게 항상 1주로 고정되어 있습니다.

위 사항들은 본 프로젝트를 시스템 검증 수준에서 실제 전략 평가 수준으로
발전시키기 위한 자연스러운 다음 단계입니다.

## 7. 결론

실험 결과는 구현된 시스템이 실제 증권사 테스트 환경을 대상으로 전체
자동매매 주기를 정확히 수행함을 확인시켜 줍니다: 실제 시세를 조회하고,
거래소 규칙을 준수하는 주문을 제출하여 접수·체결시키며, 체결을 감지하고,
실제 환경에서 발생하는 오류 상황(호출 제한, 재고 제약)에서도 중단되지
않고, 거래소 자체 계좌 데이터를 기반으로 실시간 포지션 성과를 보고합니다.
이는 본 프로젝트의 엔지니어링 목표를 검증하는 결과입니다. 다만 이는
정상적으로 동작하는 매매 시스템 파이프라인을 시연한 것으로 해석되어야
하며, 수익성이 검증된 매매 전략의 증거로 해석되어서는 안 됩니다.

---

## 부록 A: 설치 및 재현 방법

Python 3.9 이상이 필요합니다.

```powershell
cd samsung_auto_trader
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 필수 환경변수

| 변수 | 설명 |
|---|---|
| `GH_ACCOUNT` | 모의투자 계좌번호 (`12345678-01`, `1234567801`, 또는 `12345678`) |
| `GH_APPKEY` | KIS 모의투자 앱키 |
| `GH_APPSECRET` | KIS 모의투자 앱시크릿 |

`.env.example`을 `.env`로 복사한 뒤 실제 값을 입력하거나, OS 환경변수로
설정합니다(`$env:GH_ACCOUNT = "..."` 등). `.env`는 gitignore 대상이며
절대 커밋되지 않습니다.

### 실행

```powershell
python main.py
```

거래 시간 전에 실행하면 시작 시각까지 대기하며, 15:30 이후에 실행하면
매매 없이 즉시 종료합니다. `Ctrl+C`로 언제든 종료할 수 있습니다. 로그는
콘솔과 `trading.log`에 기록됩니다.

## 부록 B: 프로젝트 구조

```
samsung_auto_trader/
    main.py            진입점
    config.py          설정, 상수, KIS tr_id/필드명
    logger.py           로깅 설정
    auth.py              토큰 발급 및 캐싱
    api_client.py        HTTP 전송 계층
    market_data.py       현재가 조회
    account.py            예수금/보유수량/손익 조회
    orders.py              주문 제출
    trader.py               매매 루프 및 체결 로직
    .env                     인증정보 (gitignore 대상, 사용자 생성)
    .env.example              인증정보 템플릿
    token_cache.json        실행 시 자동 생성 (gitignore 대상)
    trading.log               실행 시 자동 생성 (gitignore 대상)
    requirements.txt
    README.md
```

## 부록 C: KIS API 필드 검증에 대한 참고

`config.py`의 거래ID(`TR_ID_*`)는 공식 `koreainvestment/open-trading-api`
저장소의 예제 스크립트로 검증하였습니다. 일부 잔고 응답 필드명
(`hldg_qty`, `pdno`, `dnca_tot_amt`, `ord_psbl_qty`, `pchs_avg_pric`,
`evlu_pfls_amt`, `evlu_pfls_rt`)은 KIS의 공개 명세를 따르되, 로컬 문서가
아닌 테스트 중 실제 응답을 통해 검증하였으며, KIS 측에서 필드를 변경할
경우 쉽게 수정할 수 있도록 `config.py`에 별도 상수로 분리해 두었습니다.

## 안전 수칙

- `config.BASE_URL`은 KIS 모의(가상)투자 도메인만 가리킵니다. 그 영향을
  충분히 이해하지 못한 상태에서 실전투자 도메인으로 변경해서는 안 됩니다.
- 주문 수량은 기본적으로 1주입니다.
- 의도적으로 REST 폴링 방식만 사용하며, 웹소켓이나 실시간 스트리밍은
  사용하지 않습니다.
