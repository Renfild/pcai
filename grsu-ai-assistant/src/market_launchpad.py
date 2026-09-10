"""
Streamlit-инструмент для автономного выбора рыночной ниши и сборки MVP-плана.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

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


@dataclass(frozen=True)
class RankedNiche:
    niche: Niche
    score: float
    breakdown: Dict[str, float]


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

METRIC_LABELS: Dict[str, str] = {
    "demand": "Спрос",
    "competition": "Конкуренция",
    "monetization": "Монетизация",
    "virality": "Виральность",
    "build_speed": "Скорость сборки",
}


def score_niche(niche: Niche, time_per_day: int, budget: int, risk_tolerance: int) -> RankedNiche:
    """Считает оценку ниши и вклад каждого фактора."""
    competition_input = niche.scores["competition"] if risk_tolerance >= 7 else max(1, 11 - niche.scores["competition"])
    competition_weight = WEIGHTS["competition"] * (1.6 if risk_tolerance <= 3 else 1.0)

    breakdown = {
        "demand": niche.scores["demand"] * WEIGHTS["demand"],
        "competition": competition_input * competition_weight,
        "monetization": niche.scores["monetization"] * WEIGHTS["monetization"],
        "virality": niche.scores["virality"] * WEIGHTS["virality"],
        "build_speed": niche.scores["build_speed"] * WEIGHTS["build_speed"],
    }

    if budget < 100:
        breakdown["budget_fit"] = -0.4
    elif budget > 700:
        breakdown["budget_fit"] = 0.2
    else:
        breakdown["budget_fit"] = 0.0

    if time_per_day < 2:
        breakdown["time_fit"] = -((10 - niche.scores["build_speed"]) * 0.08)
    elif time_per_day >= 4:
        breakdown["time_fit"] = 0.2
    else:
        breakdown["time_fit"] = 0.0

    total = round(sum(breakdown.values()), 2)
    return RankedNiche(niche=niche, score=total, breakdown=breakdown)


def evaluate_niches(time_per_day: int, budget: int, risk_tolerance: int) -> List[RankedNiche]:
    """Возвращает ранжированный список ниш."""
    ranked = [score_niche(niche, time_per_day, budget, risk_tolerance) for niche in NICHES]
    return sorted(ranked, key=lambda item: item.score, reverse=True)


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


def build_first_48h_sprint(best_niche: Niche) -> List[str]:
    """Приоритетные задачи на первые 48 часов."""
    return [
        f"Описать ICP: {best_niche.audience}",
        "Собрать MVP-лендинг + форму заявки за 1 день",
        f"Подготовить 3 оффера под каналы: {', '.join(best_niche.channels[:3])}",
        "Сделать 20 персональных outreach-сообщений потенциальным первым пользователям",
        "Назначить 5 созвонов для customer discovery",
    ]


def build_launch_brief(
    winner: RankedNiche,
    roadmap: Dict[str, List[str]],
    sprint_48h: List[str],
    time_per_day: int,
    budget: int,
    risk_tolerance: int,
) -> str:
    """Формирует копируемый launch brief."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Launch Brief",
        f"Generated: {ts}",
        "",
        "## Input",
        f"- Time per day: {time_per_day}h",
        f"- Budget: ${budget}",
        f"- Risk tolerance: {risk_tolerance}/10",
        "",
        "## Best Niche",
        f"- Name: {winner.niche.name}",
        f"- Score: {winner.score}/10",
        f"- Audience: {winner.niche.audience}",
        f"- Pain: {winner.niche.pain}",
        f"- MVP: {winner.niche.mvp}",
        f"- Monetization: {winner.niche.monetization}",
        "",
        "## First 48h Sprint",
    ]

    lines.extend([f"- {item}" for item in sprint_48h])
    lines.append("")
    lines.append("## 30-day Plan")

    for stage, tasks in roadmap.items():
        lines.append(f"### {stage}")
        lines.extend([f"- {task}" for task in tasks])

    return "\n".join(lines)


def render_niche_card(rank: int, ranked: RankedNiche, best_score: float) -> None:
    niche = ranked.niche
    st.markdown(f"### {rank}. {niche.name} — {ranked.score}/10")
    st.progress(min(1.0, ranked.score / max(best_score, 1)))
    st.write(f"**Аудитория:** {niche.audience}")
    st.write(f"**Проблема:** {niche.pain}")
    st.write(f"**MVP:** {niche.mvp}")
    st.write(f"**Монетизация:** {niche.monetization}")
    st.write(f"**Каналы роста:** {', '.join(niche.channels)}")


def render_score_explainer(winner: RankedNiche) -> None:
    st.subheader("Почему победила эта ниша")
    metric_rows = []
    for key in ["demand", "competition", "monetization", "virality", "build_speed"]:
        metric_rows.append({"Фактор": METRIC_LABELS[key], "Вклад": round(winner.breakdown.get(key, 0.0), 2)})

    st.table(metric_rows)
    st.caption(
        f"Поправка бюджета: {winner.breakdown.get('budget_fit', 0.0):+.2f} | "
        f"Поправка по времени: {winner.breakdown.get('time_fit', 0.0):+.2f}"
    )


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
    winner = ranked[0]

    st.subheader("Топ-3 ниши по текущим условиям")
    for index, ranked_niche in enumerate(ranked, start=1):
        render_niche_card(index, ranked_niche, winner.score)
        st.divider()

    st.subheader("Победитель")
    st.success(f"Лучший выбор: {winner.niche.name} (оценка: {winner.score}/10)")

    render_score_explainer(winner)

    roadmap = build_30_day_plan(winner.niche)
    st.subheader("30-дневный план действий")
    for stage, tasks in roadmap.items():
        st.markdown(f"#### {stage}")
        for task in tasks:
            st.markdown(f"- {task}")

    sprint_48h = build_first_48h_sprint(winner.niche)
    st.subheader("Первые 48 часов")
    for task in sprint_48h:
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

    launch_brief = build_launch_brief(winner, roadmap, sprint_48h, time_per_day, budget, risk_tolerance)
    st.subheader("Launch Brief")
    st.code(launch_brief, language="markdown")
    st.download_button(
        label="Скачать launch_brief.md",
        data=launch_brief,
        file_name="launch_brief.md",
        mime="text/markdown",
    )


if __name__ == "__main__":
    main()
