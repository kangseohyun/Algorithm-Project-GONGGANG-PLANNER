"""
============================================================
기능명:
혼잡도/대기시간 계산

담당자:
김시형

핵심 기능:
- 후보 장소별 현재 시간대 혼잡도 점수를 계산한다.
- 혼잡도 점수와 장소 유형을 기준으로 예상 대기시간을 계산한다.
- 혼잡도 데이터가 없는 장소는 기본값으로 처리한다.
- 추천 기능에서 바로 사용할 수 있도록 list[dict] 형태로 반환한다.

사용 알고리즘:
- 알고리즘명: 이진 탐색(Binary Search)
  사용 위치: find_time_slot()
- 알고리즘명: 딕셔너리 탐색(Dictionary Lookup)
  사용 위치: normalize_place_name(), get_crowd_level()
- 알고리즘명: 규칙 기반 계산(Rule-based Calculation)
  사용 위치: calculate_wait_minutes()

사용 자료구조:
- 자료구조명: 리스트(List)
  사용 위치: TIME_SLOT_STARTS, candidate_places, crowd_results
- 자료구조명: 딕셔너리(Dictionary)
  사용 위치: PLACE_INFO, PLACE_ALIASES, WAIT_TIME_TABLE
- 자료구조명: 중첩 딕셔너리(Nested Dictionary)
  사용 위치: CROWD_DATA

입력 데이터:
- current_time: "HH:MM" 형식의 현재 시간 문자열
- candidate_places: 혼잡도/대기시간을 계산할 후보 장소명 리스트
- crowd_data: 장소별 시간대 혼잡도 데이터, 생략 시 data/crowd_data.py 사용

출력 데이터:
- crowd_results: 후보 장소별 혼잡도/대기시간 결과 리스트
- 반환 key: place, crowd_level, expected_wait_minutes, time_slot, is_default
============================================================
"""

from bisect import bisect_right

from data.crowd_data import (
    CROWD_DATA,
    CROWD_TARGETS,
    DEFAULT_CROWD_LEVEL,
    DEFAULT_PLACE_TYPE,
    PLACE_ALIASES,
    TIME_SLOTS,
    WAIT_TIME_TABLE,
)


# [자료구조: 리스트]
# 이진 탐색을 위해 시간대 시작 시각만 따로 저장한다.
TIME_SLOT_STARTS = [slot[0] for slot in TIME_SLOTS]


# [자료구조: 딕셔너리]
# 장소명을 key로 사용해 장소 유형과 대기시간 필요 여부를 빠르게 찾는다.
PLACE_INFO = {
    target["place"]: {
        "place_type": target["place_type"],
        "need_wait": target["need_wait"],
    }
    for target in CROWD_TARGETS
}


def time_to_minutes(time_text):
    """HH:MM 형식의 시간 문자열을 분 단위 정수로 변환한다."""
    hour, minute = map(int, time_text.split(":"))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("시간은 'HH:MM' 형식이어야 합니다.")
    return hour * 60 + minute


def minutes_to_time(minutes):
    """분 단위 정수를 HH:MM 문자열로 변환한다."""
    if not 0 <= minutes < 24 * 60:
        raise ValueError("분 단위 시간은 0 이상 1440 미만이어야 합니다.")
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


def normalize_place_name(place_name):
    """장소명을 공통 명칭 규칙의 표준 장소명으로 변환한다."""
    return PLACE_ALIASES.get(place_name, place_name)


def load_sample_data():
    """혼잡도/대기시간 계산용 샘플 데이터를 반환한다."""
    return CROWD_DATA


def validate_required_keys(data, required_keys):
    """통합에 필요한 key가 모두 있는지 확인한다."""
    return all(key in data for key in required_keys)


def find_time_slot(current_minutes, crowd_data=None):
    """
    현재 시간이 속한 시간대 구간을 찾는다.

    [알고리즘: 이진 탐색(Binary Search)]
    정렬된 TIME_SLOT_STARTS에서 현재 시간보다 작거나 같은 가장 가까운 시작 시각을 찾는다.
    """
    slot_index = bisect_right(TIME_SLOT_STARTS, current_minutes) - 1
    return TIME_SLOTS[slot_index][1]


def get_crowd_level(place, time_slot, crowd_data=None):
    """
    특정 장소/시간대의 혼잡도 점수를 가져온다.

    [알고리즘: 딕셔너리 탐색(Dictionary Lookup)]
    장소명과 시간대를 key로 사용해 혼잡도 점수를 조회한다.
    """
    data = crowd_data if crowd_data is not None else CROWD_DATA
    standard_place = normalize_place_name(place)
    place_crowd = data.get(standard_place, {})
    return place_crowd.get(time_slot, DEFAULT_CROWD_LEVEL)


def calculate_wait_minutes(crowd_level, place_type=DEFAULT_PLACE_TYPE, need_wait=True):
    """
    혼잡도 점수를 예상 대기시간으로 바꾼다.

    [알고리즘: 규칙 기반 계산(Rule-based Calculation)]
    장소 유형과 혼잡도 점수에 맞는 대기시간 규칙을 적용한다.
    """
    if not need_wait:
        return 0

    wait_table = WAIT_TIME_TABLE.get(place_type, WAIT_TIME_TABLE[DEFAULT_PLACE_TYPE])
    return wait_table.get(crowd_level, wait_table[DEFAULT_CROWD_LEVEL])


def get_default_crowd_result(place, current_time):
    """혼잡도 데이터가 없을 때 기본 결과를 만든다."""
    current_minutes = time_to_minutes(current_time)
    time_slot = find_time_slot(current_minutes)

    return {
        "place": normalize_place_name(place),
        "crowd_level": DEFAULT_CROWD_LEVEL,
        "expected_wait_minutes": 0,
        "time_slot": time_slot,
        "is_default": True,
    }


def analyze_crowd(current_time, candidate_places, crowd_data=None):
    """
    후보 장소별 혼잡도와 예상 대기시간을 계산한다.

    반환 key:
    - place: 장소명
    - crowd_level: 혼잡도 점수
    - expected_wait_minutes: 예상 대기시간
    - time_slot: 현재 시간이 속한 시간대
    - is_default: 기본값 사용 여부
    """
    current_minutes = time_to_minutes(current_time)
    time_slot = find_time_slot(current_minutes, crowd_data)
    data = crowd_data if crowd_data is not None else CROWD_DATA
    crowd_results = []

    for candidate_place in candidate_places:
        place = normalize_place_name(candidate_place)

        if place not in data:
            crowd_results.append(get_default_crowd_result(place, current_time))
            continue

        place_info = PLACE_INFO.get(
            place,
            {"place_type": DEFAULT_PLACE_TYPE, "need_wait": False},
        )
        crowd_level = get_crowd_level(place, time_slot, data)
        expected_wait_minutes = calculate_wait_minutes(
            crowd_level,
            place_info["place_type"],
            place_info["need_wait"],
        )

        crowd_results.append(
            {
                "place": place,
                "crowd_level": crowd_level,
                "expected_wait_minutes": expected_wait_minutes,
                "time_slot": time_slot,
                "is_default": False,
            }
        )

    return crowd_results


if __name__ == "__main__":
    current_time = "12:20"
    candidate_places = [
        "AI도서관 열람실",
        "교육대학원 식당",
        "비전타워 식당",
        "스타벅스 가천대점",
        "제3기숙사 기숙사식당",
        "중앙도서관 열람실",
        "데이터에 없는 장소",
    ]

    for result in analyze_crowd(current_time, candidate_places):
        print(result)
