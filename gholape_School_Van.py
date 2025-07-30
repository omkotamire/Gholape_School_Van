import streamlit as st
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import json

# ---------------------------- FIREBASE INIT ----------------------------
if not firebase_admin._apps:
    #cred = credentials.Certificate(st.secrets["firebase"])
    
    cred_dict = json.loads(st.secrets["firebase"])  # Convert JSON string to dict
    cred = credentials.Certificate(cred_dict)

    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://your-project-id.firebaseio.com"  # Replace with your actual URL
    })

# ---------------------------- SESSION INIT ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user" not in st.session_state:
    st.session_state.user = None

SCHOOLS = ["School A", "School B", "School C", "School D"]

# ---------------------------- UTILS ----------------------------
def get_school_ref(school):
    return db.reference(f"schools/{school.replace(' ', '_')}")

def get_notif_ref(school):
    return db.reference(f"notifications/{school.replace(' ', '_')}")

def load_data(school):
    ref = get_school_ref(school)
    data = ref.get()
    if not data:
        return pd.DataFrame(columns=["name", "school_name", "fee", "remaining_fee", "parent_name", "parent_contact"])
    
    df = pd.DataFrame(data.values())
    df["fee"] = pd.to_numeric(df.get("fee", 0), errors="coerce").fillna(0).astype(int)
    df["remaining_fee"] = pd.to_numeric(df.get("remaining_fee", 0), errors="coerce").fillna(0).astype(int)
    return df

def save_data(school, df):
    data_dict = df.to_dict(orient="records")
    get_school_ref(school).set({f"S{i+1:04d}": record for i, record in enumerate(data_dict)})

def append_payment(school, payment):
    db.reference(f"payments/{school.replace(' ', '_')}").push(payment)

def load_payments(school):
    data = db.reference(f"payments/{school.replace(' ', '_')}").get()
    return pd.DataFrame(data.values()) if data else pd.DataFrame(columns=["name", "amount_paid", "timestamp"])

def append_notification(school, msg):
    notif = {"message": msg, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    get_notif_ref(school).push(notif)

def load_notifications(school):
    data = get_notif_ref(school).get()
    return pd.DataFrame(data.values()) if data else pd.DataFrame(columns=["message", "timestamp"])

# ---------------------------- LOGIN ----------------------------
if not st.session_state.logged_in:
    st.title("🚌 Welcome to Gholape School Van Services")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        admin_users = st.secrets["admin_users"]
        if username in admin_users and password == admin_users[username]:
            st.session_state.logged_in = True
            st.session_state.role = "admin"
            st.session_state.user = username
        else:
            for school in SCHOOLS:
                df = load_data(school)
                match = df[
                    (df["parent_name"].fillna("").str.lower() == username.lower()) &
                    (df["parent_contact"].fillna("").astype(str) == password)
                ]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.role = "parent"
                    st.session_state.user = {"name": username, "contact": password, "school": school}
                    break
            if not st.session_state.logged_in:
                st.error("Invalid credentials")
    st.stop()

# ---------------------------- DASHBOARD ----------------------------
st.title("🚌 Welcome to Gholape School Van Services")
st.subheader(f"Welcome, {st.session_state.role.title()}!")

if st.button("🔓 Logout"):
    for key in ["logged_in", "role", "user"]:
        st.session_state.pop(key, None)
    st.rerun()

# ---------------------------- ADMIN ----------------------------
if st.session_state.role == "admin":
    st.sidebar.header("📣 School Notification")
    with st.sidebar.form("notif_form"):
        selected_school = st.selectbox("Select School", SCHOOLS)
        msg = st.text_area("Notification Message")
        if st.form_submit_button("Send Notification"):
            append_notification(selected_school, msg)
            st.sidebar.success("Notification sent!")

    tabs = st.tabs(SCHOOLS)
    for i, school in enumerate(SCHOOLS):
        with tabs[i]:
            df = load_data(school)

            st.markdown("### ➕ Add Student")
            with st.form(f"form_add_{school}"):
                name = st.text_input("Student Name", key=f"name_{school}")
                fee = st.number_input("Total Fee", min_value=0, key=f"fee_{school}")
                remaining = st.number_input("Remaining Fee", min_value=0, key=f"rem_{school}")
                pname = st.text_input("Parent Name", key=f"pname_{school}")
                contact = st.text_input("Parent Contact", key=f"contact_{school}")
                if st.form_submit_button("Add Student"):
                    if not name or not pname or not contact:
                        st.warning("Fill required fields")
                    else:
                        df.loc[len(df)] = {
                            "name": name,
                            "school_name": school,
                            "fee": fee,
                            "remaining_fee": remaining,
                            "parent_name": pname,
                            "parent_contact": contact
                        }
                        save_data(school, df)
                        st.success("Student added")

            st.markdown("### 📄 All Students")
            if not df.empty:
                st.dataframe(df)
            else:
                st.info("No students found.")

            st.markdown("### 💰 Submit Fee Payment")
            with st.form(f"form_pay_{school}"):
                if not df.empty:
                    selected = st.selectbox("Select Student", df["name"])
                    amt = st.number_input("Amount Paid", min_value=0, key=f"amt_{school}")
                    if st.form_submit_button("Submit Fee"):
                        idx = df[df["name"] == selected].index[0]
                        df.at[idx, "remaining_fee"] = max(0, df.at[idx, "remaining_fee"] - amt)
                        save_data(school, df)
                        append_payment(school, {
                            "name": df.at[idx, "name"],
                            "amount_paid": amt,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.success(f"Fee of ₹{amt} submitted for {df.at[idx, 'name']}")

# ---------------------------- PARENT ----------------------------
elif st.session_state.role == "parent":
    school = st.session_state.user["school"]
    df = load_data(school)
    my_kids = df[(df["parent_name"].str.lower() == st.session_state.user["name"].lower()) &
                 (df["parent_contact"] == st.session_state.user["contact"])]

    st.header(f"🎓 {school}")
    st.write("### 👨‍👩‍👧 Your Child's Info")
    st.dataframe(my_kids)

    st.write("### 💸 Payment History")
    df_pay = load_payments(school)
    df_pay = df_pay[df_pay["name"].isin(my_kids["name"])]
    if not df_pay.empty:
        st.dataframe(df_pay.sort_values(by="timestamp", ascending=False).head(5))
    else:
        st.info("No payments found")

    st.write("### 📢 Notifications")
    df_notices = load_notifications(school)
    if not df_notices.empty:
        st.dataframe(df_notices.tail(5))
    else:
        st.info("No notifications")
