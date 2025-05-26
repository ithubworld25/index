# BPMN Text Parser

This example application converts a plain text business process description into a BPMN 2.0 diagram. At startup, the server applies simple AI heuristics to detect actors and their tasks, creating pools and lanes accordingly.

## Usage

```
python app.py
```

Open the browser at `http://localhost:8000/`. Paste text describing your process and click **Generate**. Lines formatted as `Actor: Task` are preferred, but the server also tries to guess the actor and action when no colon is present. Tasks are grouped into lanes by actor inside a single pool, and the resulting diagram can be edited and downloaded as a `.bpmn` file.
