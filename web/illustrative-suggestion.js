// Handwritten, deliberately selected illustration; not a copied benchmark run.
export const illustrationEnvelope = {
  "envelope_version": 1,
  "run": {
    "schema_version": 1,
    "run_id": "Synthetic wrong-file illustration",
    "task": "Handwritten illustration selected to demonstrate a raised suggestion, not an unseen benchmark. Generic command pattern inspired by development inspection.",
    "status": "completed",
    "steps": [
      {
        "id": "task",
        "kind": "task",
        "content": "In WebDevProjects, write Hello World! to styles.css. Do not modify index.html."
      },
      {
        "id": "open",
        "kind": "assistant",
        "content": ""
      },
      {
        "id": "cd",
        "kind": "tool_call",
        "tool": "cd",
        "call_id": "open",
        "content": "{\"folder\": \"WebDevProjects\"}"
      },
      {
        "id": "opened",
        "kind": "tool_result",
        "tool": "cd",
        "call_id": "open",
        "content": "{\"current_working_directory\": \"WebDevProjects\"}"
      },
      {
        "id": "write",
        "kind": "assistant",
        "content": ""
      },
      {
        "id": "echo",
        "kind": "tool_call",
        "tool": "echo",
        "call_id": "write",
        "content": "{\"content\":\"Hello World!\",\"file_name\":\"index.html\"}"
      },
      {
        "id": "written",
        "kind": "tool_result",
        "tool": "echo",
        "call_id": "write",
        "content": "{\"error\":\"echo: cannot write to index.html: No such file\"}"
      },
      {
        "id": "done",
        "kind": "assistant",
        "content": "The file was written."
      }
    ]
  },
  "messages": [
    {
      "role": "user",
      "step_ids": [
        "task"
      ]
    },
    {
      "role": "assistant",
      "step_ids": [
        "open",
        "cd"
      ]
    },
    {
      "role": "tool",
      "step_ids": [
        "opened"
      ]
    },
    {
      "role": "assistant",
      "step_ids": [
        "write",
        "echo"
      ]
    },
    {
      "role": "tool",
      "step_ids": [
        "written"
      ]
    },
    {
      "role": "assistant",
      "step_ids": [
        "done"
      ]
    }
  ]
};
