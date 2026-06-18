"""
============================================================
기능명: 최단경로 계산 - 경로 시각화 (실제 지도 버전)
담당자: 전병호

핵심 기능:
- 실제 지도(OpenStreetMap) 위에 캠퍼스 건물 마커 표시
- 최단경로를 색상 선으로 강조하여 표시
- 건물 간 이동시간을 팝업으로 표시
- 결과를 HTML 파일로 저장하고, 요청한 경우에만 브라우저 실행

사용 라이브러리:
- folium: 실제 지도 시각화 (pip install folium)

사용 알고리즘:
- 알고리즘명: 다익스트라 (Dijkstra)
  사용 위치: path_finder.py의 find_shortest_paths() 호출

입력 데이터:
- current_place: 현재 위치 (str)
- next_class_place: 다음 수업 장소 (str)
- candidate_places: 추천 후보 장소 목록 (list)

출력 데이터:
- campus_path.html: 브라우저에서 열리는 실제 지도 시각화
============================================================
"""

import os
import webbrowser
import folium
from folium import plugins

# data 폴더 구조에 맞게 임포트 (같은 폴더에 있을 경우 대비)
try:
    from data.graph_data import CAMPUS_GRAPH, EDGE_PATHS
except ImportError:
    try:
        from graph_data import CAMPUS_GRAPH, EDGE_PATHS
    except ImportError:
        from graph_data import CAMPUS_GRAPH
        EDGE_PATHS = {}

try:
    from path_finder import find_shortest_paths
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from path_finder import find_shortest_paths


# ──────────────────────────────────────────────────────────
# 실제 건물 위도/경도 (구글맵 위성 기반 측정)
# 가천대학교 글로벌캠퍼스, 경기도 성남시 수정구 성남대로 1342
# ──────────────────────────────────────────────────────────
BUILDING_COORDS = {
    "비전타워":      (37.4497184, 127.1272083),
    "가천관":        (37.450470,  127.129785),
    "스타덤광장":    (37.450829,  127.127895),
    "AI관":          (37.455134,  127.133493),
    "제3기숙사":     (37.455884,  127.133168),
    "제2기숙사":     (37.456051,  127.133975),
    "종합운동장":    (37.455100,  127.135151),
    "중앙도서관":    (37.452401,  127.132947),
    "교육대학원":    (37.451964,  127.131881),
    "공과대학1":     (37.451583,  127.128075),
    "공과대학2":     (37.449308,  127.128314),
    "글로벌센터":    (37.451817,  127.127242),
    "예술체육대학1": (37.452245,  127.128764),
    "예술체육대학2": (37.451630,  127.129749),
    "반도체대학":    (37.451021,  127.127093),
}

# 색상 정의
COLOR_START    = "#534AB7"   # 보라 - 출발
COLOR_END      = "#993C1D"   # 붉은갈색 - 도착
COLOR_WAYPOINT = "#0F6E56"   # 초록 - 경유(후보)
COLOR_DEFAULT  = "#888780"   # 회색 - 일반 건물
COLOR_GO_PATH  = "#534AB7"   # 가는 길 선
COLOR_RET_PATH = "#1D9E75"   # 돌아오는 길 선
COLOR_EDGE     = "#B4B2A9"   # 기본 그래프 간선


def make_marker_html(color, label):
    """원형 마커 HTML 생성 - 글자 길이에 맞게 크기 자동 조정."""
    char_count = len(label)
    width = max(36, char_count * 13 + 16)
    height = 36
    font_size = 11
    border_radius = height // 2
    return f"""
    <div style="
        background:{color};
        border:2.5px solid white;
        border-radius:{border_radius}px;
        width:{width}px;height:{height}px;
        display:flex;align-items:center;justify-content:center;
        font-size:{font_size}px;font-weight:700;color:white;
        box-shadow:0 2px 8px rgba(0,0,0,0.3);
        font-family:sans-serif;
        white-space:nowrap;
        padding:0 6px;
    ">{label}</div>"""


