"""
============================================================
파일명: place_recommender.py
기능명: 장소 추천 순위 계산
담당자: 강서현

기능 요약:
- 시간표/공강 분석 결과에서 공강 시간(free_minutes)을 받는다.
- 최단경로 계산 결과에서 후보 장소별 이동시간과 경로를 받는다.
- 혼잡도/대기시간 계산 결과에서 후보 장소별 혼잡도와 대기시간을 받는다.
- 공강 시간 안에 이용 가능한 장소를 필터링한다.
- 이동시간, 대기시간, 혼잡도, 장소 선호점수를 가중합 모델로 계산한다.
- 추천 점수 기준으로 정렬하여 장소 추천 순위를 반환한다.

사용 자료구조:
- 해시 테이블(dict): 장소 정보, 경로 결과, 혼잡도 결과를 장소명으로 조회한다.
- 동적 배열(list): 추천 후보와 최종 추천 결과를 저장하고 정렬한다.

사용 알고리즘:
- 선형 탐색: 추천 후보 장소를 하나씩 확인한다.
- 필터링 알고리즘: 공강 시간 안에 이용 가능한 장소인지 판단한다.
- 가중합 모델: 이동시간, 대기시간, 혼잡도, 선호점수를 합산해 점수를 계산한다.
- 정렬 알고리즘: 추천 점수가 높은 순서로 결과를 정렬한다.

핵심 알고리즘:
- 가중합 모델(Weighted Sum Model)

대표 함수:
- recommend_places(free_time_result, path_results, crowd_results, places=None)

주의:
- main.py에서 recommend_places()와 print_recommendations()를 호출해 통합 실행한다.
============================================================
"""

from data.place_data import (
    FOOD_CAFE_CANDIDATES,
    RECOMMENDATION_EVIDENCE,
    get_recommendation_places,
    normalize_place_name,
)


DEFAULT_CROWD_LEVEL = 50
DEFAULT_WAIT_MINUTES = 5
TOP_RECOMMENDATION_COUNT = 3

CROWD_LEVEL_SCORES = {
    "여유": 25,
    "낮음": 30,
    "보통": 50,
    "혼잡": 70,
    "매우혼잡": 90,
    "매우 혼잡": 90,
    "정보없음": DEFAULT_CROWD_LEVEL,
}


# 사용자 목적을 엑셀 추천 데이터의 태그/장소명과 연결하기 위한 딕셔너리이다.
PURPOSE_KEYWORDS = {
    "공부": ["study", "공부", "학습", "열람실", "아르테크네"],
    "팀플": ["team_project", "팀플", "카페", "스타벅스", "라운지"],
    "회의": ["team_project", "meeting", "회의", "카페", "스타벅스", "라운지"],
    "휴식": ["rest", "휴식", "라운지", "광장", "아르테크네"],
    "공강": ["waiting", "공강", "대기", "아르테크네", "라운지"],
    "공강대기": ["waiting", "공강", "대기", "아르테크네", "라운지"],
    "식사": ["food", "식사", "식당"],
    "밥": ["food", "식사", "식당"],
    "카페": ["cafe", "카페", "커피", "스타벅스"],
    "커피": ["cafe", "카페", "커피", "스타벅스"],
    "프린트": ["print", "프린트", "프린터"],
    "편의점": ["convenience_store", "편의점"],
}

FOOD_CAFE_PATH_NODE_OVERRIDES = {
    "포밥인뉴욕 가천대점": "비전타워",
    "치미치미 부리또": "비전타워",
    "신의한컵": "비전타워",
    "쩡이떡볶이": "비전타워",
    "차이나스푼": "비전타워",
    "1209 가천대점": "비전타워",
    "던킨도너츠": "비전타워",
    "파스쿠찌/파스쿠치 계열 가천대점": "스타덤광장",
    "리플커피": "비전타워",
}

FOOD_CAFE_NAME_OVERRIDES = {
    "파스쿠찌/파스쿠치 계열 가천대점": "파스쿠찌",
}

INDEPENDENT_SAME_BUILDING_KEYWORDS = (
    "식당",
    "카페",
    "커피",
    "간식",
    "프린트",
    "편의점",
    "스타벅스",
    "투썸",
    "VVCZ",
    "1209",
    "던킨",
    "파스쿠찌",
    "리플커피",
    "포밥",
    "부리또",
    "신의한컵",
    "떡볶이",
    "차이나스푼",
)


