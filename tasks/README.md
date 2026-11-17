# tasks

연구실 비서 3종과 비슷한 RoboCasa 태스크입니다 (robocasa/robocasa main, 261117 확인).

| 데모 | RoboCasa 참고 태스크 | 부족한 점 |
| --- | --- | --- |
| 1. 책상 치우기 | `ClearingTable` 계열, `PickPlaceCounterToCabinet`/`CounterToDrawer`, `OrganizingRecycling` | 부엌 장면만 있음. 책·펜·펜꽂이·쓰레기통 물체 없음 |
| 2. 냉장고에서 꺼내오기 | `OpenFridge`/`CloseFridge`, `PickPlaceFridgeShelfToDrawer`, `LoadingFridge`(반대 동작), `NavigateKitchen` | 사람에게 건네기 없음 |
| 3. 간식 채우기 | `RestockingSupplies`(`RestockPantry` 등), `SnackPreparation` | 바구니 빈칸 판단은 직접 정의 |

기본 물체에 과자(chips)·초콜릿·캔·팩 음료가 있습니다.
