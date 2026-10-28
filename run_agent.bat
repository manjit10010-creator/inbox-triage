@echo off
cd /d "C:\Users\manji\OneDrive\Desktop\automated inboxlead triage assistant\inbox-triage"
set AGENT_AUTO=1
echo ---- %date% %time% ---- >> agent.log
uv run agent.py >> agent.log 2>&1