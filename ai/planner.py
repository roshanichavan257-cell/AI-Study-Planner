from datetime import datetime

def generate_plan(homework, exams, routine):

    plan = []

    # Daily Routine
    plan.append("📅 Today's Routine")

    for r in routine:
        plan.append(
            f"⏰ {r['start_time']} - {r['end_time']} : {r['activity']}"
        )

    plan.append("")

    # High Priority Homework
    high = []
    medium = []
    low = []

    for hw in homework:

        if hw["priority"] == "High":
            high.append(hw)

        elif hw["priority"] == "Medium":
            medium.append(hw)

        else:
            low.append(hw)

    plan.append("🔥 High Priority")

    for hw in high:
        plan.append(
            f"📖 {hw['subject']} (2 Hours)"
        )

    plan.append("")

    plan.append("📘 Medium Priority")

    for hw in medium:
        plan.append(
            f"📘 {hw['subject']} (1 Hour)"
        )

    plan.append("")

    plan.append("📗 Low Priority")

    for hw in low:
        plan.append(
            f"📗 {hw['subject']} (30 Minutes)"
        )

    plan.append("")

    plan.append("📝 Upcoming Exams")

    for exam in exams:
        plan.append(
            f"Revise {exam['subject']}"
        )

    return plan
def generate_timetable(homework, exams, routine):

    timetable = []

    for r in routine:
        timetable.append(
            f"{r['start_time']} - {r['end_time']} : {r['activity']}"
        )

    for hw in homework:
        timetable.append(
            f"Study {hw['subject']}"
        )

    return timetable