import random
import sqlite3
from deap import base, creator, tools
import matplotlib
matplotlib.use('Agg')  # Headless backend for cloud compatibility
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI School Timetable Optimizer",
    page_icon="📅",
    layout="wide"
)

DB_NAME = "timetable_sections.db"

# --- DATABASE SETUP ---
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Subjects Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    
    # 2. Faculty Table (Independent teacher-to-subject mapping, NO class/section required)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_name TEXT NOT NULL,
            subject TEXT NOT NULL
        )
    """)
    
    # 3. Lessons / Timetable Requirements Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            section TEXT NOT NULL,
            subject TEXT NOT NULL,
            teacher TEXT NOT NULL
        )
    """)
    conn.commit()
    
    # Populate default data if empty
    cursor.execute("SELECT COUNT(*) FROM subjects")
    if cursor.fetchone()[0] == 0:
        default_subjects = [
            "Mathematics", "English", "Science / Physics", 
            "Chemistry", "History / Geography", "Second Language", "Computer Science"
        ]
        for subj in default_subjects:
            cursor.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?)", (subj,))
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM faculty")
    if cursor.fetchone()[0] == 0:
        default_faculty = [
            ("Mr. Roy", "Mathematics"), ("Mr. Gupta", "Mathematics"),
            ("Ms. Bose", "English"), ("Mrs. Dutta", "English"),
            ("Mrs. Sen", "Science / Physics"), ("Dr. Banerjee", "Science / Physics"),
            ("Dr. Banerjee", "Chemistry"), ("Mr. Alok Roy", "Chemistry"),
            ("Mr. Das", "History / Geography"), ("Ms. Mukherjee", "History / Geography"),
            ("Mrs. Chatterjee", "Second Language"), ("Mr. Ghosh", "Second Language"),
            ("Tanmoy Sir", "Computer Science"), ("Mr. Sharma", "Computer Science")
        ]
        cursor.executemany("INSERT INTO faculty (teacher_name, subject) VALUES (?, ?)", default_faculty)
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM lessons")
    if cursor.fetchone()[0] == 0:
        classes = ["Class 6", "Class 7", "Class 8", "Class 9", "Class 10", "Class 11", "Class 12"]
        sections = ["A", "B"]
        
        default_lessons = []
        for cls in classes:
            for sec in sections:
                cursor.execute("SELECT teacher_name, subject FROM faculty")
                fac_list = cursor.fetchall()
                # Assign a few sample lessons per section from the faculty pool
                for teacher, subj in fac_list[:6]:  # Pick subset for default template
                    default_lessons.append((cls, sec, subj, teacher))
                    
        cursor.executemany("INSERT INTO lessons (class_name, section, subject, teacher) VALUES (?, ?, ?, ?)", default_lessons)
        conn.commit()
        
    conn.close()

init_db()

# --- DATABASE HELPER FUNCTIONS ---
def get_all_subjects():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM subjects ORDER BY name")
    subjects = [row[0] for row in cursor.fetchall()]
    conn.close()
    return subjects

