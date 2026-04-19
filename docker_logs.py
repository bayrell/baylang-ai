#!/usr/bin/env python3
"""
Script to filter Docker service logs and remove container ID prefix.
Usage: ./docker_logs.py <container_id> [docker_options]
Example: ./docker_logs.py my_container --tail=100 -f
"""

import sys
import subprocess
import re


def main():
    if len(sys.argv) < 2:
        print("Usage: ./docker_logs.py <container_id> [docker_options]")
        sys.exit(1)

    container_id = sys.argv[1]
    options = sys.argv[2:]
    if not options:
        options = ["--tail=20", "-f"]

    # Build the docker command
    cmd = ["docker", "service", "logs", container_id] + options

    try:
        # Run the command with real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
        )

        # Process each line in real-time
        for line in process.stdout:
            # Remove container ID prefix (format: "id | text")
            # Find the position of the pipe and extract text after it
            arr = line.split(" | ", 2)
            cleaned_line = arr[1] if len(arr) == 2 else arr[0]
            
            # Write to stdout without adding extra newline
            sys.stdout.write(cleaned_line)
            sys.stdout.flush()

        # Wait for process to complete
        process.wait()

    except FileNotFoundError:
        print("Error: docker command not found. Make sure Docker is installed.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()