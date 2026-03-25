"""
Tests that the Python -O/-OO optimization flags are forwarded to SLURM workers.

When a user runs `python -O script.py`, `__debug__` should be False on workers too.
"""

import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

from slurminade.execute_cmds import create_slurminade_command
from slurminade.function_call import FunctionCall


def _make_dummy_entry(tmp_path: Path) -> Path:
    entry = tmp_path / "entry.py"
    entry.write_text("# dummy entry point\n")
    return entry


class TestCreateCommandOptimizeFlag:
    """Unit tests: create_slurminade_command includes -O/-OO when appropriate."""

    def _build_command(self, tmp_path: Path, optimize: int) -> list[str]:
        entry = _make_dummy_entry(tmp_path)
        func = FunctionCall("mod.func", (), {})
        with patch("sys.flags") as mock_flags:
            mock_flags.optimize = optimize
            return create_slurminade_command(entry, [func], max_arg_length=10_000)

    def test_no_flag_when_optimize_0(self, tmp_path):
        cmd = self._build_command(tmp_path, 0)
        # Should NOT contain -O or -OO between executable and -m
        m_index = cmd.index("-m")
        flags_before_m = cmd[1:m_index]
        assert "-O" not in flags_before_m
        assert "-OO" not in flags_before_m

    def test_single_O_when_optimize_1(self, tmp_path):
        cmd = self._build_command(tmp_path, 1)
        assert cmd[0] == sys.executable
        m_index = cmd.index("-m")
        assert "-O" in cmd[1:m_index]

    def test_double_O_when_optimize_2(self, tmp_path):
        cmd = self._build_command(tmp_path, 2)
        assert cmd[0] == sys.executable
        m_index = cmd.index("-m")
        assert "-OO" in cmd[1:m_index]


class TestOptimizeFlagIntegration:
    """Integration test: a subprocess dispatcher honours the -O flag end-to-end."""

    def test_debug_is_false_with_optimize(self, tmp_path):
        """Launch a helper script with -O and verify __debug__ is False on the worker."""
        result_file = tmp_path / "debug_result.txt"
        script = tmp_path / "opt_test_script.py"
        script.write_text(
            textwrap.dedent(f"""\
            import slurminade
            from pathlib import Path

            RESULT = Path({str(result_file)!r})

            @slurminade.slurmify()
            def write_debug():
                RESULT.write_text(str(__debug__))

            if __name__ == "__main__":
                slurminade.set_entry_point(__file__)
                slurminade.set_dispatcher(slurminade.SubprocessDispatcher())
                slurminade.set_dispatch_limit(100)
                write_debug.distribute()
            """)
        )

        # Run the script with -O so __debug__ is False on the caller side
        proc = subprocess.run(
            [sys.executable, "-O", str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert proc.returncode == 0, f"Script failed:\n{proc.stderr}"
        assert result_file.exists(), "Worker did not write result file"
        assert result_file.read_text() == "False"
