"""
============================================================
기능명: 시간표/공강시간 분석
담당자: 김희민

핵심 기능:
- 현재 요일/시간 기준으로 공강 여부 판별
- 다음 수업 정보(과목명, 시작시간, 건물) 계산
- 공강 시간 및 장소 추천 가능 시간 반환

사용 알고리즘:
- 알고리즘명: 정렬 알고리즘 (Sorting)
  사용 위치: get_daily_schedule() — 해당 요일 수업을 시작 시간 기준 오름차순 정렬
- 알고리즘명: 이진 탐색 (Binary Search)
  사용 위치: find_current_schedule_index() — 정렬된 시간표에서 현재 시간의 위치를 탐색
- 알고리즘명: 구간 비교 (Interval Comparison)
  사용 위치: analyze_free_time() — 현재 시간이 수업 중/공강/수업 전후인지 판별

사용 자료구조:
- 자료구조명: 리스트 (List)
  사용 위치: today_classes — 해당 요일 수업 목록 저장 및 정렬
- 자료구조명: 딕셔너리 (Dictionary)
  사용 위치: PLACE_ALIASES — 장소 별칭→표준명 변환 / result — 최종 반환값

입력 데이터:
- current_day: 현재 요일 (str, 예: "월")
- current_time: 현재 시간 (str, HH:MM 형식, 예: "10:30")
- current_place: 현재 위치 (str, 표준 장소명, 예: "AI관")
- timetable: 시간표 데이터 (list, 없으면 샘플 데이터 사용)

출력 데이터:
- is_free_time: 현재 공강 여부 (bool)
- free_minutes: 다음 수업까지 남은 공강 시간 (int, 분 단위)
- current_place: 현재 위치 표준명 (str)
- next_class: 다음 수업 과목명 (str 또는 None)
- next_class_place: 다음 수업 건물 (str 또는 None)
- next_class_start: 다음 수업 시작 시간 (str 또는 None)
- buffer_minutes: 다음 수업 준비 여유 시간 (int, 고정값 10분)
- available_minutes_for_recommendation: 장소 추천에 사용 가능한 시간 (int, 분 단위)
============================================================
"""

import sys
import os

# data 폴더 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
from timetable_data import TIMETABLE, PLACE_ALIASES, STANDARD_BUILDINGS

# 다음 수업 준비 여유 시간 (고정값)
BUFFER_MINUTES = 10


# ============================================================
# 유틸 함수
# ============================================================

def time_to_minutes(time_text):
    """
    HH:MM 형식의 시간 문자열을 분 단위 정수로 변환한다.
    예: "13:30" → 810
    """
    # [자료구조: 리스트] split() 결과를 언패킹하여 시/분 분리
    hour, minute = time_text.strip().split(":")
    return int(hour) * 60 + int(minute)


def minutes_to_time(minutes):
    """
    분 단위 정수를 HH:MM 형식의 시간 문자열로 변환한다.
    예: 810 → "13:30"
    """
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


def normalize_place_name(place_name):
    """
    장소 별칭을 표준 장소명으로 변환한다.
    place_data_v4 엑셀 수업건물 시트 기준 표준명 사용.
    예: "비타" → "비전타워", "공대1" → "공과대학1"
    """
    # [자료구조: 딕셔너리] PLACE_ALIASES 딕셔너리로 O(1) 조회
    return PLACE_ALIASES.get(place_name, place_name)


def normalize_timetable(timetable):
    """
    시간표 데이터의 장소명을 표준 장소명으로 변환한다.
    """
    normalized = []
    for cls in timetable:
        normalized.append({
            "day": cls["day"],
            "start": cls["start"],
            "end": cls["end"],
            "subject": cls["subject"],
            # [자료구조: 딕셔너리] normalize_place_name으로 표준명 변환
            "building": normalize_place_name(cls["building"]),
        })
    return normalized


# ============================================================
# 핵심 함수
# ============================================================

