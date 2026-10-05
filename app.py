import random
import sqlite3
from deap import base, creator, tools
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="School Timetable Optimizer (Classes 6-12)",
    page_icon="🏫",
    layout="wide",
)

st.title("🏫 AI School Timetable Optimizer (Smart Subject & Faculty Lists)")
st.write(
    "Manage school schedules across 30 weekly slots (6 periods/day $\\times$"
    " 5 days) using reusable subject and teacher lists."
)


# --- Database Setup & Management Functions ---
def init_db():
  conn = sqlite3.connect("timetable_sections.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            section TEXT NOT NULL,
            subject TEXT NOT NULL,
            teacher TEXT NOT NULL
        )
    """)

  # Auto-populate default curriculum with sections if empty
  cursor.execute("SELECT COUNT(*) FROM lessons")
  if cursor.fetchone()[0] == 0:
    default_curriculum = []
    classes = [
        "Class 6",
        "Class 7",
        "Class 8",
        "Class 9",
        "Class 10",
        "Class 11",
        "Class 12",
    ]
    sections = ["A", "B"]

    subjects_map = {
        "Mathematics": ["Mr. Roy", "Mr. Gupta"],
        "English": ["Ms. Bose", "Mrs. Dutta"],
        "Science / Physics": ["Mrs. Sen", "Dr. Banerjee"],
        "History / Geography": ["Mr. Das", "Ms. Mukherjee"],
        "Second Language": ["Mrs. Chatterjee", "Mr. Ghosh"],
        "Computer Science": ["Tanmoy Sir", "Mr. Sharma"],
    }

    for cls in classes:
      for sec in sections:
        for subj, teachers in subjects_map.items():
          for i in range(3):
            teacher = teachers[(i + hash(sec)) % len(teachers)]
            default_curriculum.append((cls, sec, subj, teacher))

    cursor.executemany(
        """
            INSERT INTO lessons (class_name, section, subject, teacher) 
            VALUES (?, ?, ?, ?)
        """,
        default_curriculum,
    )
    conn.commit()
  conn.close()


def add_lesson_to_db(class_name, section, subject, teacher):
  conn = sqlite3.connect("timetable_sections.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO lessons (class_name, section, subject, teacher) 
        VALUES (?, ?, ?, ?)
    """,
      (class_name, section, subject, teacher),
  )
  conn.commit()
  conn.close()


def reset_default_db():
  conn = sqlite3.connect("timetable_sections.db")
  cursor = conn.cursor()
  cursor.execute("DROP TABLE IF EXISTS lessons")
  conn.commit()
  conn.close()
  init_db()


def load_lessons_from_db():
  conn = sqlite3.connect("timetable_sections.db")
  query = "SELECT id, class_name, section, subject, teacher FROM lessons"
  df_db = pd.read_sql(query, conn)
  conn.close()

  lessons = []
  for _, row in df_db.iterrows():
    lessons.append({
        "id": row["id"],
        "class": row["class_name"],
        "section": row["section"],
        "subject": row["subject"],
        "teacher": row["teacher"],
    })
  return lessons


def get_distinct_subjects_teachers():
  conn = sqlite3.connect("timetable_sections.db")
  cursor = conn.cursor()
  cursor.execute("SELECT DISTINCT subject FROM lessons ORDER BY subject")
  subjects = [row[0] for row in cursor.fetchall()]
  cursor.execute("SELECT DISTINCT teacher FROM lessons ORDER BY teacher")
  teachers = [row[0] for row in cursor.fetchall()]
  conn.close()
  return subjects, teachers


# Initialize DB
init_db()

# --- Sidebar: Optimization Controls ---
st.sidebar.header("⚙️ AI Parameters")
pop_size = st.sidebar.slider(
    "Population Size", min_value=50, max_value=500, value=200, step=50
)
ngen = st.sidebar.slider(
    "Generations", min_value=20, max_value=200, value=80, step=20
)
mut_pb = st.sidebar.slider(
    "Mutation Probability", min_value=0.01, max_value=0.3, value=0.15, step=0.05
)

run_button = st.sidebar.button(
    "🚀 Run AI Optimizer", type="primary", use_container_width=True
)

# --- Main Page: Data Management ---
st.header("📚 Curriculum Management (Smart Dropdowns)")

col_btn1, col_btn2 = st.columns([2, 2])
with col_btn1:
  if st.button("🔄 Reset to Default Template"):
    reset_default_db()
    st.success("Reset database to standard Classes 6-12 template!")
    st.rerun()

