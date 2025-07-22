import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import base64
from datetime import datetime

# ------------------ Initialize Firebase ------------------
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firebase_credentials"])
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["firebase_url"]
    })

# ------------------ Helpers ------------------
def get_school_ref(school):
    return db.reference(f"schools/{school}/students")

def get_payment_ref(school):
    return db.reference(f"schools/{school}/payments")

def get_notification_ref(school):
    return db.reference(f"schools/{school}/notifications")

def load_data(school):
    data = get_school_ref(school).get()
    if data:
        df = pd.DataFrame.from_dict(data, orient='index')
        expected_cols = ["student_id", "name", "school_name", "fee", "remaining_fee", "parent_name", "parent_contact"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        return df[expected_cols]
    else:
        return pd.DataFrame(columns=["student_id", "name", "school_name", "fee", "remaining_fee", "parent_name", "parent_contact"])

# ------------------ Session Management ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user" not in st.session_state:
    st.session_state.user = None

# ------------------ Login ------------------
def login():
    st.title("School Van Management System")
    role = st.selectbox("Login as", ["Admin", "Parent"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if role == "Admin" and username in st.secrets["admin_users"] and password == st.secrets["admin_users"][username]:
            st.session_state.logged_in = True
            st.session_state.role = "admin"
            st.session_state.user = username
        elif role == "Parent":
            school = st.text_input("Enter School Name")
            df = load_data(school)
            if not df.empty and username in df["parent_contact"].values:
                st.session_state.logged_in = True
                st.session_state.role = "parent"
                st.session_state.user = username
        else:
            st.error("Invalid credentials")

# ------------------ Admin Dashboard ------------------
def admin_dashboard():
    st.title("Admin Dashboard")
    school = st.selectbox("Select School", ["School_A", "School_B"])
    df = load_data(school)

    with st.expander("➕ Add Student"):
        with st.form("add_form"):
            name = st.text_input("Student Name")
            fee = st.number_input("Total Fee", min_value=0)
            remaining = st.number_input("Remaining Fee", min_value=0)
            pname = st.text_input("Parent Name")
            contact = st.text_input("Parent Contact")
            sid = st.text_input("Student ID (Leave blank for auto)", value="")
            submit = st.form_submit_button("Add Student")
            if submit:
                sid = sid or f"S{len(df)+1:04d}"
                df.loc[len(df)] = [sid, name, school, fee, remaining, pname, contact]
                data_to_push = df.set_index("student_id").T.to_dict()
                get_school_ref(school).set(data_to_push)
                st.success("Student added successfully")

    with st.expander("📢 Send Notification"):
        notification = st.text_area("Enter Notification Message")
        if st.button("Send Notification"):
            get_notification_ref(school).push({"message": notification, "timestamp": str(datetime.now())})
            st.success("Notification sent")

    with st.expander("💰 Record Fee Payment"):
        if df.empty:
            st.warning("No students found")
        else:
            df = df.reset_index(drop=True)
            student_list = df["student_id"] + " - " + df["name"]
            selected = st.selectbox("Select Student", student_list)
            amount = st.number_input("Amount Paid", min_value=0)
            if st.button("Record Payment"):
                idx = student_list[student_list == selected].index[0]
                df.at[idx, "remaining_fee"] = max(0, df.at[idx, "remaining_fee"] - amount)
                get_school_ref(school).set(df.set_index("student_id").T.to_dict())
                get_payment_ref(school).push({
                    "student_id": df.at[idx, "student_id"],
                    "name": df.at[idx, "name"],
                    "amount": amount,
                    "timestamp": str(datetime.now())
                })
                st.success("Payment recorded")

    with st.expander("📦 All Student Data"):
        st.dataframe(df)

# ------------------ Parent Dashboard ------------------
def parent_dashboard():
    st.title("Parent Dashboard")
    school = st.selectbox("Enter School", ["School_A", "School_B"])
    df = load_data(school)
    if not df.empty:
        student = df[df["parent_contact"] == st.session_state.user]
        if not student.empty:
            st.subheader("Student Details")
            st.dataframe(student)

            st.subheader("Notifications")
            notes = get_notification_ref(school).get()
            if notes:
                for k, v in notes.items():
                    st.info(f"📢 {v['message']}\n🕒 {v['timestamp']}")

            st.subheader("Payment History")
            payments = get_payment_ref(school).get()
            if payments:
                for k, v in payments.items():
                    if v["student_id"] == student.iloc[0]["student_id"]:
                        st.success(f"💰 Rs.{v['amount']} paid on {v['timestamp']}")

# ------------------ Main App ------------------
if not st.session_state.logged_in:
    login()
else:
    if st.session_state.role == "admin":
        admin_dashboard()
    elif st.session_state.role == "parent":
        parent_dashboard()

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user = None
        st.experimental_rerun()
