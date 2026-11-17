# RB-Y1 Sim2Real

RB-Y1(Model M v1.2)로 연구실 비서 태스크 3종을 시뮬레이션(RoboCasa/robosuite)에서 학습하고 실물로 옮기는 프로젝트입니다.

| 항목 | 내용 |
| --- | --- |
| 작업 호스트 | lab-desktop (`~/Desktop/lab/robot/rby1-sim2real`), 시뮬·학습·페이지는 Docker에서 실행 |
| 실물 제어 | 별도 저장소 `robo-synapse` (제어 PC·U-PC). 이 저장소는 실물 제어 코드를 두지 않음 |
| 진행상황 페이지 | `status-page/` (메인·영상·태스크 탭), lab-desktop loopback `127.0.0.1:8920` |
| 상태 | 261117 저장소 생성. 구현 전 |

## 구현 방법론
명령을 하위 작업으로 분해하고, 부위별 모듈이 나눠 수행합니다.

- **베이스**: 사전 등록한 연구실 지도·장소·물체 위치로 작업 위치까지 이동
- **몸통**: 팔이 작업하기 쉬운 높이·각도로 상체 자세 조정
- **팔**: 잡기부터 시작하는 단위 조작 스킬. 학습 정책과 CaP를 비교 후 결정

## 태스크
1. 책상 치우기: "책상 좀 치워줘"
2. 냉장고에서 먹을 거 꺼내오기: "콜라 하나 갖다줘"
3. 간식 채우기: "간식 바구니 채워줘"

RoboCasa 참고 태스크는 [tasks/README.md](tasks/README.md)를 봅니다.

## 단계
1. 환경: Docker 이미지, RB-Y1 MJCF를 robosuite 로봇으로 등록, RoboCasa 부엌에 로딩
2. 기본 태스크: `OpenFridge`·`PickPlace`로 팔·베이스·몸통 동작 확인
3. 연구실 장면: 책상·책꽂이·간식 바구니 물체·장면 추가
4. 데이터: 시뮬 텔레옵 시연 수집, 실물 기록과 행동 형식 맞추기
5. 학습: 학습 정책 vs CaP 비교
6. 실물 이전: robo-synapse로 실행, 성공률 비교

## 폴더
| 폴더 | 내용 |
| --- | --- |
| `docker/` | 시뮬 이미지 (robosuite + RoboCasa + MuJoCo) |
| `robots/rby1/` | RB-Y1 robosuite 등록 (MJCF, 그리퍼, 베이스, 카메라) |
| `tasks/` | 연구실 비서 3종 태스크 |
| `data/` | 시연 수집·변환 스크립트. 데이터 자체는 Git에 넣지 않음 |
| `policies/` | 학습 정책 / CaP 실험 |
| `status-page/` | 진행상황 페이지 (research-page-template 0.1.0) |
| `docs/` | 결정 기록 |

## 진행상황 페이지
```sh
cd status-page
docker run --rm -v "$PWD":/w -w /w python:3.11-slim python3 scripts/build.py
docker run -d --name rby1-sim2real-page --restart unless-stopped --network host \
  -v "$PWD":/w -w /w python:3.11-slim python3 scripts/serve.py --port 8920
```
Mac에서 보기: `ssh -N -L 8920:127.0.0.1:8920 lab-desktop` 후 http://127.0.0.1:8920
