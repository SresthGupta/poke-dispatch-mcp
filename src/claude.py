import subprocess
import threading
import json
import time
import os


class ClaudeSession:
    def __init__(self, session_id, prompt, cwd):
        self.session_id = session_id
        self.prompt = prompt
        self.cwd = cwd
        self.status = "running"
        self.output_lines = []
        self.process = None
        self.start_time = time.time()
        self.end_time = None

    def start(self):
        self.process = subprocess.Popen(
            ["claude", "--output-format", "stream-json", "--input-format", "stream-json", "--verbose"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.expanduser(self.cwd),
            text=True,
        )
        msg = json.dumps({"type": "user", "content": self.prompt})
        self.process.stdin.write(msg + "\n")
        self.process.stdin.flush()
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()

    def _read_output(self):
        for line in self.process.stdout:
            line = line.strip()
            if line:
                self.output_lines.append(line)
                try:
                    data = json.loads(line)
                    if data.get("type") == "result":
                        self.status = "completed"
                        self.end_time = time.time()
                except json.JSONDecodeError:
                    pass
        if self.status == "running":
            self.status = "completed"
            self.end_time = time.time()

    def send_message(self, message):
        if self.process and self.process.poll() is None:
            msg = json.dumps({"type": "user", "content": message})
            self.process.stdin.write(msg + "\n")
            self.process.stdin.flush()
            return True
        return False

    def get_latest_output(self, n=20):
        return self.output_lines[-n:]

    def get_text_result(self):
        texts = []
        for line in self.output_lines:
            try:
                data = json.loads(line)
                if data.get("type") == "assistant" and "content" in data:
                    for block in data["content"]:
                        if block.get("type") == "text":
                            texts.append(block["text"])
                elif data.get("type") == "result" and "result" in data:
                    return data["result"]
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        return "\n".join(texts) if texts else "No output yet"


class ClaudeManager:
    def __init__(self):
        self.sessions = {}
        self._lock = threading.Lock()

    def run_sync(self, prompt, cwd="~/Agents", timeout=300):
        try:
            result = subprocess.run(
                ["claude", "--print", "--output-format", "text", prompt],
                cwd=os.path.expanduser(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout or result.stderr or "No output"
        except subprocess.TimeoutExpired:
            return "Task timed out after 5 minutes"
        except Exception as e:
            return f"Error: {str(e)}"

    def start_async(self, prompt, cwd="~/Agents"):
        session_id = f"poke-{int(time.time() * 1000)}"
        session = ClaudeSession(session_id, prompt, cwd)
        session.start()
        with self._lock:
            self.sessions[session_id] = session
        return session_id

    def start_parallel(self, prompts, cwd="~/Agents"):
        session_ids = []
        threads = []

        def spawn(prompt):
            sid = self.start_async(prompt, cwd)
            session_ids.append(sid)

        for prompt in prompts:
            t = threading.Thread(target=spawn, args=(prompt,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return session_ids

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def list_all(self):
        with self._lock:
            return list(self.sessions.values())
