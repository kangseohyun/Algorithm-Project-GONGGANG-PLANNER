"""
============================================================
기능명: 최단경로 계산
담당자: 전병호

핵심 기능:
- 현재 위치에서 후보 장소까지의 최단 이동경로와 이동시간 계산
- 후보 장소에서 다음 수업 장소까지의 최단 이동경로와 이동시간 계산

사용 알고리즘:
- 알고리즘명: 다익스트라 (Dijkstra)
  사용 위치: dijkstra() 함수
- 알고리즘명: 경로 복원 (Backtracking)
  사용 위치: reconstruct_path() 함수

사용 자료구조:
- 자료구조명: 딕셔너리 (Dictionary)
  사용 위치: CAMPUS_GRAPH, distances, previous_nodes
- 자료구조명: 우선순위 큐 (Priority Queue)
  사용 위치: dijkstra() 함수 내 priority_queue (heapq 모듈)

입력 데이터:
- current_place: 현재 위치 (str)
- next_class_place: 다음 수업 장소 (str)
- candidate_places: 추천 후보 장소 목록 (list)
- graph: 캠퍼스 그래프 데이터 (dict, 기본값: CAMPUS_GRAPH)

출력 데이터:
- 후보 장소별 딕셔너리 리스트
  - place: 후보 장소명
  - go_minutes: 현재 위치 → 후보 장소 이동시간
  - return_minutes: 후보 장소 → 다음 수업 장소 이동시간
  - total_travel_minutes: 총 이동시간
  - go_path: 현재 위치 → 후보 장소 경로 리스트
  - return_path: 후보 장소 → 다음 수업 장소 경로 리스트
  - full_path: 전체 경로 리스트
  - is_reachable: 경로 계산 가능 여부
============================================================
"""

import heapq  # [자료구조] 우선순위 큐 (Priority Queue)
from data.graph_data import CAMPUS_GRAPH


def dijkstra(graph, start_place):
    """
    [알고리즘] 다익스트라 (Dijkstra)
    시작 장소에서 모든 장소까지의 최단 이동시간을 계산한다.
    시간복잡도: O((V + E) log V)
    """
    # [자료구조] 딕셔너리 - 최단거리 저장
    distances = {place: float("inf") for place in graph}
    distances[start_place] = 0

    # [자료구조] 딕셔너리 - 경로 복원용 직전 노드 기록
    previous_nodes = {place: None for place in graph}

    # [자료구조] 우선순위 큐 - (이동시간, 장소명) 형태로 관리
    priority_queue = [(0, start_place)]

    while priority_queue:
        current_distance, current_place = heapq.heappop(priority_queue)

        if current_distance > distances[current_place]:
            continue

        for neighbor, weight in graph.get(current_place, {}).items():
            distance = current_distance + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_place
                heapq.heappush(priority_queue, (distance, neighbor))

    return distances, previous_nodes


def reconstruct_path(previous_nodes, start_place, end_place):
    """
    [알고리즘] 경로 복원 (Backtracking)
    previous_nodes를 역추적해 실제 이동 경로 리스트를 반환한다.
    시간복잡도: O(V)
    """
    path = []
    current = end_place

    while current is not None:
        path.append(current)
        current = previous_nodes.get(current)

    path.reverse()

    if not path or path[0] != start_place:
        return []

    return path


def get_unreachable_path_result(place):
    """경로가 없는 장소의 기본 결과를 반환한다."""
    return {
        "place": place,
        "go_minutes": None,
        "return_minutes": None,
        "total_travel_minutes": None,
        "go_path": [],
        "return_path": [],
        "full_path": [],
        "is_reachable": False,
    }


def find_shortest_paths(current_place, next_class_place, candidate_places, graph=None):
    """
    후보 장소별 최단 이동 경로와 이동시간을 계산해 반환한다.
    총 이동시간 기준 오름차순 정렬.
    """
    if graph is None:
        graph = CAMPUS_GRAPH

    distances_from_current, prev_from_current = dijkstra(graph, current_place)
    distances_from_next, prev_from_next = dijkstra(graph, next_class_place)

    path_results = []

    for candidate in candidate_places:
        go_minutes = distances_from_current.get(candidate, float("inf"))
        return_minutes = distances_from_next.get(candidate, float("inf"))

        if go_minutes == float("inf") or return_minutes == float("inf"):
            path_results.append(get_unreachable_path_result(candidate))
            continue

        go_path = reconstruct_path(prev_from_current, current_place, candidate)
        return_path = reconstruct_path(prev_from_next, next_class_place, candidate)
        return_path.reverse()

        full_path = go_path + return_path[1:] if return_path else go_path
        total_travel_minutes = go_minutes + return_minutes

        path_results.append({
            "place": candidate,
            "go_minutes": go_minutes,
            "return_minutes": return_minutes,
            "total_travel_minutes": total_travel_minutes,
            "go_path": go_path,
            "return_path": return_path,
            "full_path": full_path,
            "is_reachable": True,
        })

    path_results.sort(key=lambda x: (x["total_travel_minutes"] is None, x["total_travel_minutes"]))

    return path_results


if __name__ == "__main__":
    current_place    = "AI관"
    next_class_place = "비전타워"
    candidate_places = ["중앙도서관", "스타덤광장", "가천관", "교육대학원"]

    results = find_shortest_paths(current_place, next_class_place, candidate_places)

    print("=" * 60)
    print("          최단경로 계산 결과")
    print("=" * 60)
    print(f"  현재 위치  : {current_place}")
    print(f"  다음 수업  : {next_class_place}")
    print(f"  후보 장소  : {candidate_places}")
    print("=" * 60)

    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['place']}")
        if not r["is_reachable"]:
            print("     경로 없음")
            continue
        print(f"     이동시간(현재→후보) : {r['go_minutes']}분")
        print(f"     이동시간(후보→수업) : {r['return_minutes']}분")
        print(f"     총 이동시간         : {r['total_travel_minutes']}분")
        print(f"     전체 경로           : {' → '.join(r['full_path'])}")