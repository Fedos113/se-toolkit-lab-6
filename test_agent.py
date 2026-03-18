import unittest
import subprocess
import json


class TestAgentOutput(unittest.TestCase):
    """Test basic agent output structure."""

    def test_agent_outputs_answer_and_tool_calls(self):
        """Test that agent.py outputs valid JSON with required fields."""
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


class TestAgentToolCalls(unittest.TestCase):
    """Test agent tool calling behavior."""

    def test_merge_conflict_question_uses_read_file(self):
        """
        Test that asking about merge conflicts triggers read_file tool.

        Expected behavior:
        - Agent should call list_files to discover wiki files
        - Agent should call read_file to read git-workflow.md
        - Source should reference wiki/git-workflow.md
        """
        result = subprocess.run(
            ["python", "agent.py", "How do you resolve a merge conflict?"],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Check if process succeeded
        self.assertEqual(
            result.returncode, 0,
            f"agent.py failed with stderr: {result.stderr}"
        )

        # Parse stdout as JSON
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.fail(f"stdout is not valid JSON: {e}\nStdout: {result.stdout}")

        # Check required keys exist
        self.assertIn("answer", output, "Missing 'answer' key in output")
        self.assertIn("source", output, "Missing 'source' key in output")
        self.assertIn("tool_calls", output, "Missing 'tool_calls' key in output")

        # Check that read_file was called
        tool_names = [call.get("tool") for call in output["tool_calls"]]
        self.assertIn(
            "read_file", tool_names,
            f"Expected 'read_file' in tool_calls, got: {tool_names}"
        )

        # Check that source references git-workflow.md
        source = output.get("source", "")
        self.assertIn(
            "git-workflow.md", source.lower(),
            f"Expected 'git-workflow.md' in source, got: {source}"
        )

    def test_wiki_listing_question_uses_list_files(self):
        """
        Test that asking about wiki files triggers list_files tool.

        Expected behavior:
        - Agent should call list_files with path "wiki"
        - tool_calls should contain list_files entry
        """
        result = subprocess.run(
            ["python", "agent.py", "What files are in the wiki?"],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Check if process succeeded
        self.assertEqual(
            result.returncode, 0,
            f"agent.py failed with stderr: {result.stderr}"
        )

        # Parse stdout as JSON
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.fail(f"stdout is not valid JSON: {e}\nStdout: {result.stdout}")

        # Check required keys exist
        self.assertIn("answer", output, "Missing 'answer' key in output")
        self.assertIn("source", output, "Missing 'source' key in output")
        self.assertIn("tool_calls", output, "Missing 'tool_calls' key in output")

        # Check that list_files was called
        tool_names = [call.get("tool") for call in output["tool_calls"]]
        self.assertIn(
            "list_files", tool_names,
            f"Expected 'list_files' in tool_calls, got: {tool_names}"
        )

        # Check that source references wiki
        source = output.get("source", "")
        self.assertIn(
            "wiki", source.lower(),
            f"Expected 'wiki' in source, got: {source}"
        )

    def test_framework_question_uses_read_file(self):
        """
        Test that asking about the backend framework triggers read_file tool.

        Expected behavior:
        - Agent should call read_file to read backend source code (e.g., main.py)
        - Answer should mention FastAPI
        - tool_calls should contain read_file entry
        """
        result = subprocess.run(
            ["python", "agent.py", "What Python web framework does the backend use?"],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Check if process succeeded
        self.assertEqual(
            result.returncode, 0,
            f"agent.py failed with stderr: {result.stderr}"
        )

        # Parse stdout as JSON
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.fail(f"stdout is not valid JSON: {e}\nStdout: {result.stdout}")

        # Check required keys exist
        self.assertIn("answer", output, "Missing 'answer' key in output")
        self.assertIn("source", output, "Missing 'source' key in output")
        self.assertIn("tool_calls", output, "Missing 'tool_calls' key in output")

        # Check that read_file was called
        tool_names = [call.get("tool") for call in output["tool_calls"]]
        self.assertIn(
            "read_file", tool_names,
            f"Expected 'read_file' in tool_calls, got: {tool_names}"
        )

        # Check that answer mentions FastAPI
        answer = output.get("answer", "").lower()
        self.assertIn(
            "fastapi", answer,
            f"Expected 'fastapi' in answer, got: {output.get('answer', '')}"
        )

    def test_database_count_question_uses_query_api(self):
        """
        Test that asking about item count triggers query_api tool.

        Expected behavior:
        - Agent should call query_api to query /items/ endpoint
        - Answer should contain a number > 0
        - tool_calls should contain query_api entry
        """
        result = subprocess.run(
            ["python", "agent.py", "How many items are in the database?"],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Check if process succeeded
        self.assertEqual(
            result.returncode, 0,
            f"agent.py failed with stderr: {result.stderr}"
        )

        # Parse stdout as JSON
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.fail(f"stdout is not valid JSON: {e}\nStdout: {result.stdout}")

        # Check required keys exist
        self.assertIn("answer", output, "Missing 'answer' key in output")
        self.assertIn("source", output, "Missing 'source' key in output")
        self.assertIn("tool_calls", output, "Missing 'tool_calls' key in output")

        # Check that query_api was called
        tool_names = [call.get("tool") for call in output["tool_calls"]]
        self.assertIn(
            "query_api", tool_names,
            f"Expected 'query_api' in tool_calls, got: {tool_names}"
        )

        # Check that answer contains a number > 0
        import re
        answer = output.get("answer", "")
        numbers = re.findall(r"\d+", answer)
        has_positive_number = any(int(n) > 0 for n in numbers)
        self.assertTrue(
            has_positive_number,
            f"Expected a positive number in answer, got: {answer}"
        )


if __name__ == "__main__":
    unittest.main()
