# RB-Y1 Sim2Real

RB-Y1(Model M v1.2)로 연구실 비서 태스크 3종을 RoboCasa(robosuite)에서 학습하고 실물로 옮기는 프로젝트입니다.
**원칙: 기존 프레임워크를 그대로 쓰고, 직접 작성은 RB-Y1 등록과 실물 형식 변환에 한정합니다.**

| 항목 | 내용 |
| --- | --- |
| 작업 호스트 | lab-desktop `~/Desktop/lab/robot/rby1-sim2real`, 모든 실행은 Docker(`scripts/run.sh`) |
| 고정 소스 | `ext.lock`: robosuite 5ce6643, robocasa 425684d, rby1-sdk main → `ext/` (Git 밖, 에셋 ~23 GB) |
| 실물 제어 | 별도 저장소 robo-synapse. 이 저장소는 실물 명령을 보내지 않음 |

## 무엇을 재사용하고 무엇을 썼나
| 단계 | 재사용 | 이 저장소에서 쓴 것 |
| --- | --- | --- |
| 로봇 | robosuite ManipulatorModel·GripperModel(Tiago 패턴), NullMobileBase, BASIC composite controller | `rby1_sim/robot/`: rby1-sdk MJCF → robosuite 형식 변환, 제어기 설정(팔 OSC 기준 = `link_torso_5`) |
| 환경 | RoboCasa `create_env`, 부엌 장면·태스크·성공 판정 | `rby1_sim/sim/robocasa_patch.py`: 제어기 설정 조회·카메라 위치 몽키패치(ext 무수정) |
| 태스크 | `FoodCleanup`, `MoveToCounter`, `MakeFruitBowl` | `rby1_sim/tasks/`: 물체·문장만 바꾼 서브클래스 |
| 병렬·reset | robosuite `hard_reset`, tianshou `SubprocVectorEnv` | `rby1_sim/sim/vec.py`: N번에 한 번만 새 장면 |
| 시연 수집 | `robocasa.scripts.collect_demos`(키보드·스페이스마우스 텔레옵) | 없음 (`python -m rby1_sim.run`으로 실행) |
| 변환 | robosuite 상태 재생, RoboCasa HDF5 형식 | `scripts/convert_to_real_format.py`: 실물 형식 LeRobot 데이터셋 |
| 학습 | lerobot 0.3.3 CLI (ACT 등) | `scripts/train.sh`: 인자만 채움 |
| 실물 연결 | robo-synapse "Policy 실행" 패널(ZMQ 정책 서버 계약) | `rby1_sim/serve/policy_server.py` |

## 실물 형식 (robo-synapse CONTROL_API.md 3절)
- `observation.state` 15 = 활성 팔 관절 7 + 손끝 위치 3 + 쿼터니언 xyzw 4 + 그리퍼(닫힘=1), `link_torso_5` 기준
- `action` 7 = `ee_delta`: 위치 변화 3(m) + 회전 벡터 3(rad, 현재 자세 앞에 곱함) + 그리퍼
- 이미지: `observation.images.top`(머리), `observation.images.wrist`(손목)

## 태스크 (실물 물체 → RoboCasa 대체)
| 데모 | 클래스 | 기반 | 대체 |
| --- | --- | --- | --- |
| 책상 치우기 | `TidyDesk` | `FoodCleanup` | 책=boxed_food→캐비닛, 펜=straw→mug, 과자=bar→basket |
| 콜라 가져오기 | `FetchColaFromFridge` | `MoveToCounter` | 콜라=can, 건네는 자리=조리대 접시, `fridge_open=False`면 문 닫힌 채 시작 |
| 간식 채우기 | `RefillSnackBasket` | `MakeFruitBowl` | 바구니=basket, 간식=bar·donut·cupcake |

## 사용법
```sh
sh scripts/setup_ext.sh --assets                  # ext/ 소스 고정 + 에셋 다운로드 (처음 한 번)
docker build -t rby1-sim2real:latest -f docker/Dockerfile .
scripts/run.sh --gpu python -m pytest -q tests/   # 로봇·태스크·변환·정책 서버 테스트

# 시연 수집 (X 디스플레이 필요, RoboCasa 원본 스크립트)
python -m rby1_sim.run robocasa.scripts.collect_demos --environment FetchColaFromFridge --robots RBY1 --device keyboard
# 실물 형식으로 변환 → 학습 → 서빙
scripts/run.sh --gpu python scripts/convert_to_real_format.py --hdf5 DEMO.hdf5 --out outputs/datasets/fetch_cola
scripts/train.sh outputs/datasets/fetch_cola fetch_cola_act --steps=50000 --batch_size=8
scripts/run.sh --gpu python -m rby1_sim.serve.policy_server --checkpoint outputs/train/fetch_cola_act/checkpoints/last/pretrained_model
# 속도 측정
scripts/run.sh --gpu python scripts/bench_env.py --workers 2
scripts/run.sh --gpu python scripts/render_scene.py TidyDesk
```

## 측정 (261117, lab-desktop RTX 3050 8 GB, 다른 컨테이너가 6.6 GB 사용 중)
| 항목 | 값 |
| --- | --- |
| reset, PandaOmron / RB-Y1 (원본 bench_speed, 5회) | 1.86 s / 4.33 s |
| step, PandaOmron / RB-Y1 (원본 bench_speed) | 66.8 / 46.7 fps |
| reset 새 장면 / 같은 장면 (RB-Y1, 카메라 2개) | 3.8–5.6 s / 0.92–1.07 s |
| step, GPU 1개 / GPU 작업자 2 (합계) | 35.3 / 48.1 steps/s |
| step, CPU 1개 / CPU 작업자 4 (합계) | 13.5 / 34.5 steps/s |
GPU 작업자 4개 이상은 GPU 메모리 부족으로 실패합니다.

## 알려진 점
- numba JIT가 이 이미지에서 segfault → `setup_ext.sh`가 robosuite `ENABLE_NUMBA=False`로 둠
- 바퀴 충돌 메시는 제거(베이스는 슬라이드 관절로 구동). 있으면 RoboCasa 배치 검사가 로봇을 부엌 밖으로 밀어냄
- 관절 토크 한계·감쇠는 근사값, 실물과 맞추기 전
- 진행상황 페이지 `status-page/`(lab-desktop 127.0.0.1:8920)는 보조 기록