def get_daily_schedule(timetable, day):
    """
    전체 시간표에서 해당 요일 수업만 골라 시작 시간 기준으로 정렬한다.

    [알고리즘: 정렬 알고리즘]
    - 해당 요일 수업 필터링 후 start 시간 기준 오름차순 정렬
    - 시간복잡도: O(n log n)
    """
    # [자료구조: 리스트] 해당 요일 수업만 필터링
    today_classes = [cls for cls in timetable if cls["day"] == day]

    # [알고리즘: 정렬] 시작 시간 기준 오름차순 정렬
    today_classes.sort(key=lambda cls: time_to_minutes(cls["start"]))

    return today_classes


def find_current_schedule_index(daily_schedule, current_minutes):
    """
    정렬된 시간표에서 이진 탐색으로 현재 시간의 위치 인덱스를 찾는다.
    반환값: 현재 시간보다 시작 시간이 큰 첫 번째 수업의 인덱스

    [알고리즘: 이진 탐색 (Binary Search)]
    - 정렬된 수업 리스트에서 현재 시간 기준 위치를 O(log n)에 탐색
    - 시간복잡도: O(log n)
    """
    # [자료구조: 리스트] 이진 탐색 대상 — 정렬된 수업 목록
    left = 0
    right = len(daily_schedule)

    # [알고리즘: 이진 탐색] 현재 시간보다 시작 시간이 큰 첫 번째 수업 인덱스 탐색
    while left < right:
        mid = (left + right) // 2
        if time_to_minutes(daily_schedule[mid]["start"]) <= current_minutes:
            left = mid + 1
        else:
            right = mid

    return left


def find_current_class(daily_schedule, current_minutes):
    """
    현재 시간에 진행 중인 수업을 찾아 반환한다.
    진행 중인 수업이 없으면 None 반환.

    [알고리즘: 구간 비교]
    - 각 수업의 start~end 구간과 현재 시간을 비교
    """
    # [알고리즘: 구간 비교] 수업 시간 구간과 현재 시간 비교
    for cls in daily_schedule:
        start = time_to_minutes(cls["start"])
        end = time_to_minutes(cls["end"])
        if start <= current_minutes < end:
            return cls
    return None


def find_next_class(daily_schedule, current_minutes):
    """
    현재 시간 이후 가장 가까운 다음 수업을 찾아 반환한다.
    다음 수업이 없으면 None 반환.

    [알고리즘: 이진 탐색 활용]
    - find_current_schedule_index()로 얻은 인덱스로 바로 다음 수업 접근
    """
    # [알고리즘: 이진 탐색] 현재 시간 이후 첫 수업 인덱스 찾기
    idx = find_current_schedule_index(daily_schedule, current_minutes)

    for i in range(idx, len(daily_schedule)):
        if time_to_minutes(daily_schedule[i]["start"]) > current_minutes:
            return daily_schedule[i]
    return None


def calculate_free_minutes(current_minutes, next_class_start_str):
    """
    현재 시간부터 다음 수업 시작까지 남은 공강 시간을 분 단위로 계산한다.
    """
    next_start = time_to_minutes(next_class_start_str)
    return max(0, next_start - current_minutes)


