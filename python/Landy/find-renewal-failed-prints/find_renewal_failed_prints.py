#!/usr/bin/env python3

import os
import datetime
import re
from pathlib import Path


def find_small_recent_files(directory):
    # Convert target date to timestamp for comparison
    target_date = datetime.datetime(2025, 7, 1).date()

    # Walk through directory and subdirectories
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = Path(root) / file

            try:
                # Get file stats
                stats = file_path.stat()

                # Check file size (10KB = 10 * 1024 bytes)
                if stats.st_size >= 10 * 1024:
                    continue

                # Get file creation time and convert to date
                creation_date = datetime.datetime.fromtimestamp(stats.st_ctime).date()

                # Check if file was created on July 1st, 2025
                if creation_date == target_date:
                    # Search for 7 consecutive digits in filename
                    matches = re.findall(r"\d{7}", file)

                    # Print any found 7-digit numbers
                    if matches:
                        for match in matches:
                            print(f"File: {file_path}")
                            print(f"Found 7-digit number: {match}\n")

            except (OSError, PermissionError) as e:
                print(f"Error accessing {file_path}: {e}")


def check_7digit_numbers_in_scriptlist2(numbers_file, scriptlist2_path):
    """
    numbers_file: path to file with one 7-digit number per line
    scriptlist2_path: path to script_list2 file
    """
    # Read list of 7-digit numbers
    with open(numbers_file, 'r', encoding='utf-8') as f:
        valid_numbers = set(line.strip() for line in f if re.fullmatch(r'\d{7}', line.strip()))

    # Read script_list2
    with open(scriptlist2_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    found_first = False
    for idx, line in enumerate(lines, 1):
        for match in re.findall(r'(?<!\d)(\d{7})(?!\d)', line):
            if not found_first and match in valid_numbers:
                print(f"First instance: {match} found at line {idx}")
                found_first = True
            elif found_first:
                if match not in valid_numbers:
                    print(f"ERROR: 7-digit number {match} at line {idx} not in provided list!")
                else:
                    print(f"Confirmed: {match} at line {idx} is in provided list.")
    if not found_first:
        print("No 7-digit number from the list was found in script_list2.")


def main():
    # Get the directory to search from command line or use current directory
    search_dir = input(
        "Enter directory path to search (or press Enter for current directory): "
    ).strip()
    if not search_dir:
        search_dir = "."

    if not os.path.isdir(search_dir):
        print(f"Error: '{search_dir}' is not a valid directory")
        return

    print(f"\nSearching in: {os.path.abspath(search_dir)}")
    print("Looking for files:")
    print("- Less than 10 KB in size")
    print("- Created on July 1st, 2025")
    print("- Containing 7 consecutive digits in filename\n")

    find_small_recent_files(search_dir)

    # Example usage of check_7digit_numbers_in_scriptlist2
    # This part is just for demonstration and may need to be adapted
    numbers_file = input("Enter path to file with 7-digit numbers: ").strip()
    scriptlist2_path = input("Enter path to script_list2 file: ").strip()
    check_7digit_numbers_in_scriptlist2(numbers_file, scriptlist2_path)


if __name__ == "__main__":
    main()
