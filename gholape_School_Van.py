import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

# ---------------------------- SESSION INIT ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------------------- CONFIG ----------------------------
GITHUB_TOKEN = st.secrets["github_token"]
GITHUB_REPO = "yourusername/yourrepo"  # Replace with your GitHub repo
GITHUB_BRANCH = "main"
SCHOOLS = ["School A", "School B", "School C", "School D"]
CSV_FOLDER = "schools"
NOTIF_FOLDER = "notifications"

os.makedirs(CSV_FOLDER, exist_ok=True)
os.makedirs(NOTIF_FOLDER, exist_ok=True)

# ---------------------------- UTILS ----------------------------
def load_csv(school):
    path = f"{CSV_FOLDER}/{school.replace(' ', '_').lower()}.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    else:
        return pd.DataFrame(columns=["student_id", "name", "school_name", "fee", "remaining_fee", "parent_name", "parent_contact"])

def save_csv(school, df):
    path = f"{CSV_FOLDER}/{school.replace(' ', '_').lower()}.csv"
    df.to_csv(path, index=False)
    push_to_github(path, path)

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
    st.title("𝓖𝓱𝓸𝓵𝓪𝓹𝓮 𝓢𝓬𝓱𝓸𝓸𝓵 𝓥𝓪𝓷 𝓢𝓮𝓻𝓿𝓲𝓬𝓮𝓼")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login", key="login_button"):
        admin_users = st.secrets["admin_users"]
        if username in admin_users and password == admin_users[username]:
            st.session_state.logged_in = True
            st.session_state.role = "admin"
            st.session_state.user = username
        else:
            for school in SCHOOLS:
                df = load_csv(school)
                match = df[
                    (df["parent_name"].fillna("").str.lower() == username.lower()) &
                    (df["parent_contact"].fillna("").astype(str) == password)
                ]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.role = "parent"
                    st.session_state.user = {
                        "name": username,
                        "contact": password,
                        "school": school
                    }
                    break
            if not st.session_state.logged_in:
                st.error("Invalid credentials")
    st.stop()

# ---------------------------- DASHBOARD ----------------------------
st.title("📚 𝓖𝓱𝓸𝓵𝓪𝓹𝓮 𝓢𝓬𝓱𝓸𝓸𝓵 𝓥𝓪𝓷 𝓢𝓮𝓻𝓿𝓲𝓬𝓮𝓼 ")
st.subheader(f"Welcome, {st.session_state.role.title()}!")

if st.button("🔓 Logout"):
    for key in ["logged_in", "role", "user"]:
        st.session_state.pop(key, None)
    st.rerun()

