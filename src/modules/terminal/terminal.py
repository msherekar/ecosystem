import streamlit as st
import pexpect
import re

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def update_current_dir():
    try:
        shell = st.session_state.shell
        shell.sendline('pwd')
        shell.expect(r'__EOL__\r*\n', timeout=5)
        pwd_output = shell.before.strip()
        pwd_output = pwd_output.split('\n', 1)[-1]  # Remove echoed 'pwd' line
        pwd_output = strip_ansi(pwd_output.strip())
        st.session_state.current_dir = pwd_output
    except Exception:
        st.session_state.current_dir = "~"  # fallback

# Initialize shell
# Initialize shell
if "shell" not in st.session_state:
    try:
        shell = pexpect.spawn('/bin/bash --noprofile --norc -i', encoding='utf-8', echo=False)
        shell.delaybeforesend = 0.1

        # Set a unique prompt to detect command end reliably
        shell.sendline('export PS1="__EOL__\\n"')
        shell.sendline('echo INIT_OK')
        shell.expect_exact('INIT_OK', timeout=5)
        shell.expect(r'__EOL__\r*\n', timeout=5)

        # Send your welcome message as an echo command
        welcome_message = 'echo "Welcome to your Streamlit Terminal! Type commands below and press Enter."'
        shell.sendline(welcome_message)
        shell.expect(r'__EOL__\r*\n', timeout=5)

        # Capture and store welcome message output in history
        welcome_output = shell.before.strip()
        welcome_output = welcome_output.split('\n', 1)[-1]  # Remove echoed command
        st.session_state.terminal_history = [welcome_output]

        st.session_state.shell = shell
        st.session_state.current_dir = "~"
        update_current_dir()
    except Exception as e:
        st.session_state.terminal_history = [f"Error initializing shell: {e}"]
        st.session_state.current_dir = "~"

if "run_command" not in st.session_state:
    st.session_state.run_command = False
if "input_key" not in st.session_state:
    st.session_state.input_key = "input_0"
if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0

def execute_command(command):
    try:
        if not command.strip():
            return ""

        # Block interactive shells that can't be handled here
        if command.strip() in ['python', 'python3', 'ipython']:
            return "⚠️ Interactive shells are not supported."

        if command.strip() == "clear":
            st.session_state.terminal_history = []
            return ""

        shell = st.session_state.shell
        shell.sendline(command)
        shell.expect(r'__EOL__\r*\n', timeout=10)

        output = shell.before.strip()
        output = output.split('\n', 1)[-1]  # Remove echoed command line
        output = strip_ansi(output.strip())

        update_current_dir()

        return output

    except pexpect.TIMEOUT:
        return "❌ Command timed out"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def submit_command():
    st.session_state.run_command = True

def terminal():
    st.markdown("""
        <style>
        .terminal {
            background-color: black;
            color: #00FF00;
            font-family: monospace;
            padding: 20px;
            border-radius: 10px;
            height: 600px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .cursor {
            display: inline-block;
            width: 10px;
            height: 20px;
            background-color: #00FF00;
            animation: blink 1s step-start infinite;
            vertical-align: bottom;
        }
        input[type="text"] {
            border: 2px solid #00FF00;
            border-radius: 5px;
            background-color: black;
            color: #00FF00;
            font-family: monospace;
            padding: 5px;
        }
        input::placeholder {
            color: #00FF00 !important;
            opacity: 1;
        }
        @keyframes blink { 50% { opacity: 0; } }
        </style>
    """, unsafe_allow_html=True)

    
    terminal_output = "\n".join(st.session_state.terminal_history)

    st.markdown(f"""
        <div class="terminal">
        {terminal_output}
        </div>
    """, unsafe_allow_html=True)

    
    

    st.markdown("---")

    st.text_input(
        "Command",
        placeholder="Enter command",
        label_visibility="collapsed",
        key=st.session_state.input_key,
        on_change=submit_command
    )

    if st.session_state.run_command:
        cmd = st.session_state[st.session_state.input_key]
        st.session_state.terminal_history.append(f"$ {cmd}")
        output = execute_command(cmd)
        if output:
            st.session_state.terminal_history.append(output)
        st.session_state.run_command = False
        st.session_state.input_counter += 1
        st.session_state.input_key = f"input_{st.session_state.input_counter}"
        st.rerun()


