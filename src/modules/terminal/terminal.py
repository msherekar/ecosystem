"""
LEGACY FEATURE: Terminal Interface
This module provides an interactive terminal interface within the Streamlit app.
Note: This feature was removed in the ecosystem version but is kept here for backward compatibility.
"""

import streamlit as st
import pexpect
import re
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

# Initialize all session state variables
if "shell" not in st.session_state:
    st.session_state.shell = None
if "command_history" not in st.session_state:
    st.session_state.command_history = []
if "history_index" not in st.session_state:
    st.session_state.history_index = -1
if "run_command" not in st.session_state:
    st.session_state.run_command = False
if "input_key" not in st.session_state:
    st.session_state.input_key = "input_0"
if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0
if "terminal_history" not in st.session_state:
    st.session_state.terminal_history = []
if "current_dir" not in st.session_state:
    st.session_state.current_dir = "~"

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def update_current_dir():
    try:
        shell = st.session_state.shell
        shell.sendline('pwd')
        shell.expect(r'\$ ', timeout=5)
        pwd_output = shell.before.strip()
        pwd_output = pwd_output.split('\n', 1)[-1]  # Remove echoed 'pwd' line
        pwd_output = strip_ansi(pwd_output.strip())
        # Convert ~ to full home directory path
        if pwd_output == "~":
            shell.sendline('echo $HOME')
            shell.expect(r'\$ ', timeout=5)
            home_dir = shell.before.strip().split('\n', 1)[-1]
            st.session_state.current_dir = home_dir
        else:
            st.session_state.current_dir = pwd_output
    except Exception:
        # If there's an error, try to get home directory
        try:
            shell = st.session_state.shell
            shell.sendline('echo $HOME')
            shell.expect(r'\$ ', timeout=5)
            home_dir = shell.before.strip().split('\n', 1)[-1]
            st.session_state.current_dir = home_dir
        except Exception:
            st.session_state.current_dir = "/home"  # fallback

# Initialize shell
if st.session_state.shell is None:
    try:
        shell = pexpect.spawn('/bin/bash --noprofile --norc -i', encoding='utf-8', echo=False)
        shell.delaybeforesend = 0.1

        # Set a directory-based prompt and wait for it
        shell.sendline('export PS1="\w $ "')
        shell.expect(r'\$ ', timeout=5)  # Wait for the prompt

        # Verify shell is working
        shell.sendline('echo "INIT_OK"')
        shell.expect(r'INIT_OK', timeout=5)
        shell.expect(r'\$ ', timeout=5)  # Wait for prompt after echo

        # Send welcome message
        welcome_message = 'echo "Welcome to your Terminal! Type commands below and press Enter."'
        shell.sendline(welcome_message)
        shell.expect(r'\$ ', timeout=5)

        # Capture and store welcome message output in history
        welcome_output = shell.before.strip()
        welcome_output = welcome_output.split('\n', 1)[-1]  # Remove echoed command
        st.session_state.terminal_history = [welcome_output]

        st.session_state.shell = shell
        update_current_dir()  # This will now set the full path
    except Exception as e:
        st.session_state.terminal_history = [f"Error initializing shell: {str(e)}"]
        update_current_dir()  # This will set the fallback path

def execute_command(command):
    try:
        if not command.strip():
            return ""

        if command.strip() == "clear":
            st.session_state.terminal_history = []
            return ""

        # Add command to history
        st.session_state.command_history.append(command)

        # Handle commands that need pager or interactive input
        pager_commands = ['less', 'more', 'head', 'tail', 'git', 'man']
        needs_pager = any(cmd in command.split() for cmd in pager_commands)
        
        if needs_pager:
            command = f"{command} | cat"

        # Set a longer timeout for potentially long-running commands
        timeout = 30  # 30 seconds timeout
        
        # Send the command
        st.session_state.shell.sendline(command)
        
        try:
            # First try to expect the prompt
            st.session_state.shell.expect(r'\$ ', timeout=timeout)
            output = st.session_state.shell.before.strip()
        except pexpect.TIMEOUT:
            # If timeout occurs, try to get whatever output we have
            output = st.session_state.shell.before.strip()
            if not output:
                return "❌ Command timed out. Try using a more specific command or check if the command is still running."
        
        # Clean up the output
        output = output.split('\n', 1)[-1]  # Remove echoed command line
        output = strip_ansi(output.strip())
        
        # If output is empty but command didn't timeout, it might be a background process
        if not output and not needs_pager:
            return "Command executed (no output)"

        update_current_dir()
        return output

    except Exception as e:
        return f"❌ Error: {str(e)}"

def submit_command():
    st.session_state.run_command = True

def navigate_history(direction):
    if not st.session_state.command_history:
        return
    
    if direction == "up":
        if st.session_state.history_index > 0:
            st.session_state.history_index -= 1
    else:  # down
        if st.session_state.history_index < len(st.session_state.command_history) - 1:
            st.session_state.history_index += 1
    
    if 0 <= st.session_state.history_index < len(st.session_state.command_history):
        st.session_state[st.session_state.input_key] = st.session_state.command_history[st.session_state.history_index]

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
            color: #00FF00;
            font-family: monospace;
            padding: 5px;
            background-color: black;
        }
        input::placeholder {
            color: #00FF00 !important;
            opacity: 1;
        }
        .current-dir {
            color: #00FF00;
            font-family: monospace;
            margin-bottom: 10px;
        }
        @keyframes blink { 50% { opacity: 0; } }
        </style>
    """, unsafe_allow_html=True)

    # Display current directory above terminal
    st.markdown(f"""
        <div class="current-dir">
        Current Directory: {st.session_state.current_dir}
        </div>
    """, unsafe_allow_html=True)

    terminal_output = "\n".join(st.session_state.terminal_history)

    st.markdown(f"""
        <div class="terminal">
        {terminal_output}
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Add keyboard event handling for history navigation
    st.markdown("""
        <script>
        document.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowUp') {
                window.parent.postMessage({type: 'history', direction: 'up'}, '*');
            } else if (e.key === 'ArrowDown') {
                window.parent.postMessage({type: 'history', direction: 'down'}, '*');
            }
        });
        </script>
    """, unsafe_allow_html=True)

    # Handle history navigation messages
    if st.session_state.get('history_message'):
        navigate_history(st.session_state.history_message['direction'])
        st.session_state.history_message = None

    st.text_input(
        "Command",
        placeholder="Enter command",
        label_visibility="collapsed",
        key=st.session_state.input_key,
        on_change=submit_command
    )

    if st.session_state.run_command:
        cmd = st.session_state[st.session_state.input_key]
        prompt = "$ "
        st.session_state.terminal_history.append(f"{prompt} {cmd}")
        output = execute_command(cmd)
        if output:
            st.session_state.terminal_history.append(output)
        st.session_state.run_command = False
        st.session_state.input_counter += 1
        st.session_state.input_key = f"input_{st.session_state.input_counter}"
        st.rerun()


