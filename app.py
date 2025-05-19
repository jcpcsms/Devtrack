# app.py - Main Streamlit Application
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import sqlite3
import os
from pathlib import Path

# Set page configuration
st.set_page_config(
    page_title="DevTrack - Software Project Management",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
def init_db():
    db_path = Path("project_management.db")
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    # Create tables if they don't exist
    c.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT NOT NULL,
        progress REAL DEFAULT 0
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS team_members (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        email TEXT
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        project_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL,
        priority TEXT NOT NULL,
        start_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        assigned_to INTEGER,
        progress REAL DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects (id),
        FOREIGN KEY (assigned_to) REFERENCES team_members (id)
    )
    ''')
    
    conn.commit()
    return conn

# Initialize session state
def init_session_state():
    if 'page' not in st.session_state:
        st.session_state['page'] = 'Dashboard'
    if 'edit_project' not in st.session_state:
        st.session_state['edit_project'] = None
    if 'edit_task' not in st.session_state:
        st.session_state['edit_task'] = None
    if 'edit_team_member' not in st.session_state:
        st.session_state['edit_team_member'] = None

# Navigation
def sidebar_navigation():
    with st.sidebar:
        st.title("DevTrack 💻")
        st.markdown("### Software Project Management")
        
        nav_options = ["Dashboard", "Projects", "Tasks", "Team", "Reports"]
        icons = ["📊", "🚀", "✅", "👥", "📈"]
        
        for i, option in enumerate(nav_options):
            if st.button(f"{icons[i]} {option}"):
                st.session_state['page'] = option
        # Reset edit states when changing pages
                if option != "Projects":
                    st.session_state['edit_project'] = None
                if option != "Tasks":
                    st.session_state['edit_task'] = None
                if option != "Team":
                    st.session_state['edit_team_member'] = None
        
        st.divider()
        st.markdown("### Quick Actions")
        if st.button("➕ New Project"):
            st.session_state['page'] = "Projects"
            st.session_state['edit_project'] = "new"
        if st.button("➕ New Task"):
            st.session_state['page'] = "Tasks"
            st.session_state['edit_task'] = "new"

# Dashboard page
def dashboard_page(conn):
    st.title("Dashboard 📊")
    
    # Get data for dashboard
    projects_df = pd.read_sql("SELECT * FROM projects", conn)
    tasks_df = pd.read_sql("SELECT * FROM tasks", conn)
    team_df = pd.read_sql("SELECT * FROM team_members", conn)
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Projects", len(projects_df))
    with col2:
        st.metric("Open Tasks", len(tasks_df[tasks_df['status'] != 'Completed']))
    with col3:
        st.metric("Team Members", len(team_df))
    with col4:
        if not projects_df.empty:
            avg_progress = projects_df['progress'].mean()
            st.metric("Avg. Project Progress", f"{avg_progress:.0f}%")
        else:
            st.metric("Avg. Project Progress", "0%")
    
    # Project status and progress
    if not projects_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Project Status")
            status_counts = projects_df['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig = px.pie(status_counts, values='Count', names='Status', hole=.3)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Project Progress")
            fig = px.bar(projects_df, x='name', y='progress', 
                         labels={'name': 'Project', 'progress': 'Progress (%)'},
                         color='progress',
                         color_continuous_scale='Viridis')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No projects found. Add a project to see statistics here.")
    
    # Recent and upcoming tasks
    if not tasks_df.empty:
        st.subheader("Tasks Due Soon")
        
        # Convert date strings to datetime objects for comparison
        tasks_df['due_date'] = pd.to_datetime(tasks_df['due_date'])
        
        # Filter tasks that are not completed and due within the next 7 days
        today = datetime.datetime.now()
        upcoming_tasks = tasks_df[(tasks_df['status'] != 'Completed') & 
                                (tasks_df['due_date'] <= today + datetime.timedelta(days=7))]
        
        if not upcoming_tasks.empty:
            upcoming_tasks = upcoming_tasks.sort_values('due_date')
            
            # Join with project data to show project name
            projects_minimal = pd.read_sql("SELECT id, name FROM projects", conn)
            upcoming_tasks = upcoming_tasks.merge(projects_minimal, left_on='project_id', right_on='id', suffixes=('', '_project'))
            
            # Format for display
            display_tasks = upcoming_tasks[['name', 'name_project', 'status', 'priority', 'due_date']]
            display_tasks.columns = ['Task', 'Project', 'Status', 'Priority', 'Due Date']
            
            # Color code by priority
            def color_priority(val):
                if val == 'High':
                    return 'background-color: #FFCCCC'
                elif val == 'Medium':
                    return 'background-color: #FFFFCC'
                return ''
            
            st.dataframe(display_tasks.style.applymap(color_priority, subset=['Priority']), use_container_width=True)
        else:
            st.info("No upcoming deadlines in the next 7 days.")
    else:
        st.info("No tasks found. Add tasks to see upcoming deadlines.")

# Projects page
def projects_page(conn):
    st.title("Projects 🚀")
    
    if st.session_state['edit_project'] is None:
        # Display existing projects
        projects_df = pd.read_sql("SELECT * FROM projects", conn)
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("➕ Add New Project", type="primary"):
                st.session_state['edit_project'] = "new"
                st.rerun()
        
        if not projects_df.empty:
            for index, project in projects_df.iterrows():
                with st.expander(f"{project['name']} - {project['status']} ({project['progress']}%)"):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**Description:** {project['description']}")
                        st.write(f"**Timeline:** {project['start_date']} to {project['end_date']}")
                        
                        # Get tasks for this project
                        tasks_df = pd.read_sql(f"SELECT * FROM tasks WHERE project_id = {project['id']}", conn)
                        if not tasks_df.empty:
                            completed_tasks = len(tasks_df[tasks_df['status'] == 'Completed'])
                            st.write(f"**Tasks:** {completed_tasks}/{len(tasks_df)} completed")
                        else:
                            st.write("**Tasks:** No tasks assigned")
                    
                    with col2:
                        st.progress(project['progress'] / 100)
                    
                    with col3:
                        if st.button("Edit", key=f"edit_{project['id']}"):
                            st.session_state['edit_project'] = project['id']
                            st.rerun()
        else:
            st.info("No projects found. Create a new project to get started.")
    else:
        # Add/Edit project form
        if st.session_state['edit_project'] == "new":
            st.subheader("Add New Project")
            project_data = {
                'id': None,
                'name': '',
                'description': '',
                'start_date': datetime.date.today().isoformat(),
                'end_date': (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
                'status': 'Planning',
                'progress': 0
            }
        else:
            st.subheader("Edit Project")
            c = conn.cursor()
            c.execute("SELECT * FROM projects WHERE id = ?", (st.session_state['edit_project'],))
            project_data = dict(zip([column[0] for column in c.description], c.fetchone()))
        
        with st.form("project_form"):
            name = st.text_input("Project Name", value=project_data['name'])
            description = st.text_area("Description", value=project_data['description'])
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.date.fromisoformat(project_data['start_date']))
            with col2:
                end_date = st.date_input("End Date", value=datetime.date.fromisoformat(project_data['end_date']))
            
            col1, col2 = st.columns(2)
            with col1:
                status = st.selectbox("Status", 
                                     ["Planning", "In Progress", "On Hold", "Completed", "Cancelled"],
                                     index=["Planning", "In Progress", "On Hold", "Completed", "Cancelled"].index(project_data['status']))
            with col2:
                progress = st.slider("Progress (%)", 0, 100, int(project_data['progress']))
            
            col1, col2 = st.columns([1, 3])
            with col1:
                submit = st.form_submit_button("Save Project")
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state['edit_project'] = None
                    st.rerun()
            
            if submit:
                if name:
                    c = conn.cursor()
                    if project_data['id'] is None:
                        c.execute('''
                        INSERT INTO projects (name, description, start_date, end_date, status, progress)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', (name, description, start_date.isoformat(), end_date.isoformat(), status, progress))
                    else:
                        c.execute('''
                        UPDATE projects
                        SET name = ?, description = ?, start_date = ?, end_date = ?, status = ?, progress = ?
                        WHERE id = ?
                        ''', (name, description, start_date.isoformat(), end_date.isoformat(), status, progress, project_data['id']))
                    
                    conn.commit()
                    st.session_state['edit_project'] = None
                    st.success("Project saved successfully!")
                    st.rerun()
                else:
                    st.error("Project name is required.")

# Tasks page
def tasks_page(conn):
    st.title("Tasks ✅")
    
    if st.session_state['edit_task'] is None:
        # Display tasks with filtering options
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            # Get all projects for filter
            projects_df = pd.read_sql("SELECT id, name FROM projects", conn)
            project_options = ["All Projects"] + projects_df['name'].tolist()
            selected_project = st.selectbox("Filter by Project", project_options)
        
        with col2:
            status_options = ["All Statuses", "Not Started", "In Progress", "Blocked", "Completed"]
            selected_status = st.selectbox("Filter by Status", status_options)
        
        with col3:
            if st.button("➕ Add New Task", type="primary"):
                st.session_state['edit_task'] = "new"
                st.rerun()
        
        # Build query based on filters
        query = "SELECT t.*, p.name as project_name, tm.name as assignee_name FROM tasks t LEFT JOIN projects p ON t.project_id = p.id LEFT JOIN team_members tm ON t.assigned_to = tm.id"
        where_clauses = []
        params = []
        
        if selected_project != "All Projects":
            where_clauses.append("p.name = ?")
            params.append(selected_project)
        
        if selected_status != "All Statuses":
            where_clauses.append("t.status = ?")
            params.append(selected_status)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Get filtered tasks
        tasks_df = pd.read_sql(query, conn, params=params)
        
        if not tasks_df.empty:
            # Display tasks in a nice format
            for index, task in tasks_df.iterrows():
                with st.expander(f"{task['name']} - {task['status']} ({task['progress']}%)"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Project:** {task['project_name']}")
                        st.write(f"**Description:** {task['description']}")
                        st.write(f"**Priority:** {task['priority']}")
                        st.write(f"**Timeline:** {task['start_date']} to {task['due_date']}")
                        if task['assignee_name']:
                            st.write(f"**Assigned to:** {task['assignee_name']}")
                        else:
                            st.write("**Assigned to:** Unassigned")
                    
                    with col2:
                        st.progress(task['progress'] / 100)
                        if st.button("Edit", key=f"edit_task_{task['id']}"):
                            st.session_state['edit_task'] = task['id']
                            st.rerun()
        else:
            st.info("No tasks found with the selected filters.")
    
    else:
        # Add/Edit task form
        if st.session_state['edit_task'] == "new":
            st.subheader("Add New Task")
            task_data = {
                'id': None,
                'project_id': None,
                'name': '',
                'description': '',
                'status': 'Not Started',
                'priority': 'Medium',
                'start_date': datetime.date.today().isoformat(),
                'due_date': (datetime.date.today() + datetime.timedelta(days=7)).isoformat(),
                'assigned_to': None,
                'progress': 0
            }
        else:
            st.subheader("Edit Task")
            c = conn.cursor()
            c.execute("SELECT * FROM tasks WHERE id = ?", (st.session_state['edit_task'],))
            task_data = dict(zip([column[0] for column in c.description], c.fetchone()))
        
        with st.form("task_form"):
            # Get project options
            projects_df = pd.read_sql("SELECT id, name FROM projects", conn)
            project_options = projects_df['name'].tolist()
            project_ids = projects_df['id'].tolist()
            
            # Get team member options
            team_df = pd.read_sql("SELECT id, name FROM team_members", conn)
            team_options = ["Unassigned"] + team_df['name'].tolist()
            team_ids = [None] + team_df['id'].tolist()
            
            name = st.text_input("Task Name", value=task_data['name'])
            
            # Project selection
            if projects_df.empty:
                st.error("You need to create a project before adding tasks.")
                project_idx = 0
            else:
                if task_data['project_id'] is not None:
                    default_idx = project_ids.index(task_data['project_id']) if task_data['project_id'] in project_ids else 0
                else:
                    default_idx = 0
                project_idx = st.selectbox("Project", project_options, index=default_idx)
            
            description = st.text_area("Description", value=task_data['description'])
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.date.fromisoformat(task_data['start_date']))
            with col2:
                due_date = st.date_input("Due Date", value=datetime.date.fromisoformat(task_data['due_date']))
            
            col1, col2 = st.columns(2)
            with col1:
                status = st.selectbox("Status", 
                                     ["Not Started", "In Progress", "Blocked", "Completed"],
                                     index=["Not Started", "In Progress", "Blocked", "Completed"].index(task_data['status']))
            with col2:
                priority = st.selectbox("Priority",
                                       ["Low", "Medium", "High"],
                                       index=["Low", "Medium", "High"].index(task_data['priority']))
            
            # Team member assignment
            if team_df.empty:
                st.warning("No team members available. You can add team members in the Team section.")
                assigned_idx = 0
            else:
                if task_data['assigned_to'] is not None:
                    try:
                        default_idx = team_ids.index(task_data['assigned_to'])
                    except ValueError:
                        default_idx = 0
                else:
                    default_idx = 0
                assigned_idx = st.selectbox("Assigned To", team_options, index=default_idx)
            
            progress = st.slider("Progress (%)", 0, 100, int(task_data['progress']))
            
            col1, col2 = st.columns([1, 3])
            with col1:
                submit = st.form_submit_button("Save Task")
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state['edit_task'] = None
                    st.rerun()
            
            if submit:
                if name and not projects_df.empty:
                    c = conn.cursor()
                    
                    # Get IDs for the selected options
                    project_id = project_ids[project_options.index(project_idx)]
                    assigned_to = None if assigned_idx == "Unassigned" or team_df.empty else team_ids[team_options.index(assigned_idx)]
                    
                    if task_data['id'] is None:
                        c.execute('''
                        INSERT INTO tasks (project_id, name, description, status, priority, start_date, due_date, assigned_to, progress)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (project_id, name, description, status, priority, start_date.isoformat(), due_date.isoformat(), assigned_to, progress))
                    else:
                        c.execute('''
                        UPDATE tasks
                        SET project_id = ?, name = ?, description = ?, status = ?, priority = ?, start_date = ?, due_date = ?, assigned_to = ?, progress = ?
                        WHERE id = ?
                        ''', (project_id, name, description, status, priority, start_date.isoformat(), due_date.isoformat(), assigned_to, progress, task_data['id']))
                    
                    conn.commit()
                    st.session_state['edit_task'] = None
                    st.success("Task saved successfully!")
                    st.rerun()
                else:
                    if projects_df.empty:
                        st.error("You need to create a project before adding tasks.")
                    else:
                        st.error("Task name is required.")

# Team page
def team_page(conn):
    st.title("Team 👥")
    
    if st.session_state['edit_team_member'] is None:
        # Display team members
        team_df = pd.read_sql("SELECT * FROM team_members", conn)
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("➕ Add Team Member", type="primary"):
                st.session_state['edit_team_member'] = "new"
                st.rerun()
        
        if not team_df.empty:
            # Display in a grid layout
            cols = st.columns(3)
            for index, member in team_df.iterrows():
                with cols[index % 3]:
                    with st.container(border=True):
                        st.subheader(member['name'])
                        st.write(f"**Role:** {member['role']}")
                        if member['email']:
                            st.write(f"**Email:** {member['email']}")
                        
                        # Get tasks assigned to this team member
                        tasks_count = pd.read_sql(f"SELECT COUNT(*) as count FROM tasks WHERE assigned_to = {member['id']}", conn).iloc[0]['count']
                        st.write(f"**Assigned Tasks:** {tasks_count}")
                        
                        if st.button("Edit", key=f"edit_member_{member['id']}"):
                            st.session_state['edit_team_member'] = member['id']
                            st.rerun()
        else:
            st.info("No team members found. Add team members to assign tasks.")
    else:
        # Add/Edit team member form
        if st.session_state['edit_team_member'] == "new":
            st.subheader("Add New Team Member")
            member_data = {
                'id': None,
                'name': '',
                'role': '',
                'email': ''
            }
        else:
            st.subheader("Edit Team Member")
            c = conn.cursor()
            c.execute("SELECT * FROM team_members WHERE id = ?", (st.session_state['edit_team_member'],))
            member_data = dict(zip([column[0] for column in c.description], c.fetchone()))
        
        with st.form("team_member_form"):
            name = st.text_input("Name", value=member_data['name'])
            role = st.text_input("Role", value=member_data['role'])
            email = st.text_input("Email", value=member_data['email'])
            
            col1, col2 = st.columns([1, 3])
            with col1:
                submit = st.form_submit_button("Save")
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state['edit_team_member'] = None
                    st.rerun()
            
            if submit:
                if name and role:
                    c = conn.cursor()
                    if member_data['id'] is None:
                        c.execute('''
                        INSERT INTO team_members (name, role, email)
                        VALUES (?, ?, ?)
                        ''', (name, role, email))
                    else:
                        c.execute('''
                        UPDATE team_members
                        SET name = ?, role = ?, email = ?
                        WHERE id = ?
                        ''', (name, role, email, member_data['id']))
                    
                    conn.commit()
                    st.session_state['edit_team_member'] = None
                    st.success("Team member saved successfully!")
                    st.rerun()
                else:
                    st.error("Name and role are required.")

# Reports page
def reports_page(conn):
    st.title("Reports 📈")
    
    # Tab for different reports
    tab1, tab2, tab3 = st.tabs(["Project Progress", "Team Workload", "Timeline"])
    
    with tab1:
        st.subheader("Project Progress Overview")
        
        # Get projects data
        projects_df = pd.read_sql("SELECT * FROM projects", conn)
        
        if not projects_df.empty:
            # Progress by project
            fig = px.bar(projects_df, x='name', y='progress',
                        labels={'name': 'Project', 'progress': 'Progress (%)'},
                        color='status',
                        title="Project Progress")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Project status breakdown
            status_counts = projects_df['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig = px.pie(status_counts, values='Count', names='Status', 
                        title="Project Status Distribution")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No projects data available for reporting.")
    
    with tab2:
        st.subheader("Team Workload Analysis")
        
        # Get team and task data
        team_df = pd.read_sql("SELECT id, name, role FROM team_members", conn)
        tasks_df = pd.read_sql("""
            SELECT t.*, tm.name as assignee_name, p.name as project_name 
            FROM tasks t 
            LEFT JOIN team_members tm ON t.assigned_to = tm.id
            LEFT JOIN projects p ON t.project_id = p.id
        """, conn)
        
        if not team_df.empty and not tasks_df.empty:
            # Task count by team member
            task_counts = tasks_df.groupby('assignee_name').size().reset_index()
            task_counts.columns = ['Team Member', 'Tasks Assigned']
            # Remove None/Unassigned
            task_counts = task_counts.dropna()
            
            if not task_counts.empty:
                fig = px.bar(task_counts, x='Team Member', y='Tasks Assigned',
                            title="Tasks Assigned per Team Member")
                st.plotly_chart(fig, use_container_width=True)
                
                # Task status breakdown by team member
                if not tasks_df[tasks_df['assignee_name'].notna()].empty:
                    fig = px.histogram(tasks_df[tasks_df['assignee_name'].notna()], 
                                      x='assignee_name', color='status',
                                      title="Task Status by Team Member",
                                      labels={'assignee_name': 'Team Member', 'count': 'Number of Tasks'})
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No tasks have been assigned to team members yet.")
        else:
            st.info("Insufficient data for team workload analysis.")
    
    with tab3:
        st.subheader("Project Timeline")
        
        # Get projects for selection
        projects_df = pd.read_sql("SELECT id, name FROM projects", conn)
        
        if not projects_df.empty:
            selected_project = st.selectbox("Select Project", projects_df['name'].tolist())
            project_id = projects_df[projects_df['name'] == selected_project]['id'].iloc[0]
            
            # Get project details
            project_details = pd.read_sql(f"SELECT * FROM projects WHERE id = {project_id}", conn).iloc[0]
            
            # Get tasks for this project
            tasks_df = pd.read_sql(f"""
                SELECT t.*, tm.name as assignee_name 
                FROM tasks t 
                LEFT JOIN team_members tm ON t.assigned_to = tm.id
                WHERE t.project_id = {project_id}
            """, conn)
            
            # Display project timeline
            st.write(f"**Project Duration:** {project_details['start_date']} to {project_details['end_date']}")
            st.write(f"**Status:** {project_details['status']}")
            st.write(f"**Overall Progress:** {project_details['progress']}%")
            
            if not tasks_df.empty:
                # Convert dates for plotting
                tasks_df['start_date'] = pd.to_datetime(tasks_df['start_date'])
                tasks_df['due_date'] = pd.to_datetime(tasks_df['due_date'])
                
                # Prepare data for Gantt chart
                gantt_data = []
                for _, task in tasks_df.iterrows():
                    assignee = task['assignee_name'] if task['assignee_name'] else 'Unassigned'
                    gantt_data.append({
                        'Task': task['name'],
                        'Start': task['start_date'],
                        'Finish': task['due_date'],
                        'Status': task['status'],
                        'Assignee': assignee
                    })
                
                gantt_df = pd.DataFrame(gantt_data)
                
                # Create Gantt chart
                fig = px.timeline(gantt_df, x_start='Start', x_end='Finish', y='Task', color='Status',
                                hover_data=['Assignee'])
                fig.update_layout(title="Project Task Timeline")
                st.plotly_chart(fig, use_container_width=True)
                
                # Calculate critical path (simplified - just showing the longest tasks)
                task_durations = (tasks_df['due_date'] - tasks_df['start_date']).dt.days
                critical_task_idx = task_durations.idxmax()
                critical_task = tasks_df.iloc[critical_task_idx]
                
                st.subheader("Critical Path Analysis")
                st.write(f"Longest task duration: **{task_durations.max()} days** - *{critical_task['name']}*")
                
                # Task completion prediction
                completed_tasks_count = len(tasks_df[tasks_df['status'] == 'Completed'])
                total_tasks = len(tasks_df)
                completion_percentage = (completed_tasks_count / total_tasks) * 100 if total_tasks > 0 else 0
                
                st.write(f"Task completion: **{completed_tasks_count}/{total_tasks}** tasks completed ({completion_percentage:.1f}%)")
                
                # Calculate expected completion date based on progress
                if completion_percentage > 0:
                    project_start = pd.to_datetime(project_details['start_date'])
                    project_end = pd.to_datetime(project_details['end_date'])
                    project_duration = (project_end - project_start).days
                    
                    days_passed = (datetime.datetime.now() - project_start).days
                    estimated_total_days = days_passed / (completion_percentage / 100)
                    estimated_completion = project_start + datetime.timedelta(days=estimated_total_days)
                    
                    if estimated_completion > project_end:
                        st.warning(f"Based on current progress, this project may finish **{(estimated_completion - project_end).days} days late**.")
                    else:
                        st.success(f"Based on current progress, this project is on track to finish on time.")
            else:
                st.info("No tasks found for this project. Add tasks to see timeline analysis.")
        else:
            st.info("No projects found. Create a project to view timeline reports.")

# Main app logic
def main():
    # Initialize database connection
    conn = init_db()
    
    # Initialize session state
    init_session_state()
    
    # Navigation sidebar
    sidebar_navigation()
    
    # Display the selected page
    if st.session_state['page'] == 'Dashboard':
        dashboard_page(conn)
    elif st.session_state['page'] == 'Projects':
        projects_page(conn)
    elif st.session_state['page'] == 'Tasks':
        tasks_page(conn)
    elif st.session_state['page'] == 'Team':
        team_page(conn)
    elif st.session_state['page'] == 'Reports':
        reports_page(conn)
    
    # Close the database connection when done
    conn.close()

if __name__ == "__main__":
    main()