lessons = load_lessons_from_db()
existing_subjects, existing_teachers = get_distinct_subjects_teachers()

st.info(
    f"Loaded **{len(lessons)} lessons** | **{len(existing_subjects)} Subjects"
    f" available** | **{len(existing_teachers)} Teachers available**."
)

# Smart Add Lesson Form
with st.expander(
    "➕ Add Lesson (Using Existing or New Subjects/Teachers)", expanded=True
):
  with st.form("add_custom_lesson"):
    c1, c2 = st.columns(2)
    with c1:
      c_in = st.selectbox(
          "Class",
          [
              "Class 6",
              "Class 7",
              "Class 8",
              "Class 9",
              "Class 10",
              "Class 11",
              "Class 12",
          ],
      )
    with c2:
      sec_in = st.selectbox("Section", ["A", "B", "C", "D"])

    c3, c4 = st.columns(2)
    with c3:
      subject_options = existing_subjects + ["+ Add New Subject..."]
      selected_subject = st.selectbox("Select Subject", subject_options)
      if selected_subject == "+ Add New Subject...":
        new_subject_input = st.text_input("Enter New Subject Name")
      else:
        new_subject_input = ""

    with c4:
      teacher_options = existing_teachers + ["+ Add New Teacher..."]
      selected_teacher = st.selectbox("Select Teacher", teacher_options)
      if selected_teacher == "+ Add New Teacher...":
        new_teacher_input = st.text_input("Enter New Teacher Name")
      else:
        new_teacher_input = ""

    submitted = st.form_submit_button("Add Lesson to Database")
    if submitted:
      final_subject = (
          new_subject_input.strip()
          if selected_subject == "+ Add New Subject..."
          else selected_subject
      )
      final_teacher = (
          new_teacher_input.strip()
          if selected_teacher == "+ Add New Teacher..."
          else selected_teacher
      )

      if final_subject and final_teacher:
        add_lesson_to_db(c_in, sec_in, final_subject, final_teacher)
        st.success(
            f"Added: {final_subject} for {c_in} Sec {sec_in} taught by"
            f" {final_teacher}!"
        )
        st.rerun()
      else:
        st.error("Please provide valid subject and teacher names.")

st.markdown("---")

# --- Time Slot Architecture (6 periods/day * 5 days = 30 slots) ---
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
periods_per_day = 6
total_slots = len(days) * periods_per_day

