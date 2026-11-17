# robots/rby1

RB-Y1을 robosuite 로봇으로 등록할 자리입니다. 아직 작성하지 않았습니다.

| 항목 | 확인 내용 (261117) |
| --- | --- |
| 모델 원본 | RainbowRobotics/rby1-sdk `models/rby1m/mujoco/model_v1.2.xml` (실물 Model M v1.2), Apache 2.0 |
| robosuite 지원 | RB-Y1 없음. 양팔+몸통+이동 베이스 구조인 Tiago가 가장 가까운 참고 |
| RoboCasa | 기본 로봇 PandaOmron, `kitchen.py`에 PandaOmron 전용 분기·로봇 1대 고정 |

필요한 일: 양팔·몸통·머리 ManipulatorModel, 메카넘 베이스(전방향 이동 베이스로 근사), RB-Y1 그리퍼, RoboCasa 카메라 설정(머리·손목)·초기 자세·생성 위치.
