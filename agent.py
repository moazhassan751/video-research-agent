"""
agent.py — The Agentic Orchestration Loop
==========================================

This is the CORE of the project. It implements the loop that makes this an
"agent" rather than a simple chatbot.

=== WHY AN AGENT NEEDS A LOOP (not just a single API call) ===

A normal chatbot flow is:
    User message → LLM → Text response → Done

An agent flow is:
    User message → LLM → "I need to call a tool" → YOUR CODE runs the tool
    → Result goes back to LLM → "I need another tool" → YOUR CODE runs it
    → Result goes back to LLM → "Now I have everything" → Final text response

For THIS specific project, the flow is always at least 3 turns:

    Turn 0 (User):      "Find a video about transformers and transcribe it"
    Turn 1 (Model):      Calls search_video(query="transformers explained")
    Turn 1 (Your code):  Runs SerpApi, returns {"url": "...", "title": "..."}
    Turn 2 (Model):      Calls transcribe_video(video_url="...", video_title="...")
    Turn 2 (Your code):  Runs Gemini, saves transcript, returns {"transcript": "..."}
    Turn 3 (Model):      "Here's what I found: [summary of transcript]"

Without a loop, you'd need to hardcode this exact sequence. With a loop,
the MODEL decides what to do next — that's what makes it an "agent."

=== WHY LOCAL TOOL CALLING (not built-in or MCP) ===

"Local tool calling" means:
  - YOU write the Python functions (search_video, transcribe_video)
  - YOU define the JSON schemas that describe them
  - YOU execute the functions when the model asks for them
  - The model never touches your code — it only sees schemas and results

Why is this the right pattern here?
  1. We're calling specific APIs (SerpApi, Gemini) that aren't built into any LLM
  2. We need custom logic (saving to disk, URL validation, error formatting)
  3. We want full control over what happens — no black-box tool execution
  4. MCP (Model Context Protocol) is for connecting to REMOTE tool servers.
     Here, everything runs in our own process. No server needed.

=== WHAT tool_call_id MATCHING IS FOR ===

When the model returns a tool call, it includes an `id` field (like "call_abc123").
When you send the tool result back, you MUST include that same `id` in the
tool message's `tool_call_id` field.

Why? Because the model might request MULTIPLE tool calls in one turn (parallel
tool calling). The `id` is how the model matches "this result goes with THAT
specific call." If you mix up the IDs, the model would think the search result
is the transcription result or vice versa — completely corrupting its reasoning.

In our case, parallel calling doesn't happen (transcription depends on search
output), but the protocol still requires ID matching.

=== WHY PARALLEL TOOL CALLING DOESN'T APPLY HERE ===

Parallel tool calling is when the model asks for multiple tools in ONE turn:
    "Call search_video AND transcribe_video at the same time"

This CAN'T work for us because transcribe_video needs the URL that
search_video returns. You can't transcribe a video before you know which
video to transcribe. The dependency chain is:
    search_video(query) → url → transcribe_video(url) → transcript

So the model will always call them sequentially: search first, then transcribe.
Our loop handles this naturally — each iteration processes whatever the model
asks for, then sends the result back for the next decision.
"""

import json
from groq import Groq

from tools.video_search import search_video, VIDEO_SEARCH_SCHEMA
from tools.transcription import transcribe_video, TRANSCRIPTION_SCHEMA


# =============================================================================
# TOOL REGISTRY
# =============================================================================
# This maps tool names (strings) to their Python functions.
# When the model says "call search_video", we look up "search_video" in this
# dict and call the corresponding function.
#
# Why a dict? Because it's extensible. To add a new tool, you just:
#   1. Write the function
#   2. Write the schema
#   3. Add one entry here
#   4. Add the schema to TOOL_SCHEMAS below
# No other code changes needed.

TOOL_FUNCTIONS = {
    "search_video": search_video,
    "transcribe_video": transcribe_video,
}

# The list of schemas we send to Groq. The model reads ALL of these to decide
# which tool (if any) to call at each turn.
TOOL_SCHEMAS = [VIDEO_SEARCH_SCHEMA, TRANSCRIPTION_SCHEMA]


# =============================================================================
# THE SYSTEM PROMPT
# =============================================================================
# This tells the model WHO it is and HOW to behave. Key points:
#   - It knows it has access to two tools
#   - It knows to search first, then transcribe
#   - It knows to present a useful summary at the end