# --- Execution of Optimizer ---
if run_button:
  if len(lessons) == 0:
    st.error("No lessons found in the database!")
  else:
    with st.spinner(
        f"Evolving complex schedule for {len(lessons)} lessons across 30"
        " slots..."
    ):

      # 1. DEAP Setup
      if "FitnessMin" in creator.__dict__:
        del creator.FitnessMin
      if "Individual" in creator.__dict__:
        del creator.Individual

      creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
      creator.create("Individual", list, fitness=creator.FitnessMin)

      toolbox = base.Toolbox()
      toolbox.register("attr_int", random.randint, 0, total_slots - 1)
      toolbox.register(
          "individual",
          tools.initRepeat,
          creator.Individual,
          toolbox.attr_int,
          n=len(lessons),
      )
      toolbox.register("population", tools.initRepeat, list, toolbox.individual)


      # 2. Fitness / Conflict Evaluation Function
      def evalTimetable(individual):
        conflicts = 0
        teacher_schedule = {}
        section_schedule = {}

        for lesson_idx, slot in enumerate(individual):
          lesson = lessons[lesson_idx]
          teacher = lesson["teacher"]
          cls = lesson["class"]
          sec = lesson["section"]

          t_key = (teacher, slot)
          teacher_schedule[t_key] = teacher_schedule.get(t_key, 0) + 1
          if teacher_schedule[t_key] > 1:
            conflicts += 20

          sec_key = (cls, sec, slot)
          section_schedule[sec_key] = section_schedule.get(sec_key, 0) + 1
          if section_schedule[sec_key] > 1:
            conflicts += 20

        return (conflicts,)


      toolbox.register("evaluate", evalTimetable)
      toolbox.register("mate", tools.cxTwoPoint)
      toolbox.register(
          "mutate",
          tools.mutUniformInt,
          low=0,
          up=total_slots - 1,
          indpb=mut_pb,
      )
      toolbox.register("select", tools.selTournament, tournsize=3)

      # 3. Evolution Loop
      pop = toolbox.population(n=pop_size)
      fitnesses = list(map(toolbox.evaluate, pop))
      for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

      min_fitness_history = []

      for generation in range(ngen):
        offspring = toolbox.select(pop, len(pop))
        offspring = [toolbox.clone(ind) for ind in offspring]

        for child1, child2 in zip(offspring[::2], offspring[1::2]):
          if random.random() < 0.8:
            toolbox.mate(child1, child2)
            del child1.fitness.values
            del child2.fitness.values

        for mutant in offspring:
          if random.random() < mut_pb:
            toolbox.mutate(mutant)
            del mutant.fitness.values

        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = list(map(toolbox.evaluate, invalid_ind))
        for ind, fit in zip(invalid_ind, fitnesses):
          ind.fitness.values = fit

        pop[:] = offspring

        fits = [ind.fitness.values[0] for ind in pop]
        min_fitness_history.append(min(fits))

      # 4. Extract Best Solution
      best_individual = tools.selBest(pop, k=1)[0]
      best_conflicts = best_individual.fitness.values[0]

      # --- Display Results & Charts ---
      st.header("📊 Step 2: Optimization Results & Convergence Chart")

      if best_conflicts == 0:
        st.success(
            "🎉 Perfect conflict-free master timetable generated for all"
            " sections!"
        )
      else:
        st.warning(
            f"⚠️ Optimization completed with {int(best_conflicts)} minor"
            " scheduling clashes."
        )

      col_m1, col_m2 = st.columns(2)
      with col_m1:
        st.metric("Total Conflicts", int(best_conflicts))
      with col_m2:
        st.metric("Total Scheduled Lessons", len(lessons))

      # --- Convergence Chart ---
      st.subheader("📈 Genetic Algorithm Convergence Chart")
      fig, ax = plt.subplots(figsize=(10, 4))
      ax.plot(
          min_fitness_history,
          color="crimson",
          linewidth=2.5,
          label="Conflict Penalty Score",
      )
      ax.set_title(
          "Reduction of Scheduling Conflicts Across Generations", fontsize=12
      )
      ax.set_xlabel("Generation", fontsize=10)
      ax.set_ylabel("Total Conflict Penalty (Lower is Better)", fontsize=10)
      ax.grid(True, linestyle="--", alpha=0.6)
      ax.legend()
      st.pyplot(fig)
      plt.close(fig)

      # Build full result dataset
      schedule_data = []
      for lesson_idx, slot in enumerate(best_individual):
        day_idx = slot // periods_per_day
        period_idx = slot % periods_per_day
        lesson = lessons[lesson_idx]

        schedule_data.append({
            "Day": days[day_idx] if day_idx < len(days) else "Overflow",
            "Period": f"Period {period_idx + 1}",
            "Class": lesson["class"],
            "Section": lesson["section"],
            "Subject": lesson["subject"],
            "Teacher": lesson["teacher"],
        })

      df_result = pd.DataFrame(schedule_data)

      # --- Class & Section-Wise Tabbed View ---
      st.subheader("🏫 View Timetable Matrix By Class & Section")

      df_result["Class_Section"] = (
          df_result["Class"] + " - Section " + df_result["Section"]
      )
      active_groupings = sorted(df_result["Class_Section"].unique())
      section_tabs = st.tabs(active_groupings)

      period_columns = [f"Period {i}" for i in range(1, periods_per_day + 1)]

      for idx, group_name in enumerate(active_groupings):
        with section_tabs[idx]:
          st.markdown(f"### 📌 Timetable Matrix for {group_name}")
          df_grp = df_result[df_result["Class_Section"] == group_name]

          matrix_data = {
              "Day": days,
              **{p: ["-"] * len(days) for p in period_columns},
          }

          for _, row in df_grp.iterrows():
            d = row["Day"]
            p = row["Period"]
            cell_text = f"{row['Subject']} \n({row['Teacher']})"

            if d in days and p in period_columns:
              day_row_idx = days.index(d)
              existing = matrix_data[p][day_row_idx]
              if existing == "-":
                matrix_data[p][day_row_idx] = cell_text
              else:
                matrix_data[p][day_row_idx] = f"{existing} / \n{cell_text}"

          df_matrix = pd.DataFrame(matrix_data)
          df_matrix.set_index("Day", inplace=True)
          st.dataframe(df_matrix, use_container_width=True)