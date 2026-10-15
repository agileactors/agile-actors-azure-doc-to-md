# Newer models (claude-sonnet-5-5, claude-opus-5-5) reject two things this
# pipeline relies on: thinking={"type": "disabled"} and the forced tool_choice. 
# Both return a 400 error, so switching to one of them means changing those calls as well.
MODEL_NAME = "claude-sonnet-5"
