"""
학교 생활 맞춤형 시간표·동선 추천 서비스 통합 실행본.

반영 파일:
- timetable_analyzer.py: 시간표/공강시간 분석
- path_finder.py: 최단경로 계산
- crowd_analyzer.py: 혼잡도/대기시간 계산
- place_recommender.py: 장소 추천 순위 계산
- path_visualizer.py: campus_path.html 경로 시각화
- data/*.py: 시간표, 그래프, 장소, 혼잡도 의존 데이터
"""

from crowd_analyzer import analyze_crowd
from data.place_data import get_recommendation_places
from path_finder import find_shortest_paths
from path_visualizer import visualize_path
from place_recommender import print_recommendations, recommend_places
from timetable_analyzer import analyze_timetable


def get_candidate_path_nodes(places):
    """추천 후보 장소에서 최단경로 계산에 사용할 대표 노드 목록을 만든다."""
    path_nodes = []
    for place, place_info in places.items():
        path_node = place_info.get("path_node", place)
        if path_node not in path_nodes:
            path_nodes.append(path_node)
    return path_nodes


def convert_path_results_to_dict(path_results):
    """path_finder의 list 결과를 place_recommender가 조회하기 쉬운 dict로 변환한다."""
    converted = {}

    for item in path_results:
        place = item["place"]
        converted[place] = {
            **item,
            "travel_minutes": item.get("total_travel_minutes"),
            "shortest_path": item.get("full_path", []),
            "reachable": item.get("is_reachable", False),
        }

    return converted


def convert_crowd_results_to_dict(crowd_results, candidate_places):
    """crowd_analyzer의 list 결과를 추천 후보명과 표준명 양쪽으로 조회 가능하게 변환한다."""
    converted = {}

    for index, item in enumerate(crowd_results):
        converted[item["place"]] = item
        if index < len(candidate_places):
            converted[candidate_places[index]] = item

    return converted


def print_section(title):
    """통합 실행 결과를 단계별로 구분해서 출력한다."""
    print("\n" + title)
    print("-" * 70)


def run_prototype(current_day, current_time, current_place, user_purpose="공부"):
    """전체 기능을 순서대로 실행하고 최종 추천 결과를 반환한다."""
    print("=" * 70)
    print("학교 생활 맞춤형 시간표·동선 추천 서비스 통합 실행")
    print("=" * 70)
    print(f"입력 요일       : {current_day}")
    print(f"입력 시간       : {current_time}")
    print(f"현재 위치       : {current_place}")
    print(f"사용자 목적     : {user_purpose}")
    print("=" * 70)

    free_time_result = analyze_timetable(current_day, current_time, current_place)
    free_time_result["user_purpose"] = user_purpose

    print_section("[1] 시간표/공강 시간 분석 결과")
    print(free_time_result)

    if not free_time_result.get("is_free_time"):
        print("\n현재는 공강 시간이 아니므로 장소 추천을 실행하지 않습니다.")
        return []

    places = get_recommendation_places(include_support=False)
    candidate_places = list(places.keys())
    candidate_path_nodes = get_candidate_path_nodes(places)
    next_class_place = free_time_result.get("next_class_place") or free_time_result["current_place"]

    path_results_list = find_shortest_paths(
        free_time_result["current_place"],
        next_class_place,
        candidate_path_nodes,
    )
    path_results = convert_path_results_to_dict(path_results_list)

    print_section("[2] 최단경로 계산 결과")
    for item in path_results_list:
        if item["is_reachable"]:
            go = " → ".join(item["go_path"])
            ret = " → ".join(item["return_path"])
            print(f"  경유지: {item['place']}")
            print(f"    가는 길:      {go} ({item['go_minutes']}분)")
            print(f"    돌아오는 길:  {ret} ({item['return_minutes']}분)")
            print(f"    총 이동시간:  {item['total_travel_minutes']}분")
            print()
        else:
            print(f"  [{item['place']}] 경로 없음\n")

    crowd_results_list = analyze_crowd(current_time, candidate_places)
    crowd_results = convert_crowd_results_to_dict(crowd_results_list, candidate_places)

    print_section("[3] 혼잡도/대기시간 계산 결과")
    for item in crowd_results_list:
        print(item)

    recommendations = recommend_places(
        free_time_result,
        path_results,
        crowd_results,
        places,
    )

    print_section("[4] 장소 추천 순위 계산 결과")
    print_recommendations(recommendations)

    print_section("[5] 경로 시각화 결과")
    visualize_path(
        free_time_result["current_place"],
        next_class_place,
        candidate_path_nodes,
        result=path_results_list,
    )

    return recommendations


def main():
    """프로그램 시작점 함수."""
    run_prototype(
        current_day="수", 
        current_time="10:30",
        current_place="가천관", 
        user_purpose="공부", 
    )


if __name__ == "__main__":
    main()
