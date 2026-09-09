import subprocess
import sys

# Run test_modular_domain
result = subprocess.run(
    [sys.executable, "-m", "unittest", "tests.test_modular_domain", "-v"],
    cwd=r"c:\Users\joseh\Downloads\Github\Data_tracer\MSA_gage_handy_tool",
    capture_output=True,
    text=True,
    timeout=300,
)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
print("Return code:", result.returncode)

# Run test_paired_ttest_example
result2 = subprocess.run(
    [sys.executable, "tests/test_paired_ttest_example.py"],
    cwd=r"c:\Users\joseh\Downloads\Github\Data_tracer\MSA_gage_handy_tool",
    capture_output=True,
    text=True,
    timeout=300,
)
print("EXAMPLE STDOUT:")
print(result2.stdout)
print("EXAMPLE STDERR:")
print(result2.stderr)
print("Example Return code:", result2.returncode)

sys.exit(result.returncode or result2.returncode)
