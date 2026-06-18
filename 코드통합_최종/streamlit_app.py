"""
streamlit UI 실행방법:
터미널에서
1. pip install streamlit
2. streamlit run streamlit_app.py
"""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from crowd_analyzer import analyze_crowd
from data.graph_data import CAMPUS_GRAPH
from data.place_data import get_recommendation_places
from main import (
    convert_crowd_results_to_dict,
    convert_path_results_to_dict,
    get_candidate_path_nodes,
)
from path_finder import find_shortest_paths
import path_visualizer
from place_recommender import build_user_friendly_reason, recommend_places
from timetable_analyzer import analyze_timetable
from data.timetable_data import TIMETABLE


DAY_OPTIONS = ["월", "화", "수", "목", "금"]
PURPOSE_OPTIONS = ["공부", "휴식", "팀플", "식사", "카페", "프린트", "편의점"]
TIMETABLE_START_HOUR = 7
TIMETABLE_END_HOUR = 22
TIMETABLE_COLORS = [
    "#dff3eb",
    "#e8f0ff",
    "#ffe8e8",
    "#f4ecc8",
    "#e8edf7",
    "#e8f6d5",
    "#f5e8ff",
]


st.set_page_config(
    page_title="공강 플래너",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    :root {
        --ink: #17212b;
        --muted: #667085;
        --line: #d9e2ec;
        --panel: #ffffff;
        --green: #0f766e;
        --blue: #2563eb;
    }
    .block-container {
        padding-top: 2.35rem;
        padding-bottom: 1.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 1480px;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.35rem;
    }
    h1, h2, h3 {
        letter-spacing: 0;
        color: var(--ink);
    }
    div[data-testid="stMarkdownContainer"] a.app-title-link,
    div[data-testid="stMarkdownContainer"] a.app-title-link:visited,
    div[data-testid="stMarkdownContainer"] a.app-title-link:hover,
    div[data-testid="stMarkdownContainer"] a.app-title-link:active {
        display: inline-block;
        color: #f8fafc !important;
        font-size: 2.16rem;
        font-weight: 820;
        line-height: 1.28;
        letter-spacing: 0;
        margin: .2rem 0 .8rem 0;
        padding: .08rem 0;
        text-decoration: none !important;
        max-width: 100%;
        white-space: normal;
    }
    div[data-testid="stMarkdownContainer"] a.app-title-link:hover {
        color: #ffffff !important;
    }
    .section-title {
        font-size: 1.02rem;
        font-weight: 720;
        margin: 1.1rem 0 .55rem 0;
    }
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .7rem;
        margin-bottom: .6rem;
    }
    .metric-box {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: .75rem .85rem;
        background: var(--panel);
    }
    .metric-label {
        color: var(--muted);
        font-size: .78rem;
        margin-bottom: .22rem;
    }
    .metric-value {
        color: var(--ink);
        font-size: 1.12rem;
        font-weight: 740;
        line-height: 1.25;
    }
    .metric-subvalue {
        display: block;
        color: var(--muted);
        font-size: .82rem;
        font-weight: 650;
        line-height: 1.35;
        margin-top: .16rem;
    }
    .rec-card {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: .95rem 1rem;
        margin-bottom: .75rem;
        background: var(--panel);
    }
    .rec-head {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: .28rem;
        border-bottom: 1px solid #edf1f5;
        padding-bottom: .55rem;
        margin-bottom: .7rem;
    }
    .rec-title {
        font-size: 1.03rem;
        font-weight: 760;
        color: var(--ink);
        line-height: 1.38;
    }
    .rec-meta {
        color: var(--muted);
        font-size: .85rem;
        white-space: normal;
    }
    .badge {
        display: inline-block;
        border-radius: 999px;
        padding: .16rem .5rem;
        font-size: .78rem;
        font-weight: 700;
        background: #e8f5f2;
        color: var(--green);
        margin-left: .35rem;
    }
    .detail-row {
        display: grid;
        grid-template-columns: 4.65rem minmax(0, 1fr);
        column-gap: .32rem;
        row-gap: .18rem;
        font-size: .9rem;
        margin: .32rem 0;
    }
    .detail-label {
        color: var(--muted);
        font-weight: 650;
        white-space: nowrap;
    }
    .detail-value {
        color: var(--ink);
    }
    .score-detail-row .detail-value {
        font-size: .86rem;
        white-space: nowrap;
    }
    .notice {
        border-left: 4px solid var(--blue);
        background: #eff6ff;
        padding: .75rem .9rem;
        border-radius: 6px;
        color: #1e3a8a;
        font-size: .9rem;
        margin-bottom: .8rem;
    }
    .stop-panel {
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--panel);
        padding: 1.2rem;
        margin-top: 1rem;
    }
    .stop-title {
        color: var(--ink);
        font-size: 1.12rem;
        font-weight: 760;
        margin-bottom: .35rem;
    }
    .stop-copy {
        color: var(--muted);
        line-height: 1.58;
        margin-bottom: 1rem;
    }
    .start-message {
        min-height: 620px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 1rem 0 1rem 5rem;
    }
    .start-message-title {
        color: #f8fafc;
        font-size: 2.55rem;
        font-weight: 820;
        line-height: 1.28;
        letter-spacing: 0;
        margin: 0 0 1.3rem 0;
        text-align: center;
    }
    .start-message-line {
        width: min(100%, 320px);
        height: 1px;
        background: #3b82f6;
        margin: 0 auto 1.55rem auto;
    }
    .start-message-copy {
        color: #cbd5e1;
        font-size: .98rem;
        line-height: 1.58;
        text-align: center;
        margin: 0 auto;
        max-width: 420px;
    }
    .sidebar-time-note {
        color: #cbd5e1;
        font-size: .72rem;
        line-height: 1.25;
        white-space: nowrap;
        margin: .18rem 0 .8rem 0;
    }
    .stop-panel {
        border-left: 4px solid #dc2626;
    }
    .timetable-wrap {
        width: 100%;
        overflow-x: auto;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #ffffff;
    }
    .timetable-calendar {
        min-width: 0;
        display: grid;
        grid-template-columns: 64px repeat(5, minmax(92px, 1fr));
        grid-template-rows: 42px 600px;
    }
    .tt-head {
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f8fafc;
        border-bottom: 1px solid var(--line);
        border-right: 1px solid var(--line);
        color: var(--muted);
        font-size: .9rem;
        font-weight: 700;
    }
    .tt-time-column {
        position: relative;
        grid-column: 1;
        grid-row: 2;
        background: #fbfcfe;
        border-right: 1px solid var(--line);
    }
    .tt-time-label {
        position: absolute;
        right: .32rem;
        top: calc(var(--top) * 1%);
        transform: translateY(-50%);
        color: #8a94a3;
        font-size: .68rem;
        white-space: nowrap;
    }
    .tt-day-column {
        position: relative;
        grid-row: 2;
        border-right: 1px solid var(--line);
        background:
            repeating-linear-gradient(
                to bottom,
                #ffffff 0,
                #ffffff calc(100% / 15 - 1px),
                #e7edf3 calc(100% / 15 - 1px),
                #e7edf3 calc(100% / 15)
            );
    }
    .tt-class {
        position: absolute;
        left: .26rem;
        right: .26rem;
        top: calc(var(--top) * 1%);
        height: max(calc(var(--height) * 1%), 34px);
        border: 1px solid rgba(23, 33, 43, .08);
        border-left: 4px solid rgba(23, 33, 43, .28);
        border-radius: 6px;
        padding: .3rem .34rem;
        overflow: hidden;
        color: var(--ink);
        box-shadow: none;
    }
    .tt-subject {
        font-size: .72rem;
        font-weight: 780;
        line-height: 1.15;
        margin-bottom: .08rem;
    }
    .tt-meta {
        font-size: .6rem;
        color: #475569;
        line-height: 1.2;
    }
    @media (max-width: 900px) {
        .summary-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .rec-head {
            display: block;
        }
        .rec-meta {
            margin-top: .25rem;
            white-space: normal;
        }
        .start-message {
            min-height: auto;
            padding: .8rem 0 0 0;
        }
        .start-message-title {
            font-size: 2rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_minutes(value) -> str:
    if value is None:
        return "-"
    return f"{value}분"


def format_path(path: list[str]) -> str:
    return " -> ".join(path) if path else "경로 정보 없음"


def parse_time_to_minutes(time_text: str) -> int:
    hour, minute = map(int, time_text.split(":"))
    return hour * 60 + minute


def format_hour_label(hour: int) -> str:
    if hour < 12:
        return f"오전 {hour}시"
    if hour == 12:
        return "오후 12시"
    return f"오후 {hour - 12}시"


def render_timetable_table() -> None:
    start_minutes = TIMETABLE_START_HOUR * 60
    end_minutes = TIMETABLE_END_HOUR * 60
    total_minutes = end_minutes - start_minutes
    class_counts_by_subject: dict[str, int] = {}

    header_cells = ['<div class="tt-head" style="grid-column:1;grid-row:1;"></div>']
    for index, day in enumerate(DAY_OPTIONS, start=2):
        header_cells.append(
            f'<div class="tt-head" style="grid-column:{index};grid-row:1;">{day}</div>'
        )

    time_labels = []
    for hour in range(TIMETABLE_START_HOUR, TIMETABLE_END_HOUR + 1):
        top = ((hour * 60 - start_minutes) / total_minutes) * 100
        time_labels.append(
            f'<div class="tt-time-label" style="--top:{top:.4f};">{format_hour_label(hour)}</div>'
        )

    day_columns = []
    for day_index, day in enumerate(DAY_OPTIONS, start=2):
        blocks = []
        day_classes = [
            row for row in sorted(TIMETABLE, key=lambda item: item["start"]) if row["day"] == day
        ]
        for row in day_classes:
            class_start = max(parse_time_to_minutes(row["start"]), start_minutes)
            class_end = min(parse_time_to_minutes(row["end"]), end_minutes)
            if class_end <= start_minutes or class_start >= end_minutes:
                continue

            subject = row["subject"]
            if subject not in class_counts_by_subject:
                class_counts_by_subject[subject] = len(class_counts_by_subject)
            color = TIMETABLE_COLORS[class_counts_by_subject[subject] % len(TIMETABLE_COLORS)]
            top = ((class_start - start_minutes) / total_minutes) * 100
            height = ((class_end - class_start) / total_minutes) * 100
            blocks.append(
                f'<div class="tt-class" style="--top:{top:.4f};--height:{height:.4f};background:{color};">'
                f'<div class="tt-subject">{escape(subject)}</div>'
                f'<div class="tt-meta">{escape(row["start"])}-{escape(row["end"])} · {escape(row["building"])}</div>'
                "</div>"
            )
        day_columns.append(
            f'<div class="tt-day-column" style="grid-column:{day_index};">{"".join(blocks)}</div>'
        )

    timetable_html = (
        '<div class="timetable-wrap">'
        '<div class="timetable-calendar">'
        f"{''.join(header_cells)}"
        f'<div class="tt-time-column">{"".join(time_labels)}</div>'
        f"{''.join(day_columns)}"
        "</div>"
        "</div>"
    )
    st.markdown(timetable_html, unsafe_allow_html=True)


def format_location(item: dict) -> str:
    path_node = item.get("path_node") or item.get("place", "")
    detail = item.get("detail_location") or ""
    if detail and detail != path_node:
        return f"{path_node}({detail})"
    return path_node


def format_score_detail(score_detail: dict) -> str:
    if not isinstance(score_detail, dict):
        return "-"
    return (
        f"이동 {score_detail.get('travel', 0)}점 + "
        f"대기 {score_detail.get('wait', 0)}점 + "
        f"혼잡 {score_detail.get('crowd', 0)}점 + "
        f"선호 {score_detail.get('preference', 0)}점 = "
        f"{score_detail.get('total', 0)}점"
    )


def can_recommend(free_time: dict) -> bool:
    return (
        bool(free_time.get("is_free_time"))
        and free_time.get("free_minutes") != 999
        and bool(free_time.get("next_class_place"))
        and bool(free_time.get("next_class_start"))
    )


def get_unrecommendable_message(free_time: dict) -> tuple[str, str]:
    status = free_time.get("status")
    if status == "수업후":
        return (
            "오늘 남은 수업이 없습니다.",
            "다음 수업 장소로 돌아가는 시간을 계산할 수 없어 장소 추천을 중단했습니다.",
        )
    if status == "수업없음":
        return (
            "해당 요일 수업이 없습니다.",
            "다음 수업 기준 이동 경로가 없어서 장소 추천을 중단했습니다.",
        )
    if not free_time.get("is_free_time"):
        return (
            "현재는 수업 시간입니다.",
            "공강 시간이 아닐 때는 장소 추천을 실행하지 않습니다.",
        )
    return (
        "추천 기준이 부족합니다.",
        "다음 수업 시간 또는 다음 수업 장소를 확인할 수 없어 장소 추천을 중단했습니다.",
    )


def build_summary_html(free_time: dict, recommendation_count: int) -> str:
    total_minutes = free_time.get("free_minutes", 0)
    available_minutes = free_time.get("available_minutes_for_recommendation", total_minutes)
    next_class = free_time.get("next_class") or "-"
    next_place = free_time.get("next_class_place") or free_time.get("current_place") or "-"
    next_start = free_time.get("next_class_start") or "-"

    return f"""
    <div class="summary-grid">
        <div class="metric-box">
            <div class="metric-label">전체 공강시간</div>
            <div class="metric-value">{total_minutes}분</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">추천 기준 시간</div>
            <div class="metric-value">{available_minutes}분</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">다음 수업</div>
            <div class="metric-value">{next_class} · {next_start}<span class="metric-subvalue">장소 {next_place}</span></div>
        </div>
        <div class="metric-box">
            <div class="metric-label">추천 수</div>
            <div class="metric-value">{recommendation_count}곳</div>
        </div>
    </div>
    """


def render_start_screen() -> None:
    timetable_col, message_col = st.columns([0.62, 0.38], gap="small")

    with timetable_col:
        st.markdown('<div class="section-title">현재 입력 기준 시간표</div>', unsafe_allow_html=True)
        render_timetable_table()

    with message_col:
        st.markdown(
            """
            <div class="start-message">
                <div class="start-message-title">공강 시간을<br>선명하게 설계하다</div>
                <div class="start-message-line"></div>
                <div class="start-message-copy">시간표 · 경로 · 혼잡도 · 목적을 하나의 흐름으로 연결해<br>공강 시간 안에 실제로 이용 가능한 장소를 추천합니다.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_unrecommendable_state(free_time: dict) -> None:
    title, message = get_unrecommendable_message(free_time)
    status = free_time.get("status") or "-"
    current_place = free_time.get("current_place") or "-"
    next_class = free_time.get("next_class") or "-"
    next_place = free_time.get("next_class_place") or "-"

    st.markdown('<div class="section-title">공강 요약</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="summary-grid">
            <div class="metric-box">
                <div class="metric-label">현재 상태</div>
                <div class="metric-value">{status}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">현재 위치</div>
                <div class="metric-value">{current_place}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">다음 수업</div>
                <div class="metric-value">{next_class}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">다음 장소</div>
                <div class="metric-value">{next_place}</div>
            </div>
        </div>
        <div class="stop-panel">
            <div class="stop-title">{title}</div>
            <div class="stop-copy">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recommendation_card(item: dict) -> None:
    available_text = "이용 가능" if item.get("available") else "이용 불가"
    total_free = item.get("total_free_minutes")
    total_needed = item.get("total_needed_minutes")
    time_usage = (
        f"공강시간 {total_free}분 중 {total_needed}분 사용"
        if total_free and total_needed is not None
        else f"총 {total_needed}분 사용"
    )

    st.markdown(
        f"""
        <div class="rec-card">
            <div class="rec-head">
                <div class="rec-title">
                    {item.get("rank")}위 · {item.get("place")}({item.get("score")}점)
                    <span class="badge">{available_text}</span>
                </div>
                <div class="rec-meta">{time_usage}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">위치</div>
                <div class="detail-value">{format_location(item)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">소요 시간</div>
                <div class="detail-value">
                    이동 {format_minutes(item.get("travel_minutes"))} + 대기 {format_minutes(item.get("expected_wait_minutes"))}
                    + 최소 이용 {format_minutes(item.get("min_stay_minutes"))} = 총 {format_minutes(total_needed)}
                </div>
            </div>
            <div class="detail-row">
                <div class="detail-label">혼잡도</div>
                <div class="detail-value">{item.get("crowd_level")}점({item.get("crowd_label", "보통")})</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">경로</div>
                <div class="detail-value">{format_path(item.get("shortest_path", []))}</div>
            </div>
            <div class="detail-row score-detail-row">
                <div class="detail-label">점수 구성</div>
                <div class="detail-value">{format_score_detail(item.get("score_detail"))}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">추천 이유</div>
                <div class="detail-value">{build_user_friendly_reason(item)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_map_html(current_place, next_class_place, candidate_places, path_results, recommendations=None):
    reachable = [result for result in path_results if result.get("is_reachable")]
    best = reachable[0] if reachable else None
    if best and recommendations:
        best_place = recommendations[0]["place"]
        best_node = recommendations[0].get("path_node", best_place)
        for r in path_results:
            if r.get("place") == best_node:
                best = {**r, "place": best_place}
                break

    best_path_nodes = set(best["full_path"]) if best else set()

    fmap = path_visualizer.folium.Map(
        location=(37.45250, 127.13000),
        zoom_start=17,
        tiles="OpenStreetMap",
    )
    path_visualizer.draw_base_edges(fmap)

    if best:
        path_visualizer.draw_path_line(
            fmap,
            best["go_path"],
            path_visualizer.COLOR_GO_PATH,
            "가는 길",
        )
        path_visualizer.draw_path_line(
            fmap,
            best["return_path"],
            path_visualizer.COLOR_RET_PATH,
            "돌아오는 길",
        )

    path_visualizer.add_markers(
        fmap,
        current_place,
        next_class_place,
        candidate_places,
        best_path_nodes,
    )
    legend_html = path_visualizer.build_legend_html(current_place, next_class_place, best)
    fmap.get_root().html.add_child(path_visualizer.folium.Element(legend_html))
    return fmap.get_root().render()


def build_recommendations(current_day: str, current_time: str, current_place: str, user_purpose: str):
    free_time_result = analyze_timetable(current_day, current_time, current_place)
    free_time_result["user_purpose"] = user_purpose

    if not can_recommend(free_time_result):
        return free_time_result, [], [], [], None

    places = get_recommendation_places(include_support=False)
    candidate_places = list(places.keys())
    candidate_path_nodes = get_candidate_path_nodes(places)
    next_class_place = free_time_result.get("next_class_place") or free_time_result["current_place"]
    route_start_place = current_place

    path_results_list = find_shortest_paths(
        route_start_place,
        next_class_place,
        candidate_path_nodes,
    )
    path_results = convert_path_results_to_dict(path_results_list)

    crowd_results_list = analyze_crowd(current_time, candidate_places)
    crowd_results = convert_crowd_results_to_dict(crowd_results_list, candidate_places)

    recommendations = recommend_places(
        free_time_result,
        path_results,
        crowd_results,
        places,
    )

    map_html = build_map_html(
        route_start_place,
        next_class_place,
        candidate_path_nodes,
        path_results_list,
        recommendations,
    )

    return free_time_result, recommendations, path_results_list, crowd_results_list, map_html


def get_query_param_value(name: str):
    try:
        value = st.query_params.get(name)
    except Exception:
        try:
            value = st.experimental_get_query_params().get(name)
        except Exception:
            return None

    if isinstance(value, list):
        return value[0] if value else None
    return value


def clear_home_query_param() -> None:
    try:
        if "home" in st.query_params:
            del st.query_params["home"]
        return
    except Exception:
        pass

    try:
        st.experimental_set_query_params()
    except Exception:
        pass


def rerun_app() -> None:
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()


def handle_home_navigation() -> None:
    if get_query_param_value("home") == "1":
        st.session_state.pop("last_result", None)
        clear_home_query_param()
        rerun_app()


def main() -> None:
    handle_home_navigation()
    st.markdown(
        '<a class="app-title-link" href="?home=1" target="_self">공강 플래너</a>',
        unsafe_allow_html=True,
    )

    graph_places = sorted(CAMPUS_GRAPH.keys())
    default_place_index = graph_places.index("가천관") if "가천관" in graph_places else 0

    with st.sidebar:
        st.header("입력")
        selected_day = st.selectbox("요일", DAY_OPTIONS, index=2)
        st.markdown(
            '<div class="sidebar-time-note">현재 시간은 07:00부터 22:00까지만 선택합니다.</div>',
            unsafe_allow_html=True,
        )
        hour_col, minute_col = st.columns(2)
        with hour_col:
            selected_hour = st.selectbox(
                "시",
                list(range(7, 23)),
                index=3,
                format_func=lambda hour: f"{hour:02d}시",
            )
        minute_options = [0] if selected_hour == 22 else list(range(0, 60, 5))
        default_minute_index = minute_options.index(30) if 30 in minute_options else 0
        with minute_col:
            selected_minute = st.selectbox(
                "분",
                minute_options,
                index=default_minute_index,
                format_func=lambda minute: f"{minute:02d}분",
            )
        current_time = f"{selected_hour:02d}:{selected_minute:02d}"
        current_place = st.selectbox("현재 위치", graph_places, index=default_place_index)
        user_purpose = st.selectbox("목적", PURPOSE_OPTIONS, index=0)
        run_button = st.button("추천 계산", type="primary", use_container_width=True)

        st.markdown("---")
        st.caption("공강플래너 프로토타입")

    if run_button:
        with st.spinner("공강 시간과 추천 장소를 계산하는 중입니다."):
            st.session_state.last_result = build_recommendations(
                selected_day,
                current_time,
                current_place,
                user_purpose,
            )

    if "last_result" not in st.session_state:
        render_start_screen()
        return

    free_time_result, recommendations, path_results, crowd_results, map_html = st.session_state.last_result

    if not can_recommend(free_time_result):
        render_unrecommendable_state(free_time_result)
        return

    st.markdown('<div class="section-title">공강 요약</div>', unsafe_allow_html=True)
    st.markdown(build_summary_html(free_time_result, len(recommendations)), unsafe_allow_html=True)

    st.markdown('<div class="notice">혼잡도는 1점 매우 여유, 2점 여유, 3점 보통, 4점 혼잡, 5점 매우 혼잡 기준입니다. 대기시간은 식당, 카페, 기타 장소 유형별 기준표를 사용합니다.</div>', unsafe_allow_html=True)

    table_rows = [
        {
            "순위": item.get("rank"),
            "장소": item.get("place"),
            "점수": item.get("score"),
            "위치": format_location(item),
            "총 소요": item.get("total_needed_minutes"),
            "이동": item.get("travel_minutes"),
            "대기": item.get("expected_wait_minutes"),
            "혼잡도": f"{item.get('crowd_level')}점({item.get('crowd_label', '보통')})",
        }
        for item in recommendations
    ]

    map_col, recommendation_col = st.columns([1.35, 0.65], gap="large")

    with map_col:
        st.markdown('<div class="section-title">경로 지도</div>', unsafe_allow_html=True)
        if map_html:
            components.html(map_html, height=620, scrolling=True)
        else:
            st.info("지도 파일을 아직 생성하지 못했습니다.")

        if table_rows:
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        with st.expander("혼잡도/대기시간 계산 결과"):
            st.dataframe(pd.DataFrame(crowd_results), use_container_width=True, hide_index=True)

        with st.expander("최단경로 계산 결과"):
            st.dataframe(pd.DataFrame(path_results), use_container_width=True, hide_index=True)

    with recommendation_col:
        st.markdown('<div class="section-title">추천 결과</div>', unsafe_allow_html=True)
        for item in recommendations:
            render_recommendation_card(item)


if __name__ == "__main__":
    main()