# ---------------------------- Admin Section ----------------------------
if st.session_state.role == "admin":
    st.sidebar.header("📣 School Notification")
    with st.sidebar.form("notification_form"):
        selected_school = st.selectbox("Select School", SCHOOLS, key="notif_school")
        msg = st.text_area("Notification Message", key="notif_msg")
        submit_notif = st.form_submit_button("Send Notification")

        notif_file = f"{NOTIF_FOLDER}/{selected_school.replace(' ', '_').lower()}_notices.csv"

        try:
            # Try to read the file or create it with proper columns
            if os.path.exists(notif_file) and os.path.getsize(notif_file) > 0:
                df_notif = pd.read_csv(notif_file)
                # Ensure it has the right columns
                if list(df_notif.columns) != ["message", "timestamp"]:
                    df_notif = pd.DataFrame(columns=["message", "timestamp"])
            else:
                df_notif = pd.DataFrame(columns=["message", "timestamp"])

            # Append the new row as a dictionary for column safety
            new_row = {"message": msg, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            df_notif = pd.concat([df_notif, pd.DataFrame([new_row])], ignore_index=True)

            # Save back and push to GitHub
            df_notif.to_csv(notif_file, index=False)
            push_to_github(notif_file, notif_file)
            st.success("Notification sent!")
        except Exception as e:
            st.sidebar.error(f"Error sending notification: {e}")


    # Admin Tabs per School
    tabs = st.tabs(SCHOOLS)
    for i, school in enumerate(SCHOOLS):
        with tabs[i]:
            df = load_csv(school)

            st.markdown("### ➕ Add Student")
            with st.form(f"form_{school}"):
                sid = st.text_input("Student ID (Leave blank for auto)", key=f"sid_{school}")
                name = st.text_input("Student Name", key=f"name_{school}")
                fee = st.number_input("Total Fee", min_value=0, key=f"fee_{school}")
                remaining_fee = st.number_input("Remaining Fee", min_value=0, key=f"rem_fee_{school}")
                parent_name = st.text_input("Parent Name", key=f"pname_{school}")
                parent_contact = st.text_input("Parent Contact", key=f"pcontact_{school}")
                submit = st.form_submit_button("Add Student")
                if submit:
                    if not name or not parent_name or not parent_contact:
                        st.warning("Please fill required fields.")
                    else:
                        sid = sid or f"S{len(df)+1:04d}"
                        df.loc[len(df)] = [sid, name, school, fee, remaining_fee, parent_name, parent_contact]
                        save_csv(school, df)
                        st.success("Student added successfully!")

            st.markdown("### 📋 All Students")

            st.markdown("### 💰 Submit Fee Payment")
            with st.form(f"pay_form_{school}"):
                selected_student = st.selectbox("Select Student", df["student_id"] + " - " + df["name"], key=f"select_student_{school}")
                amount_paid = st.number_input("Amount Paid", min_value=0, key=f"amount_paid_{school}")
                submit_fee = st.form_submit_button("Submit Fee")

                if submit_fee:
                    sid = selected_student.split(" - ")[0]
                    idx = df[df["student_id"] == sid].index
                    if not idx.empty:
                        i = idx[0]
                        df.at[i, "remaining_fee"] = max(0, df.at[i, "remaining_fee"] - amount_paid)
                        save_csv(school, df)

                        # Save to payment history CSV
                        payment_file = f"{CSV_FOLDER}/{school.replace(' ', '_').lower()}_payments.csv"
                        if os.path.exists(payment_file):
                            df_payments = pd.read_csv(payment_file)
                        else:
                            df_payments = pd.DataFrame(columns=["student_id", "name", "amount_paid", "timestamp"])
                        df_payments.loc[len(df_payments)] = [sid, df.at[i, "name"], amount_paid, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                        df_payments.to_csv(payment_file, index=False)
                        push_to_github(payment_file, payment_file)
                        st.success(f"Fee of ₹{amount_paid} submitted for {df.at[i, 'name']}")
                    else:
                        st.error("Student not found.")
            st.dataframe(df)

# ---------------------------- Parent Section ----------------------------
elif st.session_state.role == "parent":
    school = st.session_state.user["school"]
    st.header(f"🎓 {school}")
    df = load_csv(school)
    parent_df = df[
        (df["parent_name"].fillna("").str.lower() == st.session_state.user["name"].lower()) &
        (df["parent_contact"].fillna("").astype(str) == st.session_state.user["contact"])
    ]
    if not parent_df.empty:
        st.write("### 👨‍👩‍👧‍👦 Your Child's Info")

        st.write("### 💸 Payment History")
        payment_file = f"{CSV_FOLDER}/{school.replace(' ', '_').lower()}_payments.csv"
        try:
            if os.path.exists(payment_file):
                df_payments = pd.read_csv(payment_file)
                df_payments = df_payments[df_payments["student_id"].isin(parent_df["student_id"])]
                if not df_payments.empty:
                    st.dataframe(df_payments.sort_values(by="timestamp", ascending=False).head(5))
                else:
                    st.info("No payment records found.")
            else:
                st.info("No payment records available.")
        except Exception as e:
            st.error(f"Error loading payment history: {e}")


        st.dataframe(parent_df)

        notif_file = f"{NOTIF_FOLDER}/{school.replace(' ', '_').lower()}_notices.csv"
        if not os.path.exists(notif_file) or os.path.getsize(notif_file) == 0:
            pd.DataFrame(columns=["message", "timestamp"]).to_csv(notif_file, index=False)

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
