import streamlit as st
import pandas as pd
import os
import base64
import requests

# ---------------------------- SESSION INIT ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------------------- CONFIG ----------------------------
GITHUB_TOKEN = st.secrets["github_token"]
GITHUB_REPO = "yourusername/yourrepo"
GITHUB_BRANCH = "main"
SCHOOLS = ["School A", "School B", "School C", "School D"]
CSV_FOLDER = "schools"

# ---------------------------- INIT ----------------------------
os.makedirs(CSV_FOLDER, exist_ok=True)

# ---------------------------- UTILS ----------------------------
def load_csv(school):
    path = f"{CSV_FOLDER}/{school.replace(' ', '_').lower()}.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    else:
        return pd.DataFrame(columns=["student_id", "name", "school_name", "fee", "remaining_fee", "parent_name", "parent_contact"])

def save_csv(school, df):
    df.to_csv(f"{CSV_FOLDER}/{school.replace(' ', '_').lower()}.csv", index=False)

def push_to_github(file_path, github_path):
    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{github_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.get(url, headers=headers)
    sha = resp.json().get("sha") if resp.status_code == 200 else None

    payload = {
        "message": f"Update {github_path}",
        "content": content,
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, json=payload, headers=headers)
    return r.status_code in [200, 201]

# ---------------------------- LOGIN ----------------------------
if not st.session_state.logged_in:
    st.title("School Management Login")
    username = st.text_input("Username")  # Parent name or admin username
    password = st.text_input("Password", type="password")  # Mobile number or admin password

    if st.button("Login"):
        # Admin logins
        admin_users = {"gholape": "gholape", "naveen": "naveen"}
        if username in admin_users and password == admin_users[username]:
            st.session_state.logged_in = True
            st.session_state.role = "admin"
            st.session_state.user = username
        else:
            # Parent login by name & contact match
            for school in SCHOOLS:
                df = load_csv(school)
                match = df[(df["parent_name"].str.lower() == username.lower()) &
                (df["parent_contact"].astype(str) == password)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.role = "parent"
                    st.session_state.user = {
                        "name": username,
                        "contact": password,
                        "school": school   # <-- add this
                    }
                    break
            if not st.session_state.logged_in:
                st.error("Invalid credentials")
    st.stop()

# ---------------------------- DASHBOARD ----------------------------
st.title("📚 School Management App")
st.subheader(f"Welcome, {st.session_state.role.title()}!")

# Notifications
if st.session_state.role == "admin":
    st.sidebar.header("📣 School Notification")
    selected_school = st.sidebar.selectbox("Select School", SCHOOLS)
    msg = st.sidebar.text_area("Notification Message")
    if st.sidebar.button("Send Notification"):
        notif_file = f"notifications/{selected_school.replace(' ', '_').lower()}_notices.csv"
        os.makedirs("notifications", exist_ok=True)
        
        if os.path.exists(notif_file) and os.path.getsize(notif_file) > 0:
            df_notif = pd.read_csv(notif_file)
            if not df_notif.empty:
                st.sidebar.write(df_notif.tail(5))
            else:
                st.sidebar.info("No notifications yet.")
        else:
            st.sidebar.info("No notifications yet.")
     
        df_notif.loc[len(df_notif)] = [msg]
        df_notif.to_csv(notif_file, index=False)
        st.sidebar.success("Notification sent!")

# View Notifications - Only for Admin
if st.session_state.role == "admin":
    st.sidebar.header("🔔 View Notifications")
    notif_tab = st.sidebar.selectbox("Choose School to View", SCHOOLS)
    notif_file = f"notifications/{notif_tab.replace(' ', '_').lower()}_notices.csv"
    os.makedirs("notifications", exist_ok=True)

    # ✅ Create an empty CSV with header if it doesn't exist or is empty
    if not os.path.exists(notif_file) or os.path.getsize(notif_file) == 0:
        pd.DataFrame(columns=["message"]).to_csv(notif_file, index=False)

    try:
        df_notif = pd.read_csv(notif_file)
        if not df_notif.empty:
            st.sidebar.write(df_notif.tail(5))
        else:
            st.sidebar.info("No notifications yet.")
    except Exception as e:
        st.sidebar.error(f"Error reading notifications: {e}")

# ---------------------------- SCHOOL SECTIONS ----------------------------
if st.session_state.role == "admin":
    tabs = st.tabs(SCHOOLS)
    for i, school in enumerate(SCHOOLS):
        with tabs[i]:
            df = load_csv(school)

            st.markdown("### Add Student")
            with st.form(f"form_{i}"):
                sid = st.text_input("Student ID", key=f"sid_{i}")
                name = st.text_input("Student Name", key=f"name_{i}")
                fee = st.number_input("Total Fee", 0, key=f"fee_{i}")
                remaining_fee = st.number_input("Remaining Fee", 0, key=f"rem_fee_{i}")
                parent_name = st.text_input("Parent Name", key=f"pname_{i}")
                parent_contact = st.text_input("Parent Contact", key=f"pcontact_{i}")
                if st.form_submit_button("Add Student"):
                    df.loc[len(df)] = [sid, name, school, fee, remaining_fee, parent_name, parent_contact]
                    save_csv(school, df)
                    push_to_github(f"{CSV_FOLDER}/{school.replace(' ', '_').lower()}.csv",
                                   f"{CSV_FOLDER}/{school.replace(' ', '_').lower()}.csv")
                    st.success("Student added successfully!")

            st.markdown("### All Students")
            st.dataframe(df)

elif st.session_state.role == "parent":
    school = st.session_state.user["school"]
    st.header(f"🎓 {school}")
    df = load_csv(school)
    parent_df = df[
        (df["parent_name"].str.lower() == st.session_state.user["name"].lower()) &
        (df["parent_contact"].astype(str) == st.session_state.user["contact"])
    ]
    if not parent_df.empty:
        st.write("### Your Child's Info")
        st.dataframe(parent_df)
        
        notif_file = f"notifications/{school.replace(' ', '_').lower()}_notices.csv"
        os.makedirs("notifications", exist_ok=True)
        if not os.path.exists(notif_file) or os.path.getsize(notif_file) == 0:
            pd.DataFrame(columns=["message"]).to_csv(notif_file, index=False)
        
        try:
            df_notif = pd.read_csv(notif_file)
            if not df_notif.empty:
                st.write("### 📢 School Notifications")
                st.dataframe(df_notif.tail(5))
            else:
                st.info("No notifications available from school.")
        except Exception as e:
            st.error(f"Error reading notifications: {e}")
            
    else:
        st.warning("No record found.")
