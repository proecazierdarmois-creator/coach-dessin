import streamlit as st

st.set_page_config(page_title="Test login")

st.write("USER:")
st.write(st.user)

st.write("AUTH SECRETS:")
st.write(st.secrets.get("auth", {}))

if not st.user.is_logged_in:
    st.button("Google", on_click=lambda: st.login("google"))
    st.stop()

st.success("Connecté")
st.write(st.user.email)

if st.button("Logout"):
    st.logout()
    st.rerun()