def get_edge_coords(u, v):
    """EDGE_PATHS에서 보행로 좌표를 찾고 없으면 직선 반환."""
    key = tuple(sorted([u, v]))
    coords = EDGE_PATHS.get((u, v)) or EDGE_PATHS.get((v, u)) or EDGE_PATHS.get(key)
    if coords:
        return coords
    if u in BUILDING_COORDS and v in BUILDING_COORDS:
        return [BUILDING_COORDS[u], BUILDING_COORDS[v]]
    return None


def draw_base_edges(fmap):
    """전체 캠퍼스 그래프 간선을 점선으로 그린다."""
    drawn = set()
    for u, neighbors in CAMPUS_GRAPH.items():
        for v, weight in neighbors.items():
            key = tuple(sorted([u, v]))
            if key in drawn:
                continue
            drawn.add(key)
            coords = get_edge_coords(u, v)
            if coords:
                folium.PolyLine(
                    locations=coords,
                    color=COLOR_EDGE,
                    weight=2,
                    opacity=0.5,
                    dash_array="6 4",
                    tooltip=f"{u} ↔ {v}: {weight}분",
                ).add_to(fmap)


def draw_path_line(fmap, path, color, label):
    """경로를 굵은 선으로 그린다. EDGE_PATHS가 있으면 보행로 따라 그림."""
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        coords = get_edge_coords(u, v)
        if not coords:
            continue
        # 방향 맞추기: u가 시작점이 되도록
        if coords[0] != BUILDING_COORDS.get(u) and coords[-1] == BUILDING_COORDS.get(u):
            coords = list(reversed(coords))
        folium.PolyLine(
            locations=coords,
            color=color,
            weight=6,
            opacity=0.85,
            tooltip=label,
        ).add_to(fmap)


