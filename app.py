from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_connection
from ai.planner import generate_plan, generate_timetable
from ai.chatbot import ask_ai

import os
from dotenv import load_dotenv
from openai import OpenAI

app = Flask(__name__)

app.secret_key = "studyplanner123"


@app.route("/")
def home():
    return render_template("index.html")


# ==================================================
# LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        # Account found
        if user:

            # Correct password
            if check_password_hash(user["password"], password):

                session["user_id"] = user["id"]
                session["user_name"] = user["full_name"]

                return redirect(url_for("dashboard"))

            # Wrong password
            else:

                return """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Wrong Password</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            background: #f5f7fa;
                            text-align: center;
                            padding-top: 100px;
                        }

                        .box {
                            background: white;
                            width: 400px;
                            margin: auto;
                            padding: 35px;
                            border-radius: 12px;
                            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
                        }

                        h2 {
                            color: #dc3545;
                        }

                        p {
                            color: #555;
                        }

                        a {
                            display: inline-block;
                            margin-top: 15px;
                            padding: 10px 25px;
                            background: #0d6efd;
                            color: white;
                            text-decoration: none;
                            border-radius: 6px;
                        }

                        a:hover {
                            background: #0b5ed7;
                        }
                    </style>
                </head>

                <body>

                    <div class="box">

                        <h2>❌ Wrong Password</h2>

                        <p>
                            The password you entered is incorrect.
                        </p>

                        <p>
                            Please try again.
                        </p>

                        <a href="/login">
                            🔐 Try Again
                        </a>

                    </div>

                </body>
                </html>
                """

        # Email not found
        else:

            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Account Not Found</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background: #f5f7fa;
                        text-align: center;
                        padding-top: 100px;
                    }

                    .box {
                        background: white;
                        width: 400px;
                        margin: auto;
                        padding: 35px;
                        border-radius: 12px;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
                    }

                    h2 {
                        color: #dc3545;
                    }

                    p {
                        color: #555;
                    }

                    a {
                        display: inline-block;
                        margin-top: 15px;
                        padding: 10px 25px;
                        background: #0d6efd;
                        color: white;
                        text-decoration: none;
                        border-radius: 6px;
                    }
                </style>
            </head>

            <body>

                <div class="box">

                    <h2>❌ Account Not Found</h2>

                    <p>
                        No account was found with this email address.
                    </p>

                    <a href="/login">
                        🔐 Try Again
                    </a>

                </div>

            </body>
            </html>
            """

    # GET request
    return render_template("login.html")


# ==================================================
# DASHBOARD
# ==================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    # Homework Count
    cursor.execute(
        "SELECT COUNT(*) AS total FROM homework WHERE user_id=%s",
        (session["user_id"],)
    )

    homework_count = cursor.fetchone()["total"]

    # Exam Count
    cursor.execute(
        "SELECT COUNT(*) AS total FROM exams WHERE user_id=%s",
        (session["user_id"],)
    )

    exam_count = cursor.fetchone()["total"]

    # Next Upcoming Exam
    cursor.execute("""
        SELECT subject, exam_date
        FROM exams
        WHERE user_id=%s
        ORDER BY exam_date ASC
        LIMIT 1
    """, (session["user_id"],))

    next_exam = cursor.fetchone()

    # Completed Homework
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM homework
        WHERE user_id=%s AND status='Completed'
    """, (session["user_id"],))

    completed = cursor.fetchone()["total"]

    # Pending Homework
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM homework
        WHERE user_id=%s AND status='Pending'
    """, (session["user_id"],))

    pending = cursor.fetchone()["total"]

    # Progress Percentage
    if homework_count > 0:
        progress = int((completed / homework_count) * 100)
    else:
        progress = 0

    # Homework Data for AI
    cursor.execute(
        "SELECT subject, priority, due_date FROM homework WHERE user_id=%s",
        (session["user_id"],)
    )

    homework = cursor.fetchall()

    from datetime import date

    # Today's Due Homework
    cursor.execute("""
        SELECT subject, due_date
        FROM homework
        WHERE user_id=%s
        ORDER BY due_date ASC
        LIMIT 1
    """, (session["user_id"],))

    next_homework = cursor.fetchone()

    # Exam Data for AI
    cursor.execute(
        "SELECT subject FROM exams WHERE user_id=%s",
        (session["user_id"],)
    )

    exams = cursor.fetchall()

    # Routine Data
    cursor.execute("""
        SELECT activity, start_time, end_time
        FROM routine
        WHERE user_id=%s
        ORDER BY start_time
    """, (session["user_id"],))

    routine = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(*) AS total FROM routine WHERE user_id=%s",
        (session["user_id"],)
    )

    routine_count = cursor.fetchone()["total"]

    # AI Plan
    ai_plan = generate_plan(homework, exams, routine)

    timetable = generate_timetable(
        homework,
        exams,
        routine
    )

    # ================= STUDY TIME =================

    cursor.execute("""
        SELECT COALESCE(SUM(study_minutes), 0) AS total_minutes
        FROM study_sessions
        WHERE user_id=%s
    """, (session["user_id"],))

    total_study_minutes = cursor.fetchone()["total_minutes"]

    cursor.execute("""
        SELECT COUNT(*) AS total_sessions
        FROM study_sessions
        WHERE user_id=%s
    """, (session["user_id"],))

    total_sessions = cursor.fetchone()["total_sessions"]

    # ================= STUDY STREAK =================

    cursor.execute("""
        SELECT DISTINCT session_date
        FROM study_sessions
        WHERE user_id=%s
        ORDER BY session_date DESC
    """, (session["user_id"],))

    study_dates = cursor.fetchall()

    streak = 0

    if study_dates:

        from datetime import date, timedelta

        today = date.today()

        latest_date = study_dates[0]["session_date"]

        if latest_date == today or latest_date == today - timedelta(days=1):

            expected_date = latest_date

            for row in study_dates:

                if row["session_date"] == expected_date:

                    streak += 1

                    expected_date = expected_date - timedelta(days=1)

                else:
                    break

    from datetime import date

    def generate_study_plan(user_id):

        conn = get_connection()

        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM homework
            WHERE user_id=%s
            AND status='Pending'
            ORDER BY due_date ASC
        """, (user_id,))

        homework = cursor.fetchall()

        for h in homework:

            cursor.execute("""
                INSERT INTO study_plan
                (user_id, subject, task, plan_date, priority, status)
                VALUES(%s,%s,%s,%s,%s,%s)
            """, (
                user_id,
                h["subject"],
                h["title"],
                date.today(),
                h["priority"],
                "Pending"
            ))

        conn.commit()
        conn.close()

    from datetime import datetime

    reminder = ""

    # Exam Reminder
    if next_exam:

        today = datetime.today().date()

        exam_date = next_exam["exam_date"]

        days = (exam_date - today).days

        if days == 0:

            reminder = (
                f"🔴 Today is your "
                f"{next_exam['subject']} Exam!"
            )

        elif days == 1:

            reminder = (
                f"🟠 Tomorrow is your "
                f"{next_exam['subject']} Exam."
            )

        elif days > 1:

            reminder = (
                f"🟢 {days} days left for "
                f"{next_exam['subject']} Exam."
            )

    # Homework Reminder
    elif next_homework:

        reminder = (
            f"📚 Complete your "
            f"{next_homework['subject']} Homework."
        )

    conn.close()

    return render_template(
        "dashboard.html",
        name=session["user_name"],
        homework_count=homework_count,
        exam_count=exam_count,
        ai_plan=ai_plan,
        timetable=timetable,
        completed=completed,
        pending=pending,
        progress=progress,
        routine_count=routine_count,
        next_exam=next_exam,
        reminder=reminder,
        next_homework=next_homework,
        total_study_minutes=total_study_minutes,
        total_sessions=total_sessions,
        streak=streak
    )


