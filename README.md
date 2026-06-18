# Auto-Trading System (ECO4126 Assignment)

A project for the ECO4126 course. Using the Korea Investment & Securities
(KIS) Open API, this program retrieves real-time quotes for Samsung
Electronics (005930), automatically submits buy/sell orders, and verifies
order execution by re-checking holdings/cash — all tested against the
actual KIS mock-trading (paper trading) server, not a local simulation.

The full code lives in [`samsung_auto_trader/`](samsung_auto_trader/).
`trading.log` is excluded from version control (`.gitignore`) since it
contains account-specific run output; the figures below are filled in
directly from that log.

## What This Program Does

- Polls the current price of Samsung Electronics on a fixed interval (60s)
- Automatically submits a buy order slightly below, and a sell order
  slightly above, the current price
- Re-queries holdings and cash balance after each order cycle to confirm
  whether orders were actually filled
- Profit/loss is checked manually against the KIS mock-trading app rather
  than computed by the program itself
- Only operates within market hours (09:10–15:30) and automatically halts
  outside that window

## Results

The log below is unedited output from `trading.log`, recorded against the
real KIS mock-trading server. Each cycle queries the current price, places
a buy order slightly under it and a sell order slightly over it, then
re-checks the account snapshot a few seconds later to see whether either
order filled:

```
<img width="1042" height="652" alt="image" src="https://github.com/user-attachments/assets/cfab4eab-8e83-4acb-935d-3e952dcbedb0" />

```

The program does not compute P&L itself; profit/loss was checked manually
against the KIS mock-trading app alongside these logs.

**Issue found**: pricing the sell order purely off the current price
("current price + 1,000 KRW") sometimes filled below the original
purchase cost, since the current price drifts between cycles.
**Fix applied**: the sell price was changed to
`max(current price + 1,000 KRW, average cost + 500 KRW)`, and buying was
capped once holdings exceeded 10 shares, so the position couldn't grow
without bound while waiting for a profitable exit.

## How to Run

```powershell
cd samsung_auto_trader
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # Enter KIS mock-trading app key / account number
python main.py
```

See [`samsung_auto_trader/README.md`](samsung_auto_trader/README.md) for
details on environment variable setup, token caching, and related
configuration.

## Folder Structure

```
trading_system/
    samsung_auto_trader/   The auto-trading program implemented for this assignment (the core deliverable)
    open-trading-api/      KIS's official example code, kept for reference only (not part of the submission)
```

## Limitations and Reflections

- The program doesn't compute or log unrealized P&L itself; profit/loss
  was checked manually against the KIS mock-trading app, cross-referenced
  with the holdings/cash snapshots in `trading.log`.
- The order-pricing rule is still simple. Switching to an
  average-cost-based rule clearly improved results, but adding more
  sophisticated signals (e.g., moving averages, volatility) could likely
  improve it further.
- Unfilled orders from previous cycles are not canceled before new orders
  are submitted, which occasionally caused the sellable quantity to
  temporarily drop to zero when unfilled orders accumulated.


---

# 삼성전자 자동매매 시스템 (ECO4126 과제)

ECO4126 수업 과제로 진행한 프로젝트입니다. 한국투자증권(KIS) Open API를 이용해서
삼성전자(005930) 종목을 대상으로 시세를 조회하고, 직접 매수/매도 주문을 넣고,
보유 수량/예수금을 다시 조회해서 체결 여부를 확인하는 자동매매 프로그램을
직접 구현했습니다.

한국투자증권 모의투자 환경에 연결해서 동작을 확인했습니다. 코드 전체는
[`samsung_auto_trader/`](samsung_auto_trader/) 폴더에 있습니다. `trading.log`는
계정별 실행 기록이 포함되어 있어 `.gitignore`로 제외했고, 아래 수치는 해당 로그를
직접 보고 채워 넣은 값입니다.

## 무엇을 만들었나

- 일정한 주기(60초)마다 삼성전자 현재가를 조회
- 현재가보다 살짝 낮은 가격에 매수 주문, 살짝 높은 가격에 매도 주문을 자동으로 제출
- 주문을 넣은 뒤 보유 수량/예수금을 다시 조회해서 체결이 됐는지 확인
- 평가손익은 프로그램이 직접 계산하지 않고, 한투 모의투자 앱을 직접 보고 확인
- 정해진 거래 시간(09:10~15:30) 안에서만 동작하고, 그 외 시간엔 자동으로 멈춤

## 결과

아래는 `trading.log`에 실제로 기록된 내용을 그대로 가져온 것입니다. 매 주기마다
현재가를 조회하고, 그보다 살짝 낮은 가격에 매수, 살짝 높은 가격에 매도 주문을
넣은 뒤, 몇 초 후 계정 상태를 다시 조회해서 체결 여부를 확인합니다:

```
<img width="1042" height="652" alt="image" src="https://github.com/user-attachments/assets/3b7cbeef-97ec-49c4-b011-deebb6bca40c" />

```

프로그램이 직접 손익을 계산하지는 않고, 위 로그와 함께 한투 모의투자 앱을
직접 확인하면서 손익 여부를 판단했습니다.

**발견한 문제**: 매도 주문 가격을 단순히 "현재가 + 1,000원"으로만 정하다 보니,
주기마다 현재가가 바뀌면서 매입원가보다 낮은 가격에 체결되는 경우가 있었습니다.
**개선한 부분**: 매도 주문 가격을 `max(현재가 + 1,000원, 평균매입가 + 500원)`로
바꾸고, 보유 수량이 10주를 넘으면 매수를 멈추도록 해서, 수익이 나는 시점까지
포지션이 무한정 커지지 않도록 했습니다.

## 실행 방법

```powershell
cd samsung_auto_trader
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # KIS 모의투자 앱키/계좌번호 입력
python main.py
```

환경변수 설정, 토큰 캐싱 등 자세한 내용은
[`samsung_auto_trader/README.md`](samsung_auto_trader/README.md)에 정리해
두었습니다.

## 폴더 구조

```
trading_system/
    samsung_auto_trader/   직접 구현한 자동매매 프로그램 (이 과제의 핵심)
    open-trading-api/      참고용으로 받아온 KIS 공식 예제 코드 (제출물 아님)
```

## 한계 및 느낀 점

- 프로그램이 직접 평가손익을 계산하거나 기록하지는 않고, `trading.log`의
  보유 수량/예수금 변화를 한투 모의투자 앱과 대조하면서 수동으로 확인했습니다.
- 매수/매도 가격을 정하는 규칙이 아직 단순합니다. 평균매입가 기준으로 고치고
  나니 결과가 확실히 좋아졌는데, 더 정교한 신호(예: 이동평균, 변동성 등)를
  추가하면 더 나아질 수 있을 것 같습니다.
- 이전 주기에 낸 미체결 주문을 취소하지 않고 계속 새 주문을 쌓는 방식이라,
  체결되지 않은 주문이 쌓이면 매도 가능 수량이 일시적으로 0이 되는 경우가
  있었습니다.
