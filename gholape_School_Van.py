import streamlit as st
import firebase_admin
from firebase_admin import credentials, db

# ------------------ Initialize Firebase ------------------

if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://gholapevan-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

# ------------------ Example Firebase Usage ------------------

# Example: Read from Firebase
def read_data():
    ref = db.reference("/students")
    return ref.get()

# Example: Write to Firebase
def write_data(student_id, student_data):
    ref = db.reference(f"/students/{student_id}")
    ref.set(student_data)

# ------------------ Streamlit UI ------------------

st.title("🚌 School Van Management")

# Example student write
if st.button("🚀 Add Demo Student"):
    write_data("001", {
        "name": "Omkar",
        "school": "Sunshine School",
        "parent": "Mr. Kotamire",
        "fees_paid": True
    })
    st.success("Demo student added!")

# Example student read
if st.button("📖 Read Students"):
    students = read_data()
    if students:
        st.json(students)
    else:
        st.warning("No student data found.")