def add_markers(fmap, current_place, next_class_place, candidate_places, best_path_nodes):
    """건물 마커를 지도에 추가한다."""
    for place, coord in BUILDING_COORDS.items():
        if place == current_place:
            color, label = COLOR_START, place
        elif place == next_class_place:
            color, label = COLOR_END, place
        elif place in candidate_places:
            color, label = COLOR_WAYPOINT, place
        elif place in best_path_nodes:
            color, label = "#BA7517", place
        else:
            color, label = COLOR_DEFAULT, place

        char_count = len(label)
        width = max(36, char_count * 13 + 16)
        icon = folium.DivIcon(
            html=make_marker_html(color, label),
            icon_size=(width, 36),
            icon_anchor=(width // 2, 18),
        )
        folium.Marker(
            location=coord,
            icon=icon,
            tooltip=place,
            popup=folium.Popup(place, max_width=120),
        ).add_to(fmap)


def build_legend_html(current_place, next_class_place, best):
    """범례 및 결과 패널 HTML 생성."""
    if best:
        path_str = f"{current_place} → {best['place']} → {next_class_place}"
        result_html = f"""
        <div style="margin-top:8px;font-size:13px;color:#2C2C2A">
            <b>최적 경유지:</b> <span style="color:{COLOR_WAYPOINT}">{best['place']}</span><br>
            <b>경로:</b> {path_str}<br>
            <b>총 이동시간:</b> {best['total_travel_minutes']}분
            &nbsp;(가는 길 {best['go_minutes']}분 + 돌아오는 길 {best['return_minutes']}분)
        </div>"""
    else:
        result_html = "<div style='color:#A32D2D;margin-top:8px'>도달 가능한 경로가 없습니다.</div>"

    legend = f"""
    <div style="
        position:fixed;bottom:30px;left:20px;z-index:1000;
        background:white;border:1px solid #ddd;border-radius:12px;
        padding:14px 18px;font-family:sans-serif;
        box-shadow:0 4px 16px rgba(0,0,0,0.15);
        max-width:320px;
    ">
        <div style="font-weight:700;font-size:14px;color:#2C2C2A;margin-bottom:8px">
            🗺 가천대 캠퍼스 최단경로
        </div>
        <div style="display:flex;flex-direction:column;gap:5px;font-size:12px">
            <div><span style="background:{COLOR_START};color:white;border-radius:4px;padding:2px 8px">출발</span>
                &nbsp;{current_place}</div>
            <div><span style="background:{COLOR_END};color:white;border-radius:4px;padding:2px 8px">도착</span>
                &nbsp;{next_class_place}</div>
            <div><span style="background:{COLOR_WAYPOINT};color:white;border-radius:4px;padding:2px 8px">경유</span>
                &nbsp;후보 장소</div>
        </div>
        <hr style="margin:8px 0;border:none;border-top:1px solid #eee">
        <div style="font-size:12px;color:#5F5E5A">
            <span style="display:inline-block;width:30px;height:4px;
                background:{COLOR_GO_PATH};vertical-align:middle;margin-right:6px;border-radius:2px"></span>
            가는 길&nbsp;&nbsp;
            <span style="display:inline-block;width:30px;height:4px;
                background:{COLOR_RET_PATH};vertical-align:middle;margin-right:6px;border-radius:2px"></span>
            돌아오는 길
        </div>
        {result_html}
    </div>"""
    return legend


def visualize_path(
    current_place,
    next_class_place,
    candidate_places,
    result=None,
    open_browser=False,
):
    """캠퍼스 최단경로를 실제 지도 위에 시각화해 HTML로 저장한다.

    open_browser=True인 경우에만 기본 브라우저로 결과를 연다.
    서버·CI·통합 실행에서 불필요한 GUI 오류를 막기 위해 기본값은 False다.
    """

    if result is None:
        result = find_shortest_paths(current_place, next_class_place, candidate_places)

    reachable = [r for r in result if r["is_reachable"]]
    best = reachable[0] if reachable else None
    best_path_nodes = set(best["full_path"]) if best else set()

    # 지도 중심: 캠퍼스 중앙
    center = (37.45250, 127.13000)
    fmap = folium.Map(location=center, zoom_start=17, tiles="OpenStreetMap")

    # 기본 간선
    draw_base_edges(fmap)

    # 최단경로 선
    if best:
        # 가는 길: 현재위치 → 후보장소
        draw_path_line(fmap, best["go_path"], COLOR_GO_PATH, "가는 길")
        
        # 돌아오는 길: 후보장소 → 다음수업
        draw_path_line(fmap, best["return_path"], COLOR_RET_PATH, "돌아오는 길")
        
    else:
        # 후보 없으면 직접 경로
        try:
            from path_finder import dijkstra, reconstruct_path
            _, prev = dijkstra(CAMPUS_GRAPH, current_place)
            direct = reconstruct_path(prev, current_place, next_class_place)
            draw_path_line(fmap, direct, COLOR_GO_PATH, "직접 경로")
            best_path_nodes = set(direct)
        except Exception:
            pass

    # 마커
    add_markers(fmap, current_place, next_class_place, candidate_places, best_path_nodes)

    # 범례
    legend_html = build_legend_html(current_place, next_class_place, best)
    fmap.get_root().html.add_child(folium.Element(legend_html))

    # 저장 & 실행
    output_path = os.path.join(os.path.dirname(__file__), "campus_path.html")
    fmap.save(output_path)
    print(f"[✓] 지도 저장 완료: {output_path}")

    if best:
        print(f"[경로] {' → '.join(best['full_path'])}")
        print(f"[시간] 총 {best['total_travel_minutes']}분  "
              f"(가는 길 {best['go_minutes']}분 + 돌아오는 길 {best['return_minutes']}분)")
    else:
        print("[!] 도달 가능한 경로를 찾지 못했습니다.")

    if open_browser:
        webbrowser.open(f"file://{os.path.abspath(output_path)}")


if __name__ == "__main__":
    current_place    = "AI관"
    next_class_place = "비전타워"
    candidate_places = ["중앙도서관", "스타덤광장", "가천관", "교육대학원"] 

    results = find_shortest_paths(current_place, next_class_place, candidate_places)
    visualize_path(current_place, next_class_place, candidate_places, result=results)