def analyze_free_time(daily_schedule, current_minutes, current_place):
    """
    현재 시간 기준으로 수업/공강 상태를 분석하고 결과 딕셔너리를 반환한다.

    [알고리즘: 구간 비교 (Interval Comparison)]
    처리 케이스:
    1. 해당 요일 수업 없음
    2. 첫 수업 시작 전
    3. 수업 중
    4. 수업 사이 공강
    5. 마지막 수업 이후

    [자료구조: 딕셔너리] result — 분석 결과를 key-value 형태로 반환
    """
    # 케이스 1: 해당 요일 수업 없음
    if not daily_schedule:
        return {
            "status": "수업없음",
            "is_free_time": True,
            "free_minutes": 999,
            "current_place": normalize_place_name(current_place),
            "next_class": None,
            "next_class_place": None,
            "next_class_start": None,
            "buffer_minutes": BUFFER_MINUTES,
            "available_minutes_for_recommendation": 999,
        }

    first_start = time_to_minutes(daily_schedule[0]["start"])
    last_end = time_to_minutes(daily_schedule[-1]["end"])

    # [알고리즘: 구간 비교] 현재 수업 진행 여부 확인
    current_class = find_current_class(daily_schedule, current_minutes)

    # 케이스 3: 수업 중
    if current_class is not None:
        # 온라인 수업 중이면 current_place는 입력값 그대로 유지
        if current_class["building"] == "온라인":
            place = normalize_place_name(current_place)
        else:
            place = normalize_place_name(current_class["building"])
        next_cls = find_next_class(daily_schedule, current_minutes)
        return {
            "status": "수업중",
            "is_free_time": False,
            "free_minutes": 0,
            "current_place": place,
            "next_class": next_cls["subject"] if next_cls else None,
            "next_class_place": normalize_place_name(next_cls["building"]) if next_cls else None,
            "next_class_start": next_cls["start"] if next_cls else None,
            "buffer_minutes": BUFFER_MINUTES,
            "available_minutes_for_recommendation": 0,
        }

    # 케이스 2: 첫 수업 시작 전
    if current_minutes < first_start:
        first_class = daily_schedule[0]
        free_minutes = first_start - current_minutes
        available = max(0, free_minutes - BUFFER_MINUTES)
        return {
            "status": "수업전",
            "is_free_time": True,
            "free_minutes": free_minutes,
            "current_place": normalize_place_name(current_place),
            "next_class": first_class["subject"],
            "next_class_place": normalize_place_name(first_class["building"]),
            "next_class_start": first_class["start"],
            "buffer_minutes": BUFFER_MINUTES,
            "available_minutes_for_recommendation": available,
        }

    # 케이스 5: 마지막 수업 이후
    if current_minutes >= last_end:
        last_class = daily_schedule[-1]
        # 온라인 수업이 마지막이면 current_place 입력값 유지
        if last_class["building"] == "온라인":
            place = normalize_place_name(current_place)
        else:
            place = normalize_place_name(last_class["building"])
        return {
            "status": "수업후",
            "is_free_time": True,
            "free_minutes": 999,
            "current_place": place,
            "next_class": None,
            "next_class_place": None,
            "next_class_start": None,
            "buffer_minutes": BUFFER_MINUTES,
            "available_minutes_for_recommendation": 999,
        }

    # 케이스 4: 수업 사이 공강
    # [알고리즘: 이진 탐색] 현재 시간 이후 다음 수업 인덱스 탐색
    next_cls = find_next_class(daily_schedule, current_minutes)

    # 직전 수업 찾기 (현재 시간 이전에 끝난 마지막 수업)
    prev_class = None
    for cls in daily_schedule:
        if time_to_minutes(cls["end"]) <= current_minutes:
            prev_class = cls

    # 직전 수업이 온라인이면 입력받은 위치 사용
    if prev_class and prev_class["building"] != "온라인":
        place = normalize_place_name(prev_class["building"])
    else:
        place = normalize_place_name(current_place)

    free_minutes = calculate_free_minutes(current_minutes, next_cls["start"])
    available = max(0, free_minutes - BUFFER_MINUTES)

    return {
        "status": "공강",
        "is_free_time": True,
        "free_minutes": free_minutes,
        "current_place": place,
        "next_class": next_cls["subject"],
        "next_class_place": normalize_place_name(next_cls["building"]),
        "next_class_start": next_cls["start"],
        "buffer_minutes": BUFFER_MINUTES,
        "available_minutes_for_recommendation": available,
    }


# ============================================================
# 대표 함수 (통합 연동용)
# ============================================================

