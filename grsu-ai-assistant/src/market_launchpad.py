"""
Streamlit-инструмент для автономного выбора рыночной ниши и сборки MVP-плана.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

import streamlit as st


@dataclass(frozen=True)
class Niche:
    name: str
    audience: str
    pain: str
    mvp: str
    channels: List[str]
    monetization: str
    scores: Dict[str, int]


NICHES: List[Niche] = [
    Niche(
        name="AI-контент для short-form видео",
        audience="Креаторы и эксперты, которые растут через Reels/Shorts/TikTok",
        pain="Нужны ежедневные идеи, сценарии и контент-пакеты без выгорания",
        mvp="Генератор контент-системы: темы, hooks, сценарий, CTA, недельный контент-план",
        channels=["TikTok", "Instagram Reels", "YouTube Shorts", "Telegram"],
        monetization="Freemium + подписка Pro + шаблоны под ниши",
        scores={
            "demand": 9,
            "competition": 6,
            "monetization": 8,
            "virality": 10,
            "build_speed": 8,
        },
    ),
    Niche(
        name="AI-менеджер заявок для локального бизнеса",
        audience="Салоны, студии, частные клиники, школы",
        pain="Лиды теряются в мессенджерах, медленные ответы снижают конверсию",
        mvp="Автоответчик с квалификацией, бронированием и CRM-экспортом",
        channels=["Instagram", "WhatsApp", "Telegram", "Локальные сообщества"],
        monetization="Setup fee + ежемесячная подписка",
        scores={
            "demand": 8,
            "competition": 5,
            "monetization": 9,
            "virality": 6,
            "build_speed": 7,
        },
    ),
    Niche(
        name="Персональный AI-коуч по карьере",
        audience="Джуниоры и мидлы, меняющие работу",
        pain="Сложно адаптировать резюме, портфолио и коммуникацию под вакансии",
        mvp="Разбор профиля, адаптация CV, симулятор интервью, трекер откликов",
        channels=["LinkedIn", "Telegram", "Reddit", "YouTube"],
        monetization="Подписка + карьерные спринты + партнерские офферы",
        scores={
            "demand": 8,
            "competition": 7,
            "monetization": 8,
            "virality": 7,
            "build_speed": 7,
        },
    ),
]

WEIGHTS: Dict[str, float] = {
    "demand": 0.30,
    "competition": 0.15,
    "monetization": 0.25,
    "virality": 0.20,
    "build_speed": 0.10,
}


def weighted_score(scores: Dict[str, int], risk_tolerance: int) -> float:
    """Считает итоговый балл с учётом толерантности к конкуренции."""
    adjusted_competition = max(1, 11 - scores["competition"])
    comp_weight = WEIGHTS["competition"]
    if risk_tolerance >= 7:
        adjusted_competition = scores["competition"]
    elif risk_tolerance <= 3:
        comp_weight *= 1.6

    value = (
        scores["demand"] * WEIGHTS["demand"]
        + adjusted_competition * comp_weight
        + scores["monetization"] * WEIGHTS["monetization"]
        + scores["virality"] * WEIGHTS["virality"]
        + scores["build_speed"] * WEIGHTS["build_speed"]
    )
    return round(value, 2)


def evaluate_niches(time_per_day: int, budget: int, risk_tolerance: int) -> List[Tuple[Niche, float]]:
    """Возвращает ранжированный список ниш."""
    results: List[Tuple[Niche, float]] = []

    for niche in NICHES:
        score = weighted_score(niche.scores, risk_tolerance)

        if budget < 100:
            score -= 0.4
        elif budget > 700:
            score += 0.2

        if time_per_day < 2:
            score -= (10 - niche.scores["build_speed"]) * 0.08
        elif time_per_day >= 4:
            score += 0.2

        results.append((niche, round(score, 2)))

    return sorted(results, key=lambda item: item[1], reverse=True)


def build_30_day_plan(best_niche: Niche) -> Dict[str, List[str]]:
    """Формирует короткий roadmap запуска."""
    return {
        "Неделя 1: Продукт и позиционирование": [
            f"Сформулировать оффер: {best_niche.monetization}",
            "Подготовить лендинг с обещанием конкретного результата за 7 дней",
            "Собрать waitlist-форму и 10 интервью с целевой аудиторией",
        ],
        "Неделя 2: MVP": [
            f"Собрать MVP: {best_niche.mvp}",
            "Добавить сбор e-mail/Telegram для повторных касаний",
            "Запустить первый платный/бесплатный пилот на 5-10 пользователей",
        ],
        "Неделя 3: Контент и дистрибуция": [
            f"Запустить ежедневный контент в каналах: {', '.join(best_niche.channels)}",
            "Публиковать кейсы и конкретные результаты пользователей",
            "Настроить реферальную механику: бонус за приглашения",
        ],
        "Неделя 4: Монетизация и масштаб": [
            "Внедрить paywall и тарифы Starter/Pro",
            "Оптимизировать воронку: регистрация -> активация -> оплата",
            "Сфокусироваться на 1-2 каналах с лучшим CAC и удержанием",
        ],
    }


def render_niche_card(rank: int, niche: Niche, score: float) -> None:
    st.markdown(f"### {rank}. {niche.name} — {score}/10")
    st.write(f"**Аудитория:** {niche.audience}")
    st.write(f"**Проблема:** {niche.pain}")
    st.write(f"**MVP:** {niche.mvp}")
    st.write(f"**Монетизация:** {niche.monetization}")
    st.write(f"**Каналы роста:** {', '.join(niche.channels)}")


def main() -> None:
    st.set_page_config(page_title="Popularity Launchpad", page_icon="🚀", layout="wide")

    st.title("🚀 Popularity Launchpad")
    st.markdown(
        """
        Инструмент сам выбирает лучший рыночный вектор и даёт конкретный план запуска.
        Подходит, если нужно быстро сделать продукт с шансом на рост и публичность.
        """
    )

    with st.sidebar:
        st.header("Параметры запуска")
        time_per_day = st.slider("Время в день (часы)", min_value=1, max_value=8, value=3)
        budget = st.slider("Стартовый бюджет (USD)", min_value=0, max_value=3000, value=300, step=50)
        risk_tolerance = st.slider("Толерантность к конкуренции (1-10)", min_value=1, max_value=10, value=5)

    ranked = evaluate_niches(time_per_day, budget, risk_tolerance)
    winner, winner_score = ranked[0]

    st.subheader("Топ-3 ниши по текущим условиям")
    for index, (niche, score) in enumerate(ranked, start=1):
        render_niche_card(index, niche, score)
        st.divider()

    st.subheader("Победитель")
    st.success(f"Лучший выбор: {winner.name} (оценка: {winner_score}/10)")

    st.subheader("30-дневный план действий")
    roadmap = build_30_day_plan(winner)
    for stage, tasks in roadmap.items():
        st.markdown(f"#### {stage}")
        for task in tasks:
            st.markdown(f"- {task}")

    st.subheader("KPI на первый месяц")
    st.markdown(
        """
        - 100+ лидов в waitlist
        - 20+ активных пользователей MVP
        - 5+ платящих клиентов
        - 1-2 рабочих канала дистрибуции с прогнозируемым ростом
        """
    )


if __name__ == "__main__":
    main()
