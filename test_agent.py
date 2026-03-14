import unittest
import subprocess
import json

class TestAgentOutput(unittest.TestCase):
    def test_agent_outputs_answer_and_tool_calls(self):
        # Run agent.py as subprocess
        result = subprocess.run(
            ["python", "agent.py"],
            capture_output=True,
            text=True,
            timeout=30  # optional: prevent hanging
        )

        # Check if process succeeded
        self.assertEqual(result.returncode, 0, f"agent.py failed with stderr: {result.stderr}")

        # Parse stdout as JSON
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.fail(f"stdout is not valid JSON: {e}\nStdout: {result.stdout}")

        # Check required keys exist
        self.assertIn("answer", output, "Missing 'answer' key in output")
        self.assertIn("tool_calls", output, "Missing 'tool_calls' key in output")

if __name__ == "__main__":
    unittest.main()
