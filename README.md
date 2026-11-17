# RB-Y1 RoboCasa

RB-Y1(Model M v1.2)을 RoboCasa 부엌 시뮬레이션에 올리는 **자산 패키지 + 시뮬 서버**입니다.
CaP·Harness·정책 실행·기록 같은 상위 기능은 robo-synapse가 맡고, 이 저장소는 그 아래에서 시뮬레이션만 제공합니다.

```
robo-synapse (WebUI 패널, Rby1Skills, CodeAsPolicy, 정책 실행, 기록)
   │  pip install -e <이 저장소>  →  rby1_robocasa_client (numpy·pyzmq·msgpack만)
   │  ZMQ tcp://<GPU 서버>:5590
   ▼
rby1_robocasa.server (Docker, GPU)  →  RoboCasa + robosuite + RB-Y1
```

## 구성
| 모듈 | 역할 |
| --- | --- |
| `rby1_robocasa/robot/` | rby1-sdk MJCF → robosuite 로봇·그리퍼 변환(`build_model.py`), 클래스(`models.py`), 제어기 설정(`configs/`) |
| `rby1_robocasa/env/` | RoboCasa `create_env` 래퍼(`envs.py`), 최소 몽키패치(`patch.py`), 장면 재사용·병렬(`vec.py`) |
| `rby1_robocasa/tasks/` | 연구실 비서 3종: RoboCasa 태스크 서브클래스 |
| `rby1_robocasa/server/` | 시뮬 서버. `core`(에피소드·스텝·프레임) + 부위별 `arm`·`gripper`·`base`·`body`·`perception` + `rpc` |
| `rby1_robocasa_client/` | 클라이언트(`SimClient`)와 robo-synapse 장치 계약 어댑터(`SimArm`·`SimGripper`·`SimMobileBase`·`SimBody`) |
| `rby1_robocasa/register.py`, `run.py` | robosuite/RoboCasa 등록, RoboCasa 원본 스크립트를 RB-Y1로 실행 |
| `scripts/` | `setup_ext.sh`(소스·에셋), `run.sh`(컨테이너 실행), `sim_server.sh`(서버 시작·정지), `bench_env.py`, `render_scene.py` |

## 시뮬 서버 API (`<part>.<method>`)
좌표는 `link_torso_5`(x 앞, y 왼쪽, z 위), 쿼터니언 (x, y, z, w), 미터. 시뮬 시간은 명령 안에서만 흐릅니다(20 Hz).

| part | methods |
| --- | --- |
| `episode` | `reset(task, seed, layout, style, task_kwargs)`, `info`, `success`, `step(n)` |
| `arm` | `joint_names`, `joint_positions`, `ee_pose`, `move_to_pose`, `send_joint_trajectory`, `external_wrench`, `tare_wrench` |
| `gripper` | `open`, `close(width_m)`, `state`(`widthMeters`·`hasObject`), `width`, `held_object` |
| `base` | `set_velocity(vx, vy, wz, duration_s)`(속도 임대, 갱신 안 하면 정지), `odom_pose`, `world_pose`, `stop` |
| `body` | `joint_names`, `joint_positions`, `set_torso(6)`, `set_head(2)` |
| `perception` | `cameras`, `camera(name)`(RGB·실측 깊이·K·T_base_cam), `objects()`(정답 물체 위치·크기·잡은 팔) |

## 실행 위치 옮기기
Docker + NVIDIA GPU가 있는 어느 서버든 됩니다.
```sh
git clone https://github.com/aiden890/rby1-robocasa && cd rby1-robocasa
sh scripts/setup_ext.sh --assets                              # ext/ 소스 고정 + 에셋 ~23 GB
docker build -t rby1-robocasa:latest -f docker/Dockerfile .
scripts/sim_server.sh start                                    # 기본: 이 서버의 tailnet IP:5590
scripts/run.sh --gpu python -m pytest -q tests/                # 13개
```
클라이언트(예: 제어 PC의 robo-synapse): `pip install -e <경로>` 후 `SimClient("tcp://<서버 IP>:5590")` 또는 환경 변수 `RBY1_ROBOCASA_URL`.

## 태스크 (실물 물체 → RoboCasa 대체)
| 데모 | 클래스 | 기반 | 대체 |
| --- | --- | --- | --- |
| 책상 치우기 | `TidyDesk` | `FoodCleanup` | 책=boxed_food→캐비닛, 펜=straw→mug, 과자=bar→basket |
| 콜라 가져오기 | `FetchColaFromFridge` | `MoveToCounter` | 콜라=can, 건네는 자리=조리대 접시, `fridge_open=False`면 문 닫힌 채 시작 |
| 간식 채우기 | `RefillSnackBasket` | `MakeFruitBowl` | 바구니=basket, 간식=bar·donut·cupcake |

## 측정 (261117, lab-desktop RTX 3050 8 GB, 다른 컨테이너가 6.6 GB 사용 중)
| 항목 | 값 |
| --- | --- |
| reset, PandaOmron / RB-Y1 (RoboCasa bench_speed, 5회) | 1.86 s / 4.33 s |
| step, PandaOmron / RB-Y1 | 66.8 / 46.7 fps |
| reset 새 장면 / 같은 장면 (RB-Y1, 카메라 2개) | 3.8–5.6 s / 0.92–1.07 s |
| step, GPU 1개 / 작업자 2 (합계) | 35.3 / 48.1 steps/s |

## 알려진 점
- numba JIT가 이 이미지에서 segfault → `setup_ext.sh`가 robosuite `ENABLE_NUMBA=False`
- 바퀴 충돌 메시 제거(베이스는 슬라이드 관절 구동, 있으면 RoboCasa 배치 검사가 로봇을 부엌 밖으로 밀어냄)
- 팔 OSC는 world 프레임으로 제어하고 서버가 `link_torso_5` 명령을 변환(몸통 프레임 기준이면 흔들림이 되먹임됨)
- 관절 토크 한계·감쇠는 근사값(몸통 2000 Nm 등), 실물과 맞추기 전
- 관절 궤적 명령은 목표 관절의 손끝 자세로 직교 이동(관절 정확 추종 아님)