def add_subject_to_db(subject_name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO subjects (name) VALUES (?)", (subject_name.strip(),))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_all_faculty():
    conn = get_connection()
    df = pd.read_sql("SELECT id, teacher_name, subject FROM faculty", conn)
    conn.close()
    return df

def add_faculty_to_db(teacher_name, subject):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO faculty (teacher_name, subject) VALUES (?, ?)", (teacher_name.strip(), subject))
    conn.commit()
    conn.close()

def delete_faculty_from_db(fac_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM faculty WHERE id = ?", (fac_id,))
    conn.commit()
    conn.close()

def get_all_lessons():
    conn = get_connection()
    df = pd.read_sql("SELECT id, class_name, section, subject, teacher FROM lessons", conn)
    conn.close()
    return df

def add_lesson_to_db(cls, sec, subj, teacher):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO lessons (class_name, section, subject, teacher) VALUES (?, ?, ?, ?)", (cls, sec, subj, teacher))
    conn.commit()
    conn.close()

def delete_lesson_from_db(lesson_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
    conn.commit()
    conn.close()

def reset_database_to_default():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS subjects")
    cursor.execute("DROP TABLE IF EXISTS faculty")
    cursor.execute("DROP TABLE IF EXISTS lessons")
    conn.commit()
    conn.close()
    init_db()

# --- SIDEBAR CONTROLS ---
st.sidebar.title("⚙️ AI Parameters")
pop_size = st.sidebar.slider("Population Size", 50, 500, 200, 50)
generations = st.sidebar.slider("Generations", 20, 200, 80, 10)
mutation_prob = st.sidebar.slider("Mutation Probability", 0.01, 0.5, 0.15, 0.01)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset DB to Default"):
    reset_database_to_default()
    st.sidebar.success("Database reset successfully!")
    st.rerun()

# --- MAIN APP LAYOUT ---
st.title("🏫 AI-Powered School Timetable Optimizer")
st.markdown("Manage master subjects, register faculty independently, allocate class lessons, and optimize schedules using Genetic Algorithms (DEAP).")

tabs = st.tabs(["📚 Curriculum & Faculty", "📝 Class Lesson Allocations", "🧬 Run AI Optimizer", "📊 Timetable Matrix View"])

# --- TAB 1: CURRICULUM & FACULTY DIRECTORY ---
with tabs[0]:
    st.subheader("Master Curriculum & Faculty Registry")
    st.write("Register subjects and faculty members independently without tying them to specific classrooms yet.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 1. Master Subjects Directory")
        with st.form("add_subject_form"):
            new_subj_input = st.text_input("Subject Name", placeholder="e.g., Economics")
            if st.form_submit_button("Add Subject"):
                if new_subj_input.strip():
                    if add_subject_to_db(new_subj_input):
                        st.success(f"Subject '{new_subj_input.strip()}' added!")
                        st.rerun()
                    else:
                        st.warning("Subject already exists.")
                else:
                    st.error("Enter a valid subject name.")
                    
        st.markdown("#### Existing Subjects")
        st.write(", ".join(get_all_subjects()))

    with col2:
        st.markdown("### 2. Faculty Directory (Subject Specialization)")
        st.markdown("<small>Map a teacher directly to their qualified subject (No class/section needed here).</small>", unsafe_allow_html=True)
        
        existing_subjects = get_all_subjects()
        with st.form("add_faculty_form"):
            fac_name = st.text_input("Faculty / Teacher Name", placeholder="e.g., Mr. Alok Roy")
            fac_subject = st.selectbox("Qualified Subject", existing_subjects if existing_subjects else [""])
            
            if st.form_submit_button("Register Faculty Member"):
                if fac_name.strip() and fac_subject:
                    add_faculty_to_db(fac_name, fac_subject)
                    st.success(f"Registered **{fac_name.strip()}** for **{fac_subject}**!")
                    st.rerun()
                else:
                    st.error("Both teacher name and subject are required.")

    st.markdown("---")
    st.subheader("📋 Registered Faculty Roster")
    df_faculty = get_all_faculty()
    if not df_faculty.empty:
        st.dataframe(df_faculty, use_container_width=True)
        with st.form("delete_faculty_form"):
            del_f_id = st.selectbox("Select Faculty ID to Remove", df_faculty['id'].tolist())
            if st.form_submit_button("Remove Faculty"):
                delete_faculty_from_db(del_f_id)
                st.success(f"Removed faculty ID {del_f_id}.")
                st.rerun()
    else:
        st.info("No faculty members registered.")

# --- TAB 2: CLASS LESSON ALLOCATIONS ---
with tabs[1]:
    st.subheader("Assign Faculty & Lessons to Class Sections")
    st.write("Specify which classes and sections need which lessons taught by your registered faculty.")
    
    df_faculty = get_all_faculty()
    with st.form("add_lesson_form"):
        c1, c2 = st.columns(2)
        with c1:
            c_in = st.selectbox("Class", ["Class 6", "Class 7", "Class 8", "Class 9", "Class 10", "Class 11", "Class 12"])
        with c2:
            sec_in = st.selectbox("Section", ["A", "B", "C", "D"])
            
        if not df_faculty.empty:
            # Format faculty choices as "Teacher Name (Subject)"
            faculty_options = [f"{row['teacher_name']} ({row['subject']})" for _, row in df_faculty.iterrows()]
            selected_fac_comb = st.selectbox("Select Faculty & Subject", faculty_options)
            
            # Parse back teacher and subject
            selected_teacher = selected_fac_comb.split(" (")[0]
            selected_subject = selected_fac_comb.split(" (")[1].rstrip(")")
        else:
            selected_teacher = ""
            selected_subject = ""
            st.warning("Please register faculty in Tab 1 first.")
            
        if st.form_submit_button("Add Lesson Requirement"):
            if selected_teacher and selected_subject:
                add_lesson_to_db(c_in, sec_in, selected_subject, selected_teacher)
                st.success(f"Added {selected_subject} ({selected_teacher}) for {c_in} Sec {sec_in}!")
                st.rerun()
            else:
                st.error("Please provide valid lesson details.")

    st.markdown("---")
    st.subheader("📋 Current Class Lesson Requirements")
    df_lessons = get_all_lessons()
    if not df_lessons.empty:
        st.dataframe(df_lessons, use_container_width=True)
        with st.form("delete_lesson_form"):
            del_l_id = st.selectbox("Select Lesson Record ID to Delete", df_lessons['id'].tolist())
            if st.form_submit_button("Delete Lesson Record"):
                delete_lesson_from_db(del_l_id)
                st.success(f"Deleted lesson ID {del_l_id}.")
                st.rerun()
    else:
        st.info("No class lessons recorded.")

# --- TAB 3: RUN AI OPTIMIZER ---
with tabs[2]:
    st.subheader("🧬 Genetic Algorithm Optimization")
    st.write("Click below to run the DEAP optimization engine and schedule conflict-free master timetables.")
    
    if st.button("🚀 Run AI Optimizer", type="primary"):
        df_lessons = get_all_lessons()
        if df_lessons.empty:
            st.error("Database is empty. Please add lesson requirements in the previous tab first.")
        else:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            periods_per_day = 6
            total_slots = len(days) * periods_per_day
            
            lessons_list = df_lessons.to_dict('records')
            num_lessons = len(lessons_list)
            
            # DEAP Setup
            if "FitnessMin" in creator.__dict__:
                del creator.FitnessMin
            if "Individual" in creator.__dict__:
                del creator.Individual
                
            creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
            creator.create("Individual", list, fitness=creator.FitnessMin)
            
            toolbox = base.Toolbox()
            toolbox.register("attr_int", random.randint, 0, total_slots - 1)
            toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_int, n=num_lessons)
            toolbox.register("population", tools.initRepeat, list, toolbox.individual)
            
            def eval_timetable(individual):
                conflicts = 0
                class_sec_slots = {}
                teacher_slots = {}
                
                for idx, slot in enumerate(individual):
                    lesson = lessons_list[idx]
                    cls_sec = f"{lesson['class_name']}-{lesson['section']}"
                    teacher = lesson['teacher']
                    
                    # Track class section collision
                    key_class = (cls_sec, slot)
                    if key_class in class_sec_slots:
                        conflicts += 1
                    else:
                        class_sec_slots[key_class] = True
                        
                    # Track teacher collision
                    key_teacher = (teacher, slot)
                    if key_teacher in teacher_slots:
                        conflicts += 1
                    else:
                        teacher_slots[key_teacher] = True
                        
                return (conflicts,),
            
            toolbox.register("evaluate", eval_timetable)
            toolbox.register("mate", tools.cxTwoPoint)
            toolbox.register("mutate", tools.mutUniformInt, low=0, up=total_slots - 1, indpb=0.2)
            toolbox.register("select", tools.selTournament, tournsize=3)
            
            pop = toolbox.population(n=pop_size)
            hof = tools.HallOfFame(1)
            stats = tools.Statistics(lambda ind: ind.fitness.values)
            stats.register("min", min)
            
            with st.spinner("Running Genetic Algorithm optimization..."):
                pop, logbook = tools.eaSimple(pop, toolbox, cxpb=0.7, mutpb=mutation_prob, ngen=generations, stats=stats, halloffame=hof, verbose=False)
                
            best_ind = hof[0]
            best_conflicts = best_ind.fitness.values[0]
            
            st.session_state['best_ind'] = best_ind
            st.session_state['lessons_list'] = lessons_list
            
            if best_conflicts == 0:
                st.success("🎉 Perfect conflict-free master timetable generated!")
            else:
                st.warning(f"⚠️ Optimization completed with {int(best_conflicts)} remaining conflicts. Try running for more generations.")
                
            # Plot Convergence Chart
            gen_list = logbook.select("gen")
            min_fitness = logbook.select("min")
            
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(gen_list, min_fitness, color='red', linewidth=2, marker='o', markersize=3)
            ax.set_title("Algorithm Convergence (Total Conflicts vs. Generation)")
            ax.set_xlabel("Generation")
            ax.set_ylabel("Total Conflicts")
            ax.grid(True, linestyle='--', alpha=0.6)
            st.pyplot(fig)

# --- TAB 4: TIMETABLE MATRIX VIEW ---
with tabs[3]:
    st.subheader("📅 View Timetable Matrix By Class & Section")
    
    if 'best_ind' in st.session_state and 'lessons_list' in st.session_state:
        best_ind = st.session_state['best_ind']
        lessons_list = st.session_state['lessons_list']
        
        df_lessons = get_all_lessons()
        unique_classes_sections = df_lessons[['class_name', 'section']].drop_duplicates().values.tolist()
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        periods = ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5", "Period 6"]
        
        tabs_cs = st.tabs([f"{cls} - Sec {sec}" for cls, sec in unique_classes_sections])
        
        for idx, (cls, sec) in enumerate(unique_classes_sections):
            with tabs_cs[idx]:
                st.markdown(f"### Timetable for {cls} - Section {sec}")
                
                matrix_data = {p: ["-" for _ in days] for p in periods}
                
                for l_idx, slot in enumerate(best_ind):
                    lesson = lessons_list[l_idx]
                    if lesson['class_name'] == cls and lesson['section'] == sec:
                        day_idx = slot // len(periods)
                        period_idx = slot % len(periods)
                        
                        if day_idx < len(days) and period_idx < len(periods):
                            d_name = days[day_idx]
                            p_name = periods[period_idx]
                            cell_text = f"{lesson['subject']} ({lesson['teacher']})"
                            
                            current_val = matrix_data[p_name][days.index(d_name)]
                            if current_val == "-":
                                matrix_data[p_name][days.index(d_name)] = cell_text
                            else:
                                matrix_data[p_name][days.index(d_name)] = f"{current_val} / \n{cell_text}"
                                
                df_matrix = pd.DataFrame(matrix_data, index=days).T
                st.dataframe(df_matrix, use_container_width=True)
    else:
        st.info("Please run the AI Optimizer in the previous tab first to generate the schedule matrix.")