def analyze_timetable(current_day, current_time, current_place, timetable=None):
    """
    현재 요일/시간/위치를 기준으로 공강 여부와 다음 수업 정보를 계산한다.
    main.py에서 호출하는 대표 함수.

    Args:
        current_day (str): 현재 요일 (예: "월")
        current_time (str): 현재 시간 HH:MM (예: "10:30")
        current_place (str): 현재 위치 장소명 (예: "AI관")
        timetable (list): 시간표 데이터. None이면 샘플 데이터 사용.

    Returns:
        dict: 공강 분석 결과
            - status (str): 수업중 / 공강 / 수업전 / 수업후 / 수업없음
            - is_free_time (bool): 현재 공강 여부
            - free_minutes (int): 다음 수업까지 남은 공강 시간 (분)
            - current_place (str): 현재 위치 표준명
            - next_class (str|None): 다음 수업 과목명
            - next_class_place (str|None): 다음 수업 건물
            - next_class_start (str|None): 다음 수업 시작 시간
            - buffer_minutes (int): 다음 수업 준비 여유 시간 (고정 10분)
            - available_minutes_for_recommendation (int): 장소 추천 가능 시간
    """
    if timetable is None:
        timetable = TIMETABLE

    # 시간표 장소명 표준화
    timetable = normalize_timetable(timetable)

    # 현재 시간을 분 단위로 변환
    current_minutes = time_to_minutes(current_time)

    # [알고리즘: 정렬] 해당 요일 수업 목록 정렬
    daily_schedule = get_daily_schedule(timetable, current_day)

    # [알고리즘: 이진 탐색 + 구간 비교] 공강 구간 분석
    result = analyze_free_time(daily_schedule, current_minutes, current_place)

    return result


# ============================================================
# 단독 실행 예시
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("시간표/공강시간 분석 모듈 — 단독 실행 테스트")
    print("=" * 60)

    def print_result(result):
        print(f"  상태               : {result['status']}")
        print(f"  공강 여부          : {result['is_free_time']}")
        print(f"  남은 공강 시간     : {result['free_minutes']}분")
        print(f"  현재 위치          : {result['current_place']}")
        print(f"  다음 수업          : {result['next_class']}")
        print(f"  다음 수업 장소     : {result['next_class_place']}")
        print(f"  다음 수업 시작     : {result['next_class_start']}")
        print(f"  여유 시간(buffer)  : {result['buffer_minutes']}분")
        print(f"  추천 가능 시간     : {result['available_minutes_for_recommendation']}분")

    # ── 케이스 1: 공강 중 (수 10:30, 웹프로그래밍 끝 → 운영체제 전, 가천관)
    print("\n[ 케이스 1 ] 공강 중")
    print("  입력: 수요일 10:30, 현재 위치 가천관")
    print_result(analyze_timetable("수", "10:30", "가천관"))

    # ── 케이스 2: 수업 중 (화 10:00, 자료구조 연강 중간, 가천관)
    print("\n[ 케이스 2 ] 수업 중 (연강 중간)")
    print("  입력: 화요일 10:00, 현재 위치 가천관")
    print_result(analyze_timetable("화", "10:00", "가천관"))

    # ── 케이스 3: 첫 수업 전 (목 08:30, 공과대학1)
    print("\n[ 케이스 3 ] 첫 수업 전")
    print("  입력: 목요일 08:30, 현재 위치 공과대학1")
    print_result(analyze_timetable("목", "08:30", "공과대학1"))

    # ── 케이스 4: 마지막 수업 후 (목 16:30, 가천관)
    print("\n[ 케이스 4 ] 마지막 수업 후")
    print("  입력: 목요일 16:30, 현재 위치 가천관")
    print_result(analyze_timetable("목", "16:30", "가천관"))

    # ── 케이스 5: 수업 없는 요일 (토 12:00, 중앙도서관)
    print("\n[ 케이스 5 ] 수업 없는 요일")
    print("  입력: 토요일 12:00, 현재 위치 중앙도서관")
    print_result(analyze_timetable("토", "12:00", "중앙도서관"))

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