# ==================================================
# HOMEWORK
# ==================================================

@app.route("/homework")
def homework():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM homework "
        "WHERE user_id=%s "
        "ORDER BY due_date ASC",
        (session["user_id"],)
    )

    homework_list = cursor.fetchall()

    conn.close()

    return render_template(
        "homework.html",
        homework_list=homework_list
    )


# ==================================================
# EDIT HOMEWORK
# ==================================================

@app.route("/edit_homework/<int:id>", methods=["GET", "POST"])
def edit_homework(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        subject = request.form["subject"]
        title = request.form["title"]
        description = request.form["description"]
        due_date = request.form["due_date"]
        priority = request.form["priority"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE homework
            SET subject=%s,
                title=%s,
                description=%s,
                due_date=%s,
                priority=%s,
                status=%s
            WHERE id=%s AND user_id=%s
        """, (
            subject,
            title,
            description,
            due_date,
            priority,
            status,
            id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("homework"))

    cursor.execute(
        "SELECT * FROM homework "
        "WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )

    hw = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_homework.html",
        hw=hw
    )


# ==================================================
# DELETE HOMEWORK
# ==================================================

@app.route("/delete_homework/<int:id>")
def delete_homework(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM homework "
        "WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect(url_for("homework"))


# ==================================================
# EXAMS
# ==================================================

@app.route("/exams")
def exams():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM exams "
        "WHERE user_id=%s "
        "ORDER BY exam_date ASC",
        (session["user_id"],)
    )

    exam_list = cursor.fetchall()

    conn.close()

    return render_template(
        "exams.html",
        exam_list=exam_list
    )


# ==================================================
# ADD EXAM
# ==================================================

@app.route("/add_exam", methods=["GET", "POST"])
def add_exam():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        subject = request.form["subject"]
        exam_date = request.form["exam_date"]
        exam_time = request.form["exam_time"]
        syllabus = request.form["syllabus"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO exams
            (user_id, subject, exam_date, exam_time, syllabus)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            subject,
            exam_date,
            exam_time,
            syllabus
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("exams"))

    return render_template("add_exam.html")


# ==================================================
# ADD HOMEWORK
# ==================================================

@app.route("/add_homework", methods=["GET", "POST"])
def add_homework():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        subject = request.form["subject"]
        title = request.form["title"]
        description = request.form["description"]
        due_date = request.form["due_date"]
        priority = request.form["priority"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO homework
            (user_id, subject, title, description, due_date, priority)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            session["user_id"],
            subject,
            title,
            description,
            due_date,
            priority
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("homework"))

    return render_template("add_homework.html")


# ==================================================
# REGISTER
# ==================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Password Match Check
        if password != confirm_password:
            return "Passwords do not match"

        # Hash Password
        hashed_password = generate_password_hash(password)

        # Database Connection
        conn = get_connection()
        cursor = conn.cursor()

        # Duplicate Email Check
        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        if user:

            conn.close()

            return "Email already exists!"

        # Insert User
        cursor.execute(
            "INSERT INTO users(full_name,email,password) "
            "VALUES(%s,%s,%s)",
            (
                full_name,
                email,
                hashed_password
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ==================================================
# ROUTINE
# ==================================================

@app.route("/routine")
def routine():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM routine "
        "WHERE user_id=%s "
        "ORDER BY start_time",
        (session["user_id"],)
    )

    routine_list = cursor.fetchall()

    conn.close()

    return render_template(
        "routine.html",
        routine_list=routine_list
    )


# ==================================================
# ADD ROUTINE
# ==================================================

@app.route("/add_routine", methods=["GET", "POST"])
def add_routine():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        activity = request.form["activity"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        day = request.form["day"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO routine
            (user_id, activity, start_time, end_time, day)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            activity,
            start_time,
            end_time,
            day
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("routine"))

    return render_template("add_routine.html")


# ==================================================
# EDIT ROUTINE
# ==================================================

@app.route("/edit_routine/<int:id>", methods=["GET", "POST"])
def edit_routine(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        activity = request.form["activity"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        day = request.form["day"]

        cursor.execute("""
            UPDATE routine
            SET activity=%s,
                start_time=%s,
                end_time=%s,
                day=%s
            WHERE id=%s AND user_id=%s
        """, (
            activity,
            start_time,
            end_time,
            day,
            id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("routine"))

    cursor.execute(
        "SELECT * FROM routine "
        "WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )

    routine = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_routine.html",
        routine=routine
    )


# ==================================================
# DELETE ROUTINE
# ==================================================

@app.route("/delete_routine/<int:id>")
def delete_routine(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM routine "
        "WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect(url_for("routine"))


# ==================================================
# ALARM SYSTEM
# ==================================================

@app.route("/alarms")
def alarms():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM alarms
        WHERE user_id=%s
        ORDER BY alarm_date ASC, alarm_time ASC
    """, (session["user_id"],))

    alarm_list = cursor.fetchall()

    conn.close()

    return render_template(
        "alarms.html",
        alarm_list=alarm_list
    )


# ==================================================
# ADD ALARM
# ==================================================

@app.route("/add_alarm", methods=["GET", "POST"])
def add_alarm():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        alarm_date = request.form["alarm_date"]
        alarm_time = request.form["alarm_time"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO alarms
            (user_id, title, description, alarm_date, alarm_time)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            title,
            description,
            alarm_date,
            alarm_time
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("alarms"))

    return render_template("add_alarm.html")


# ==================================================
# POMODORO
# ==================================================

@app.route("/pomodoro")
def pomodoro():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("pomodoro.html")


# ==================================================
# STUDY TIME TRACKER
# ==================================================

@app.route("/save_study_session", methods=["POST"])
def save_study_session():

    if "user_id" not in session:
        return {
            "success": False,
            "message": "Please login first"
        }

    data = request.get_json()

    minutes = int(data.get("minutes", 0))

    if minutes <= 0:

        return {
            "success": False,
            "message": "Invalid study time"
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO study_sessions
        (user_id, study_minutes, session_date)
        VALUES (%s, %s, CURDATE())
    """, (
        session["user_id"],
        minutes
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Study session saved"
    }


# ==================================================
# DELETE ALARM
# ==================================================

@app.route("/delete_alarm/<int:id>")
def delete_alarm(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM alarms
        WHERE id=%s AND user_id=%s
    """, (
        id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("alarms"))


# ==================================================
# AI CHAT ASSISTANT
# ==================================================

@app.route("/chat", methods=["GET", "POST"])
def chat():

    answer = ""

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        question = request.form["question"].strip()

        if question:

            try:

                # ================= USER STUDY DATA =================

                conn = get_connection()
                cursor = conn.cursor()

                user_id = session["user_id"]

                # Homework
                cursor.execute("""
                    SELECT subject, title, due_date, priority, status
                    FROM homework
                    WHERE user_id=%s
                    ORDER BY due_date ASC
                """, (user_id,))

                homework = cursor.fetchall()

                # Exams
                cursor.execute("""
                    SELECT subject, exam_date, exam_time, syllabus
                    FROM exams
                    WHERE user_id=%s
                    ORDER BY exam_date ASC
                """, (user_id,))

                exams = cursor.fetchall()

                # Routine
                cursor.execute("""
                    SELECT activity, start_time, end_time, day
                    FROM routine
                    WHERE user_id=%s
                    ORDER BY start_time ASC
                """, (user_id,))

                routine = cursor.fetchall()

                # Study Progress
                cursor.execute("""
                    SELECT COUNT(*) AS total
                    FROM homework
                    WHERE user_id=%s
                """, (user_id,))

                total = cursor.fetchone()["total"]

                cursor.execute("""
                    SELECT COUNT(*) AS completed
                    FROM homework
                    WHERE user_id=%s
                    AND status='Completed'
                """, (user_id,))

                completed = cursor.fetchone()["completed"]

                pending = total - completed

                if total > 0:
                    progress = round(
                        (completed / total) * 100
                    )
                else:
                    progress = 0

                # Study Time
                cursor.execute("""
                    SELECT COALESCE(SUM(study_minutes), 0)
                    AS total_minutes
                    FROM study_sessions
                    WHERE user_id=%s
                """, (user_id,))

                total_study_minutes = cursor.fetchone()["total_minutes"]

                # Study Sessions
                cursor.execute("""
                    SELECT COUNT(*) AS total_sessions
                    FROM study_sessions
                    WHERE user_id=%s
                """, (user_id,))

                total_sessions = cursor.fetchone()["total_sessions"]

                # Close database
                conn.close()

                # ================= AI CONTEXT =================

                context = f"""

STUDENT STUDY INFORMATION

HOMEWORK:
{homework}

EXAMS:
{exams}

ROUTINE:
{routine}

PROGRESS:
Total Homework: {total}
Completed: {completed}
Pending: {pending}
Progress: {progress}%

STUDY TIME:
Total Study Minutes: {total_study_minutes}
Study Sessions: {total_sessions}

"""

                # ================= ASK AI =================

                ai_answer = ask_ai(
                    question,
                    context
                )

                answer = (
                    "🤖 <b>AI Study Assistant</b>"
                    "<br><br>"
                    + ai_answer
                )

            except Exception as e:

                answer = (
                    "❌ <b>AI Error:</b><br><br>"
                    + str(e)
                )

        else:

            answer = "⚠️ Please enter your question."

    return render_template(
        "chat.html",
        answer=answer
    )


# ==================================================
# AI QUIZ GENERATOR
# ==================================================

from ai.chatbot import ask_ai


# ==================================================
# AI QUIZ GENERATOR
# ==================================================

@app.route("/quiz", methods=["GET", "POST"])
def quiz():

    if request.method == "POST":

        subject = request.form.get("subject")
        topic = request.form.get("topic")

        num_questions = int(
            request.form.get("num_questions") or 10
        )


        prompt = f"""
Create a multiple-choice quiz.

Subject: {subject}
Topic: {topic}

Create exactly {num_questions} questions.

Return ONLY valid JSON.

The JSON must have this exact format:

[
    {{
        "question": "Question text",
        "option_a": "Option A",
        "option_b": "Option B",
        "option_c": "Option C",
        "option_d": "Option D",
        "correct_answer": "A"
    }}
]

Rules:

1. Create exactly {num_questions} questions.
2. Every question must have exactly 4 options.
3. correct_answer must be only A, B, C or D.
4. Do not use markdown.
5. Do not use ```json.
6. Do not add explanations.
"""


        try:

            ai_result = ask_ai(
                prompt,
                raw=True
            )


            print("===================================")
            print("AI QUIZ RESPONSE:")
            print(ai_result)
            print("===================================")


            if not ai_result:

                return render_template(
                    "quiz.html",
                    error="❌ AI service is currently unavailable. Please try again."
                )


            if "AI service is currently unavailable" in ai_result:

                return render_template(
                    "quiz.html",
                    error="❌ AI service is currently unavailable. Please try again."
                )


            import json

            ai_result = ai_result.strip()


            # Remove markdown code block if AI adds it

            if ai_result.startswith("```json"):

                ai_result = ai_result[7:]


            elif ai_result.startswith("```"):

                ai_result = ai_result[3:]


            if ai_result.endswith("```"):

                ai_result = ai_result[:-3]


            ai_result = ai_result.strip()


            # Convert JSON to Python list

            questions = json.loads(ai_result)


            # Check questions

            if not isinstance(questions, list):

                raise ValueError(
                    "AI did not return a valid question list."
                )


            if len(questions) == 0:

                raise ValueError(
                    "AI returned zero questions."
                )


            # ===============================
            # SAVE QUIZ IN SESSION
            # ===============================

            session["quiz_questions"] = questions

            session["quiz_subject"] = subject

            session["quiz_topic"] = topic


            print("===================================")
            print("QUESTIONS SAVED IN SESSION:")
            print(session.get("quiz_questions"))
            print("===================================")


            return render_template(
                "quiz_questions.html",
                questions=questions,
                subject=subject,
                topic=topic
            )


        except Exception as e:

            print("QUIZ ERROR:", e)


            return render_template(
                "quiz.html",
                error="Unable to generate quiz: " + str(e)
            )


    return render_template("quiz.html")
# ==================================================
# QUIZ RESULT
# ==================================================

@app.route("/quiz/result", methods=["POST"])
def quiz_result():

    try:

        # ============================================
        # LOGIN CHECK
        # ============================================

        user_id = session.get("user_id")

        if not user_id:
            return redirect(url_for("login"))

        # ============================================
        # GET QUIZ DATA FROM SESSION
        # ============================================

        questions = session.get("quiz_questions")
        subject = session.get("quiz_subject", "")
        topic = session.get("quiz_topic", "")

        print("====================================")
        print("QUIZ RESULT")
        print("QUESTIONS FROM SESSION:")
        print(questions)
        print("SUBJECT:", subject)
        print("TOPIC:", topic)
        print("====================================")

        # ============================================
        # CHECK QUESTIONS
        # ============================================

        if not questions:

            return render_template(
                "quiz.html",
                error="❌ Quiz questions data is missing. Please generate the quiz again."
            )

        # ============================================
        # CALCULATE SCORE
        # ============================================

        total_questions = len(questions)

        correct_answers = 0

        for index, question in enumerate(questions, start=1):

            user_answer = request.form.get(
                f"q{index}"
            )

            correct_answer = question.get(
                "correct_answer"
            )

            print(
                f"Q{index}: User={user_answer}, "
                f"Correct={correct_answer}"
            )

            if user_answer == correct_answer:
                correct_answers += 1

        # ============================================
        # PERCENTAGE
        # ============================================

        if total_questions > 0:

            percentage = round(
                (correct_answers / total_questions) * 100,
                2
            )

        else:

            percentage = 0

        print("TOTAL:", total_questions)
        print("CORRECT:", correct_answers)
        print("PERCENTAGE:", percentage)

        # ============================================
        # DATABASE
        # ============================================

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO quiz_results
            (
                user_id,
                subject,
                topic,
                total_questions,
                correct_answers,
                score,
                percentage
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                user_id,
                subject,
                topic,
                total_questions,
                correct_answers,
                correct_answers,
                percentage
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        print("✅ QUIZ RESULT SAVED TO DATABASE")

        # ============================================
        # CLEAR QUIZ SESSION
        # ============================================

        session.pop("quiz_questions", None)
        session.pop("quiz_subject", None)
        session.pop("quiz_topic", None)

        # ============================================
        # SHOW RESULT PAGE
        # ============================================

        return render_template(
            "quiz_result.html",
            subject=subject,
            topic=topic,
            score=correct_answers,
            total=total_questions,
            percentage=percentage
        )

    except Exception as e:

        print("❌ QUIZ RESULT ERROR:", e)

        return f"""
        <div style="font-family: Arial; padding: 40px;">
            <h2 style="color:red;">
                ❌ Quiz Result Error
            </h2>

            <p>
                {str(e)}
            </p>

            <a href="/quiz">
                Generate Quiz Again
            </a>
        </div>
        """
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)