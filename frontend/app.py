import pandas as pd
import streamlit as st
import api

st.set_page_config(page_title="Business Ops", layout="wide")
st.title("Business Ops")

if "token" not in st.session_state:
    st.session_state.token = None


def log_out():
    st.session_state.token = None
    st.rerun()


if st.session_state.token is None:
    st.subheader("Log in")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Log in"):
        try:
            token = api.login(email, password)
        except RuntimeError as error:
            st.error(str(error))
        else:
            if token is None:
                st.error("Wrong email or password.")
            else:
                st.session_state.token = token
                st.rerun()
else:
    token = st.session_state.token

    if st.button("Log out"):
        log_out()

    try:
        enquiries = api.get("/enquiries", token)
        waiting = api.get("/follow-ups", token, params={"status": "pending"})
        usage = api.get("/usage", token)
        notes = api.get("/knowledge", token)
    except api.SessionExpired:
        st.warning("Your session ended. Please log in again.")
        log_out()
    except RuntimeError as error:
        st.error(str(error))
        st.stop()

    tab_dashboard, tab_enquiries, tab_reminders, tab_knowledge = st.tabs(
        ["Dashboard", "Enquiries", "Reminders", "Knowledge"]
    )

    with tab_dashboard:
        col1, col2, col3 = st.columns(3)
        col1.metric("Enquiries", len(enquiries))
        col2.metric("Reminders waiting", len(waiting))
        col3.metric(
            "AI calls used",
            f"{usage['ai_calls_used']} / {usage['ai_call_limit']}",
        )

    with tab_enquiries:
        manual = [e for e in enquiries if e["needs_manual_sorting"]]
        if manual:
            st.warning(
                f"{len(manual)} enquiry(ies) need to be sorted by a person."
            )

        if not enquiries:
            st.info("No enquiries yet.")
        else:
            newest_first = sorted(
                enquiries, key=lambda e: e["id"], reverse=True
            )
            table = pd.DataFrame(newest_first)[
                [
                    "id",
                    "message",
                    "category",
                    "priority",
                    "status",
                    "assigned_to",
                    "needs_manual_sorting",
                ]
            ]
            st.dataframe(table, width="stretch", hide_index=True)

    with tab_reminders:
        if not waiting:
            st.info("No reminders waiting.")

        messages = {e["id"]: e["message"] for e in enquiries}

        for item in waiting:
            with st.container(border=True):
                st.caption(
                    f"Reminder {item['id']} for enquiry {item['enquiry_id']}"
                )
                st.write("**The customer wrote:**")
                st.write(messages.get(item["enquiry_id"], ""))
                st.write("**Suggested follow-up (check it before sending):**")
                if item["draft_message"]:
                    st.info(item["draft_message"])
                else:
                    st.warning(
                        "No draft was written. Please write this one yourself."
                    )

                if st.button("Mark as done", key=f"done_{item['id']}"):
                    try:
                        api.patch(f"/follow-ups/{item['id']}/done", token)
                    except api.SessionExpired:
                        st.warning("Your session ended. Please log in again.")
                        log_out()
                    except RuntimeError as error:
                        st.error(str(error))
                        st.stop()
                    st.rerun()

    with tab_knowledge:
        st.subheader("Ask a question")
        st.caption("The answer comes only from the saved notes below.")
        question = st.text_input("Your question", key="question")

        if st.button("Ask"):
            if not question.strip():
                st.warning("Please type a question first.")
            else:
                result = None
                with st.spinner("Looking through the saved notes..."):
                    try:
                        result = api.post(
                            "/knowledge/ask", token, {"question": question}
                        )
                    except api.SessionExpired:
                        st.warning("Your session ended. Please log in again.")
                        log_out()
                    except RuntimeError as error:
                        st.error(str(error))

                if result is not None:
                    if result["found"]:
                        st.success(result["answer"])
                        names = ", ".join(
                            f"{s['title']} (note {s['id']})"
                            for s in result["sources"]
                        )
                        st.caption(f"Source: {names}")
                    else:
                        st.warning(result["answer"])

        st.divider()
        st.subheader("Saved notes")

        if not notes:
            st.info("No notes saved yet.")
        for note in notes:
            with st.expander(f"{note['title']} (note {note['id']})"):
                st.write(note["content"])

        st.divider()
        st.subheader("Add a note (owner only)")
        with st.form("add_note", clear_on_submit=True):
            title = st.text_input("Title")
            content = st.text_area("Content")
            submitted = st.form_submit_button("Save note")

        if submitted:
            if not title.strip() or not content.strip():
                st.warning("Please fill in both the title and the content.")
            else:
                try:
                    api.post(
                        "/knowledge",
                        token,
                        {"title": title, "content": content},
                    )
                except api.SessionExpired:
                    st.warning("Your session ended. Please log in again.")
                    log_out()
                except RuntimeError as error:
                    st.error(str(error))
                else:
                    st.rerun()