def safe_int(value, default=0):
    """숫자로 변환할 수 없는 값이 들어와도 프로그램이 중단되지 않도록 처리한다."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_places(places=None):
    """장소 데이터가 없으면 엑셀 기반 추천 장소 데이터를 불러온다."""
    if places is None:
        return get_recommendation_places(include_support=False)

    if isinstance(places, dict):
        return places

    return {}


def get_food_cafe_tags(candidate_type):
    """식당/카페 후보 유형을 추천 필터링 태그로 변환한다."""
    candidate_type = candidate_type or ""
    tags = []

    if "식당" in candidate_type:
        tags.extend(["food", "식사", "식당"])
    if "카페" in candidate_type or "간식" in candidate_type:
        tags.extend(["cafe", "카페"])

    return tags


def get_food_cafe_min_stay_minutes(candidate_type):
    """후보 유형별 최소 이용 시간을 정한다."""
    candidate_type = candidate_type or ""
    if "식당" in candidate_type:
        return 30
    return 20


def convert_food_cafe_candidate(candidate):
    """후보 시트의 식당/카페 항목을 추천 후보 형식으로 변환한다."""
    candidate_name = candidate.get("candidate_name", "")
    if not candidate_name or candidate.get("check_status") == "기반영":
        return None, None

    path_node = FOOD_CAFE_PATH_NODE_OVERRIDES.get(
        candidate_name,
        candidate.get("path_node", ""),
    )
    if not path_node or "/" in path_node:
        return None, None

    display_name = FOOD_CAFE_NAME_OVERRIDES.get(candidate_name, candidate_name)
    candidate_type = candidate.get("type", "")
    tags = get_food_cafe_tags(candidate_type)

    if not tags:
        return None, None

    place_info = {
        "place": display_name,
        "type": candidate_type,
        "recommendation_type": candidate_type,
        "recommendation_tags": tags,
        "path_node": path_node,
        "detail_location": candidate.get("detail_location", path_node),
        "min_stay_minutes": get_food_cafe_min_stay_minutes(candidate_type),
        "preference_score": 6,
        "needs_crowd": True,
        "needs_wait": True,
        "source_note": candidate.get("source_note", ""),
        "status": "사용가능",
        "note": "식당/카페 후보 목록을 장소추천 계산용으로 변환",
    }

    return display_name, place_info


def extend_places_with_food_cafe_candidates(places):
    """기존 장소 데이터에 식당/카페 후보를 추가한다."""
    extended_places = dict(places)

    for candidate in FOOD_CAFE_CANDIDATES:
        place, place_info = convert_food_cafe_candidate(candidate)
        if place and place not in extended_places:
            extended_places[place] = place_info

    return extended_places


def is_artechne_place(place, place_info=None):
    """아르테크네 계열 장소인지 확인한다."""
    if "아르테크네" in place:
        return True

    if not isinstance(place_info, dict):
        return False

    check_text = " ".join(
        str(place_info.get(key, ""))
        for key in ("source_note", "note", "detail_location")
    )
    return "아르테크네" in check_text


def is_team_project_purpose(user_purpose):
    """사용자 목적이 팀플/회의처럼 대화가 많은 활동인지 확인한다."""
    return (user_purpose or "").strip() in {"팀플", "회의", "모임"}


def get_display_place_type(place, place_info):
    """추천 출력용 장소 유형을 반환한다."""
    if is_artechne_place(place, place_info):
        return "공부/조용한 휴식/공강 대기"

    return place_info.get("recommendation_type", "")


def get_user_purpose(free_time_result):
    """free_time_result에서 사용자 목적을 꺼낸다."""
    if not isinstance(free_time_result, dict):
        return ""

    return (
        free_time_result.get("user_purpose")
        or free_time_result.get("purpose")
        or free_time_result.get("activity_purpose")
        or ""
    )


def get_free_minutes(free_time_result):
    """추천 계산에 사용할 공강 시간을 가져온다.

    시간표 기능에서 다음 수업 준비 시간을 뺀 available_minutes_for_recommendation을
    제공하면 그 값을 우선 사용하고, 없으면 free_minutes를 사용한다.
    """
    if not isinstance(free_time_result, dict):
        return 0

    if free_time_result.get("available_minutes_for_recommendation") is not None:
        return safe_int(free_time_result.get("available_minutes_for_recommendation"), 0)

    return safe_int(free_time_result.get("free_minutes"), 0)


def get_user_keywords(user_purpose):
    """사용자 목적을 후보 장소 검색에 사용할 키워드 목록으로 바꾼다."""
    user_purpose = (user_purpose or "").strip()
    standard_purpose = normalize_place_name(user_purpose)

    if standard_purpose == "":
        return []

    if standard_purpose in PURPOSE_KEYWORDS:
        return PURPOSE_KEYWORDS[standard_purpose]

    return [standard_purpose]


def filter_places_by_purpose(user_purpose, places):
    """사용자 목적에 맞는 장소 후보만 남긴다."""
    keywords = get_user_keywords(user_purpose)
    if not keywords:
        return places

    filtered_places = {}

    # 자료구조(dict): 장소명을 key로 하여 필터링된 추천 후보를 저장한다.
    # 알고리즘(선형 탐색): 후보 장소를 하나씩 확인하면서 사용자 목적과 맞는지 검사한다.
    for place, place_info in places.items():
        if is_team_project_purpose(user_purpose) and is_artechne_place(place, place_info):
            continue

        recommendation_tags = list(place_info.get("recommendation_tags", []))
        if is_artechne_place(place, place_info) and "team_project" in recommendation_tags:
            recommendation_tags.remove("team_project")
            recommendation_tags.extend(["quiet_rest", "waiting"])

        searchable_values = [
            place,
            get_display_place_type(place, place_info),
            place_info.get("detail_location", ""),
            place_info.get("path_node", ""),
        ]
        searchable_values.extend(recommendation_tags)
        searchable_text = " ".join(str(value) for value in searchable_values)

        for keyword in keywords:
            if keyword and keyword in searchable_text:
                filtered_places[place] = place_info
                break

    if filtered_places:
        return filtered_places

    if is_team_project_purpose(user_purpose):
        return {}

    return places


def get_path_result(place, place_info, path_results):
    """장소명으로 먼저 찾고, 없으면 대표 위치(path_node) 기준으로 경로 결과를 찾는다."""
    if not isinstance(path_results, dict):
        return {}

    path_node = place_info.get("path_node", place)

    if place in path_results:
        return path_results[place]

    if path_node in path_results:
        return path_results[path_node]

    return {}


def get_travel_minutes(path_result):
    """최단경로 결과에서 이동시간을 가져온다."""
    if not isinstance(path_result, dict):
        return None

    travel_minutes = path_result.get("travel_minutes")
    if travel_minutes is None:
        travel_minutes = path_result.get("total_travel_minutes")
    if travel_minutes is None:
        from_current = path_result.get("from_current_minutes")
        to_next_class = path_result.get("to_next_class_minutes")
        if from_current is not None and to_next_class is not None:
            return safe_int(from_current, 0) + safe_int(to_next_class, 0)

    return safe_int(travel_minutes, None)


def is_path_reachable(path_result):
    """최단경로 결과에서 도달 가능 여부를 확인한다."""
    if not isinstance(path_result, dict):
        return False

    reachable = path_result.get("reachable")
    if reachable is None:
        return True

    if isinstance(reachable, str):
        return reachable.strip().lower() not in {
            "false",
            "0",
            "no",
            "n",
            "불가능",
            "도달불가",
        }

    return bool(reachable)


def get_crowd_result(place, place_info, crowd_results):
    """장소명으로 먼저 찾고, 없으면 대표 위치(path_node) 기준으로 혼잡도 결과를 찾는다."""
    if not isinstance(crowd_results, dict):
        return {}

    path_node = place_info.get("path_node", place)

    if place in crowd_results:
        return crowd_results[place]

    if path_node in crowd_results:
        return crowd_results[path_node]

    return {}


def get_numeric_crowd_level(crowd_level):
    """혼잡도를 숫자 점수로 변환한다."""
    if isinstance(crowd_level, str):
        label = crowd_level.strip()
        if label in CROWD_LEVEL_SCORES:
            return CROWD_LEVEL_SCORES[label]
        label_without_space = label.replace(" ", "")
        if label_without_space in CROWD_LEVEL_SCORES:
            return CROWD_LEVEL_SCORES[label_without_space]

    return safe_int(crowd_level, DEFAULT_CROWD_LEVEL)


def get_crowd_info(crowd_result):
    """혼잡도 결과가 없거나 일부 값이 비어 있으면 기본값을 사용한다."""
    if not isinstance(crowd_result, dict):
        crowd_result = {}

    crowd_level = get_numeric_crowd_level(crowd_result.get("crowd_level"))
    expected_wait_minutes = safe_int(
        crowd_result.get("expected_wait_minutes"),
        DEFAULT_WAIT_MINUTES,
    )

    return crowd_level, expected_wait_minutes


def calculate_total_needed_minutes(travel_minutes, expected_wait_minutes, min_stay_minutes):
    """공강 시간 안에 이용 가능한지 판단하기 위한 전체 필요 시간을 계산한다."""
    return travel_minutes + expected_wait_minutes + min_stay_minutes


def filter_available_places(free_minutes, path_results, crowd_results, places=None):
    """공강 시간 안에 이용 가능한 장소인지 판단한다."""
    places = normalize_places(places)
    free_minutes = safe_int(free_minutes, 0)
    available_places = {}

    # 알고리즘(필터링): 이동 + 대기 + 최소 이용 시간이 공강 시간 안에 들어가는지 검사한다.
    for place, place_info in places.items():
        path_result = get_path_result(place, place_info, path_results)
        travel_minutes = get_travel_minutes(path_result)
        shortest_path = path_result.get("shortest_path", [])

        crowd_result = get_crowd_result(place, place_info, crowd_results)
        crowd_level, expected_wait_minutes = get_crowd_info(crowd_result)
        min_stay_minutes = safe_int(place_info.get("min_stay_minutes"), 0)

        available = True
        unavailable_reason = ""
        total_needed_minutes = None

        if not is_path_reachable(path_result):
            available = False
            unavailable_reason = "최단경로 계산 결과에서 도달 불가능한 장소로 표시되었습니다."
        elif travel_minutes is None:
            available = False
            unavailable_reason = "최단경로 계산 결과가 없어 추천에서 제외했습니다."
        else:
            total_needed_minutes = calculate_total_needed_minutes(
                travel_minutes,
                expected_wait_minutes,
                min_stay_minutes,
            )
            if total_needed_minutes > free_minutes:
                available = False
                unavailable_reason = "이동시간, 대기시간, 최소 이용 시간을 합치면 공강 시간을 초과합니다."

        available_places[place] = {
            "available": available,
            "unavailable_reason": unavailable_reason,
            "travel_minutes": travel_minutes,
            "total_travel_minutes": travel_minutes,
            "shortest_path": shortest_path,
            "expected_wait_minutes": expected_wait_minutes,
            "crowd_level": crowd_level,
            "min_stay_minutes": min_stay_minutes,
            "total_needed_minutes": total_needed_minutes,
        }

    return available_places


def calculate_recommendation_score(
    travel_minutes,
    expected_wait_minutes,
    crowd_level,
    preference_score=0,
):
    """가중합 모델로 추천 점수를 계산한다."""
    score_detail = calculate_score_detail(
        travel_minutes,
        expected_wait_minutes,
        crowd_level,
        preference_score,
    )

    return score_detail["total"]


def calculate_score_detail(
    travel_minutes,
    expected_wait_minutes,
    crowd_level,
    preference_score=0,
):
    """추천 점수를 구성하는 세부 항목을 계산한다."""
    travel_minutes = safe_int(travel_minutes, 999)
    expected_wait_minutes = safe_int(expected_wait_minutes, 999)
    crowd_level = safe_int(crowd_level, DEFAULT_CROWD_LEVEL)
    preference_score = safe_int(preference_score, 0)

    # 핵심 알고리즘(가중합 모델):
    # 이동시간, 대기시간, 혼잡도는 낮을수록 좋은 점수를 주고 선호점수는 보너스로 더한다.
    travel_score = max(0, 40 - travel_minutes)
    wait_score = max(0, 25 - (expected_wait_minutes * 2))
    crowd_score = max(0, 20 - (crowd_level // 5))
    preference_bonus = min(15, preference_score)

    return {
        "travel": travel_score,
        "wait": wait_score,
        "crowd": crowd_score,
        "preference": preference_bonus,
        "total": travel_score + wait_score + crowd_score + preference_bonus,
    }


def get_crowd_level_label(crowd_level):
    """혼잡도 숫자 점수를 사용자가 이해하기 쉬운 라벨로 바꾼다."""
    labels = {
        1: "매우 여유",
        2: "여유",
        3: "보통",
        4: "혼잡",
        5: "매우 혼잡",
    }
    return labels.get(safe_int(crowd_level, DEFAULT_CROWD_LEVEL), "보통")


def format_place_location(recommendation):
    """대표 위치와 세부 위치를 한 줄로 표시한다."""
    path_node = recommendation.get("path_node") or recommendation.get("place", "")
    detail_location = recommendation.get("detail_location") or ""

    if detail_location and detail_location != path_node:
        return f"{path_node}({detail_location})"
    return path_node


def format_score_detail(score_detail):
    """점수 구성 dict를 출력용 문자열로 만든다."""
    if not isinstance(score_detail, dict):
        return ""

    return (
        f"이동 {score_detail.get('travel', 0)}점 + "
        f"대기 {score_detail.get('wait', 0)}점 + "
        f"혼잡 {score_detail.get('crowd', 0)}점 + "
        f"선호 {score_detail.get('preference', 0)}점 = "
        f"{score_detail.get('total', 0)}점"
    )


def format_time_usage(recommendation):
    """공강 시간 중 추천 장소 이용에 필요한 시간을 요약한다."""
    total_needed_minutes = recommendation.get("total_needed_minutes")
    total_free_minutes = recommendation.get("total_free_minutes")
    recommendation_free_minutes = recommendation.get("recommendation_free_minutes")

    if total_needed_minutes is None:
        return "소요시간 확인 필요"
    if total_free_minutes:
        return f"공강시간 {total_free_minutes}분 중 {total_needed_minutes}분 사용"
    if recommendation_free_minutes:
        return f"추천 기준 {recommendation_free_minutes}분 중 {total_needed_minutes}분 사용"
    return f"총 {total_needed_minutes}분 사용"


def build_user_friendly_reason(recommendation):
    """콘솔 출력용 짧은 추천 이유를 만든다."""
    if not recommendation.get("available"):
        return recommendation.get("reason", "이용 조건을 만족하지 못했습니다.")

    travel_minutes = safe_int(recommendation.get("travel_minutes"), 0)
    expected_wait_minutes = safe_int(recommendation.get("expected_wait_minutes"), 0)

    if travel_minutes <= 10:
        movement_text = "현재 위치와 다음 수업 장소 기준 이동 부담이 작습니다"
    else:
        movement_text = "공강 시간 안에서 이동 가능한 동선입니다"

    if expected_wait_minutes == 0:
        wait_text = "대기시간이 없어 바로 이용하기 좋습니다"
    else:
        wait_text = f"예상 대기시간은 {expected_wait_minutes}분입니다"

    return f"{movement_text}. {wait_text}."


def build_recommendation_reason(
    place,
    travel_minutes,
    expected_wait_minutes,
    crowd_level,
    place_info=None,
    total_needed_minutes=None,
):
    """추천 이유를 설명 문장으로 만든다."""
    place_info = place_info if isinstance(place_info, dict) else {}
    path_node = place_info.get("path_node", place)
    detail_location = place_info.get("detail_location", "")
    min_stay_minutes = safe_int(place_info.get("min_stay_minutes"), 0)
    preference_score = safe_int(place_info.get("preference_score"), 0)
    display_place_type = get_display_place_type(place, place_info)

    if total_needed_minutes is None and travel_minutes is not None:
        total_needed_minutes = calculate_total_needed_minutes(
            travel_minutes,
            expected_wait_minutes,
            min_stay_minutes,
        )

    return (
        f"{place}은(는) {display_place_type} 목적에 맞습니다. "
        f"대표 위치는 {path_node}, 세부 위치는 {detail_location}입니다. "
        f"이동 {travel_minutes}분, 대기 {expected_wait_minutes}분, "
        f"최소 이용 {min_stay_minutes}분으로 총 {total_needed_minutes}분이 필요합니다. "
        f"혼잡도 {crowd_level}점과 선호점수 {preference_score}점을 반영했습니다."
    )


def build_recommendation_result(
    place,
    place_info,
    score,
    reason,
    available_info,
):
    """최종 추천 결과 dict를 만든다."""
    detail_location = place_info.get("detail_location", "")
    preference_score = safe_int(place_info.get("preference_score"), 0)
    if available_info["available"]:
        score_detail = calculate_score_detail(
            available_info["travel_minutes"],
            available_info["expected_wait_minutes"],
            available_info["crowd_level"],
            preference_score,
        )
    else:
        score_detail = {
            "travel": 0,
            "wait": 0,
            "crowd": 0,
            "preference": 0,
            "total": 0,
        }

    return {
        "rank": 0,
        "place": place,
        "type": get_display_place_type(place, place_info),
        "path_node": place_info.get("path_node", place),
        "detail_location": detail_location,
        "score": score,
        "score_detail": score_detail,
        "reason": reason,
        "travel_minutes": available_info["travel_minutes"],
        "total_travel_minutes": available_info["total_travel_minutes"],
        "shortest_path": available_info["shortest_path"],
        "expected_wait_minutes": available_info["expected_wait_minutes"],
        "crowd_level": available_info["crowd_level"],
        "crowd_label": get_crowd_level_label(available_info["crowd_level"]),
        "min_stay_minutes": available_info["min_stay_minutes"],
        "total_needed_minutes": available_info["total_needed_minutes"],
        "available": available_info["available"],
        "evidence": RECOMMENDATION_EVIDENCE.get(place, {}),
    }


def sort_recommendations(recommendations):
    """추천 결과를 이용 가능 여부와 점수 기준으로 정렬한다."""
    # 알고리즘(정렬): 이용 가능한 장소를 먼저 두고, 점수가 높은 장소를 앞에 배치한다.
    return sorted(
        recommendations,
        key=lambda item: (
            not item["available"],
            -item["score"],
            item["travel_minutes"] is None,
            item["travel_minutes"] or 999,
            item["place"],
        ),
    )


def is_independent_same_building_place(recommendation):
    """같은 건물 안에서도 별도 장소로 보여줄 유형인지 확인한다."""
    check_text = " ".join(
        str(recommendation.get(key, ""))
        for key in ("place", "type", "detail_location")
    )
    return any(keyword in check_text for keyword in INDEPENDENT_SAME_BUILDING_KEYWORDS)


def add_grouped_place(base_recommendation, recommendation):
    """같은 건물의 유사한 공부/휴식 장소를 하나의 추천 카드로 묶는다."""
    grouped_places = base_recommendation.setdefault(
        "grouped_places",
        [base_recommendation.get("place", "")],
    )
    place = recommendation.get("place", "")

    if place and place not in grouped_places:
        grouped_places.append(place)

    base_recommendation["place"] = " / ".join(grouped_places)
    base_recommendation["reason"] = (
        "같은 건물의 유사한 공부/휴식 장소를 한 추천으로 묶었습니다. "
        + base_recommendation.get("reason", "")
    )


def group_similar_recommendations_by_path_node(recommendations):
    """식당 등 별도 장소는 유지하고, 공부/휴식류만 같은 건물 기준으로 묶는다."""
    grouped_recommendations = []
    group_index_by_path_node = {}

    for recommendation in recommendations:
        path_node = recommendation.get("path_node") or recommendation.get("place")

        if is_independent_same_building_place(recommendation):
            grouped_recommendations.append(recommendation)
            continue

        if path_node in group_index_by_path_node:
            base_index = group_index_by_path_node[path_node]
            add_grouped_place(grouped_recommendations[base_index], recommendation)
            continue

        group_index_by_path_node[path_node] = len(grouped_recommendations)
        grouped_recommendations.append(recommendation)

    return grouped_recommendations


def recommend_places(free_time_result, path_results, crowd_results, places=None):
    """장소 추천 순위를 계산해 list[dict] 형태로 반환하는 대표 함수이다."""
    free_time_result = free_time_result if isinstance(free_time_result, dict) else {}
    places = normalize_places(places)
    places = extend_places_with_food_cafe_candidates(places)

    user_purpose = get_user_purpose(free_time_result)
    free_minutes = get_free_minutes(free_time_result)

    candidate_places = filter_places_by_purpose(user_purpose, places)
    available_places = filter_available_places(
        free_minutes,
        path_results,
        crowd_results,
        candidate_places,
    )
    recommendations = []

    # 자료구조(list): 최종 추천 결과를 저장한다.
    # 알고리즘(선형 탐색): 후보 장소를 하나씩 확인하며 점수와 추천 이유를 만든다.
    for place, place_info in candidate_places.items():
        available_info = available_places[place]

        if not available_info["available"]:
            recommendations.append(
                build_recommendation_result(
                    place,
                    place_info,
                    0,
                    available_info["unavailable_reason"],
                    available_info,
                )
            )
            continue

        preference_score = safe_int(place_info.get("preference_score"), 0)
        score = calculate_recommendation_score(
            available_info["travel_minutes"],
            available_info["expected_wait_minutes"],
            available_info["crowd_level"],
            preference_score,
        )
        reason = build_recommendation_reason(
            place,
            available_info["travel_minutes"],
            available_info["expected_wait_minutes"],
            available_info["crowd_level"],
            place_info,
            available_info["total_needed_minutes"],
        )
        recommendations.append(
            build_recommendation_result(
                place,
                place_info,
                score,
                reason,
                available_info,
            )
        )

    sorted_recommendations = sort_recommendations(recommendations)
    grouped_recommendations = group_similar_recommendations_by_path_node(sorted_recommendations)
    top_recommendations = grouped_recommendations[:TOP_RECOMMENDATION_COUNT]
    total_free_minutes = safe_int(free_time_result.get("free_minutes"), free_minutes)
    buffer_minutes = safe_int(free_time_result.get("buffer_minutes"), 0)

    for rank, recommendation in enumerate(top_recommendations, start=1):
        recommendation["rank"] = rank
        recommendation["total_free_minutes"] = total_free_minutes
        recommendation["recommendation_free_minutes"] = free_minutes
        recommendation["buffer_minutes"] = buffer_minutes
        recommendation["current_place"] = free_time_result.get("current_place", "")
        recommendation["next_class_place"] = free_time_result.get("next_class_place", "")
        recommendation["next_class_start"] = free_time_result.get("next_class_start", "")

    return top_recommendations


def print_recommendations(recommendations):
    """단독 실행 결과를 보기 좋게 출력한다."""
    print("장소 추천 순위 계산 결과")
    print("=" * 70)

    if not recommendations:
        print("추천 가능한 장소가 없습니다.")
        return

    first_recommendation = recommendations[0]
    total_free_minutes = first_recommendation.get("total_free_minutes")
    recommendation_free_minutes = first_recommendation.get("recommendation_free_minutes")
    buffer_minutes = first_recommendation.get("buffer_minutes", 0)

    print("[공강 시간]")
    if total_free_minutes is not None:
        print(f"전체 공강시간: {total_free_minutes}분")
    if recommendation_free_minutes is not None:
        if buffer_minutes:
            print(
                f"추천 계산 기준 시간: {recommendation_free_minutes}분 "
                f"(다음 수업 준비/이동 여유 {buffer_minutes}분 제외)"
            )
        else:
            print(f"추천 계산 기준 시간: {recommendation_free_minutes}분")
    print()
    print("[혼잡도/대기시간 기준]")
    print("혼잡도: 1점 매우 여유 | 2점 여유 | 3점 보통 | 4점 혼잡 | 5점 매우 혼잡")
    print("대기시간: 식당 0/3/7/12/18분, 카페 0/2/5/9/14분, 기타 0/2/5/8/12분")
    print("대기시간 계산이 필요 없는 장소는 0분으로 처리합니다.")

    for recommendation in recommendations:
        print()
        available_text = "가능" if recommendation["available"] else "불가능"
        crowd_label = recommendation.get("crowd_label") or get_crowd_level_label(
            recommendation.get("crowd_level")
        )
        print(
            f"{recommendation['rank']}위 | {recommendation['place']}({recommendation['score']}점) | "
            f"이용 {available_text} | {format_time_usage(recommendation)}"
        )
        print(f"  위치: {format_place_location(recommendation)}")
        print(
            f"  소요 시간: 이동 {recommendation['travel_minutes']}분 + "
            f"대기 {recommendation['expected_wait_minutes']}분 + "
            f"최소 이용 {recommendation['min_stay_minutes']}분 = "
            f"총 {recommendation['total_needed_minutes']}분"
        )
        print(f"  혼잡도: {recommendation['crowd_level']}점({crowd_label})")
        if recommendation.get("shortest_path"):
            print(f"  경로: {' -> '.join(recommendation['shortest_path'])}")
        print(f"  점수 구성: {format_score_detail(recommendation.get('score_detail'))}")
        print(f"  추천 이유: {build_user_friendly_reason(recommendation)}")