SYSTEM_PROMPT = (
    "You are a helpful video research assistant. You have access to two tools:\n"
    "1. search_video — finds YouTube videos matching a query\n"
    "2. transcribe_video — transcribes the audio of a YouTube video\n\n"
    "When a user asks you to find and transcribe a video:\n"
    "  - First, use search_video to find a relevant YouTube video\n"
    "  - Then, use transcribe_video with the URL from the search result\n"
    "  - Finally, provide a clear summary of the video content based on the transcript\n\n"
    "Always tell the user the video title, channel, URL, and where the transcript was saved.\n"
    "If a tool returns an error, explain what went wrong and suggest alternatives."
)


# =============================================================================
# THE ORCHESTRATION LOOP
# =============================================================================
def run_agent(user_query: str, max_iterations: int = 10, status_callback=None) -> str:
    """
    Runs the agentic loop: sends the user query to Groq, executes any tool
    calls the model requests, and returns the model's final text response.

    Args:
        user_query:      The user's natural-language question
        max_iterations:  Safety cap to prevent infinite loops
        status_callback: Optional callable(event_type: str, data: dict) for progress tracking

    Returns:
        The model's final text answer as a string
    """
    # Initialize the Groq client. It reads GROQ_API_KEY from the environment
    # automatically (the Groq SDK does this by default).
    client = Groq()

    # -----------------------------------------------------------------
    # THE MESSAGES ARRAY — This is the "memory" of the conversation.
    #
    # At the start (Turn 0), it looks like:
    #   [
    #     {"role": "system", "content": "You are a helpful video research..."},
    #     {"role": "user",   "content": "find a video about transformers"}
    #   ]
    #
    # After Turn 1 (model calls search_video, we execute it), it grows to:
    #   [
    #     {"role": "system",    "content": "You are a helpful..."},
    #     {"role": "user",      "content": "find a video about transformers"},
    #     {"role": "assistant", "content": null, "tool_calls": [{...}]},
    #     {"role": "tool",      "tool_call_id": "call_abc", "content": '{"url": "..."}'},
    #   ]
    #
    # After Turn 2 (model calls transcribe_video, we execute it):
    #   [
    #     ... all previous messages ...,
    #     {"role": "assistant", "content": null, "tool_calls": [{...}]},
    #     {"role": "tool",      "tool_call_id": "call_def", "content": '{"transcript": "..."}'},
    #   ]
    #
    # At Turn 3, the model sees ALL of this history and generates a final
    # text response (no tool calls). That's the answer we return.
    # -----------------------------------------------------------------
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    print(f"\n{'='*60}")
    print(f"=== AGENT STARTED ===")
    print(f"{'='*60}")
    print(f"User query: {user_query}")
    print(f"Available tools: {list(TOOL_FUNCTIONS.keys())}")
    print(f"Max iterations: {max_iterations}")

    for iteration in range(max_iterations):
        print(f"\n{'-'*60}")
        print(f"--- ITERATION {iteration + 1}/{max_iterations} ---")
        print(f"{'-'*60}")
        print(f"Sending {len(messages)} messages to Groq...")

        # ==============================================================
        # STEP 1: Send the current messages to Groq
        #
        # This is the "model thinking" step. YOUR code does nothing here
        # except wait. The LLM reads all the messages (including any
        # previous tool results) and decides:
        #   a) "I need to call a tool" → returns tool_calls
        #   b) "I have enough info"   → returns text content (final answer)
        #
        # tool_choice="auto" means: "Model, YOU decide whether to call
        # a tool or just respond with text." We don't force it.
        # ==============================================================
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0,  # Deterministic — we want reliable tool calls
            )
        except Exception as e:
            error_msg = f"Groq API call failed: {e}"
            print(f"[ERROR] {error_msg}")
            return f"Error: {error_msg}"

        # Get the model's response message
        response_message = response.choices[0].message

        # ==============================================================
        # STEP 2: Check if the model wants to call tools
        #
        # If response_message.tool_calls is NOT None/empty, the model is
        # saying: "I can't answer yet — I need to run these tools first."
        #
        # If it IS None/empty, the model is giving its final text answer.
        # ==============================================================
        if not response_message.tool_calls:
            # ----------------------------------------------------------
            # NO TOOL CALLS → This is the final answer
            #
            # The model has seen enough information (from previous tool
            # results) to compose a text response. We're done.
            # ----------------------------------------------------------
            final_answer = response_message.content
            print(f"\n[SUCCESS] MODEL RESPONDED WITH FINAL ANSWER (no tool calls)")
            print(f"{'='*60}")
            return final_answer

        # ----------------------------------------------------------
        # TOOL CALLS DETECTED → Execute each one
        #
        # The model returned one or more tool_calls. For each one:
        #   1. Parse the function name and arguments
        #   2. Look up the function in our registry
        #   3. Execute it (this is YOUR code doing real work)
        #   4. Append the result to messages so the model sees it
        # ----------------------------------------------------------

        # First, append the assistant's message (with tool_calls) to the
        # conversation history. The model needs to see its own previous
        # messages to maintain coherent multi-turn reasoning.
        messages.append(response_message)

        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            call_id = tool_call.id

            print(f"\n[TOOL CALL] DETECTED:")
            print(f"   Name: {function_name}")
            print(f"   ID:   {call_id}")
            print(f"   Raw args: {tool_call.function.arguments}")

            # ==========================================================
            # STEP 3: Parse and validate tool arguments
            #
            # The model returns arguments as a JSON STRING. We need to
            # parse it into a Python dict. But the model can produce
            # malformed JSON — it's generating text, not running code.
            #
            # Example of what could go wrong:
            #   Model outputs: {"query": "transformers",}  (trailing comma)
            #   json.loads() would raise JSONDecodeError
            #
            # If we didn't catch this, our whole agent loop would crash.
            # Instead, we send an error back as the tool result, and the
            # model can try again with corrected arguments.
            # ==========================================================
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                error_result = json.dumps({
                    "error": f"Invalid JSON in tool arguments: {e}. "
                             f"Raw args were: {tool_call.function.arguments}"
                })
                print(f"   [ERROR] Bad JSON from model: {e}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": error_result,
                })
                continue

            print(f"   Parsed args: {arguments}")

            # ==========================================================
            # STEP 4: Look up and execute the tool function
            #
            # We check if the function name is in our registry. If the
            # model hallucinates a tool name that doesn't exist (rare but
            # possible), we return an error instead of crashing.
            # ==========================================================
            if function_name not in TOOL_FUNCTIONS:
                error_result = json.dumps({
                    "error": f"Unknown tool: '{function_name}'. "
                             f"Available tools: {list(TOOL_FUNCTIONS.keys())}"
                })
                print(f"   [ERROR] Unknown tool name: {function_name}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": error_result,
                })
                continue

            # Execute the tool — THIS is where YOUR code does real work
            # (calling SerpApi, calling Gemini, saving files, etc.)
            # The model is not involved at all during this step.
            tool_function = TOOL_FUNCTIONS[function_name]

            print(f"   [EXECUTE] Executing {function_name}()...")
            if status_callback:
                status_callback("tool_start", {"name": function_name, "args": arguments, "iteration": iteration + 1})

            try:
                result = tool_function(**arguments)
            except TypeError as e:
                # This catches cases where the model provided wrong argument
                # names. E.g., the model passes {"search_query": "..."} but
                # our function expects {"query": "..."}.
                result = json.dumps({
                    "error": f"Wrong arguments for {function_name}: {e}. "
                             f"Expected parameters are defined in the tool schema."
                })
                print(f"   [ERROR] Argument mismatch: {e}")
            except Exception as e:
                # Catch-all for any unexpected error in the tool function.
                # This should be rare since our tool functions have their own
                # try/except blocks, but defense in depth is good practice.
                result = json.dumps({
                    "error": f"Tool {function_name} crashed unexpectedly: {e}"
                })
                print(f"   [ERROR] Unexpected error: {e}")

            # Pretty-print the result (truncated for readability)
            result_preview = result[:200] + "..." if len(result) > 200 else result
            print(f"   [OUTPUT] Result: {result_preview}")
            if status_callback:
                status_callback("tool_end", {"name": function_name, "result": result, "iteration": iteration + 1})

            # ==========================================================
            # STEP 5: Append the tool result to messages
            #
            # This is the critical "closing the loop" step. We send the
            # result back as a "tool" role message, with the SAME
            # tool_call_id that the model used.
            #
            # WHAT BREAKS IF tool_call_id IS WRONG:
            #   The Groq API will reject the request with a 400 error
            #   because it can't match the result to the call. Even if
            #   the API accepted it, the model would be confused — it
            #   asked for search results but got a transcript, or vice
            #   versa. The model's reasoning would be completely wrong.
            # ==========================================================
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,  # MUST match tool_call.id exactly
                "content": result,        # Always a string (JSON)
            })

        # Loop continues → the updated messages (now including tool results)
        # go back to the model at Step 1, and it decides what to do next.

    # If we get here, we hit max_iterations without the model giving a final answer.
    # This is a safety net — in practice, 10 iterations is way more than needed
    # for a 2-tool chain.
    print(f"\n[WARNING] Hit max iterations ({max_iterations}) without a final answer.")
    return (
        "I wasn't able to complete the task within the maximum number of steps. "
        "This might indicate an issue with the tools or the query. Please try again."
    )
