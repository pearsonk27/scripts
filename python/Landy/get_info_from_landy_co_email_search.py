"""Extract files and emails to be stripped from application"""

import re
import dataclasses


def read_file():
    """Read the file and print relevant lines."""
    line_regex = re.compile(
        r"^(?P<fullFilePath>(?P<path>[^:]*\/(?P<parentFolder>[^:]*))\/(?P<fileName>[^:]*?)):(?P<text>.*?(?P<email>[a-zA-Z_\\]+@landy\.com).*)$"
    )
    pull_instructions = []
    directories = []
    with open(
        "Y:\\garf\\Kris\\Projects\\OldEmails_20240529\\email_text_search.txt",
        "r",
        encoding="utf8",
    ) as search_file:
        for line in search_file.readlines():
            m = line_regex.search(line)
            if m is None:
                print(line)
            elif (
                m.group("email")
                not in [
                    "landy_insurance@landy.com",
                    "policy_issuer@landy.com",
                    "info@landy.com",
                    "administrator@landy.com",
                ]
                and "safe" not in m.group("path")
                and "BACKUP" not in m.group("path")
            ):
                directory_enum = DirectoryEnum(m.group("parentFolder"), m.group("path"))
                if directory_enum not in directories:
                    directories.append(directory_enum)
                pull_instruction = PullInstructions(m.group("fileName"), directory_enum)
                if pull_instruction not in pull_instructions:
                    pull_instructions.append(pull_instruction)
    print("\nmkdir commands:\n")
    for directory in directories:
        print(directory.get_bash_mkdir())
    print("\npull commands:\n")
    for pull_instruction in pull_instructions:
        print(pull_instruction.get_command())
    print("\nenum instantiations:\n")
    for directory in directories:
        print(directory.get_enum_instantiation())


@dataclasses.dataclass
class DirectoryEnum:
    """Enumeration for java project info"""

    name: str
    directory: str

    def get_directory(self):
        """Return server path"""
        return "/var/www" + self.directory[1:]

    def get_name(self):
        """Return name with all capitalized characters"""
        return self.name.upper().replace("-", "_")

    def get_bash_mkdir(self):
        """Return mkdir command for temp directory"""
        return "mkdir " + self.get_temp_path()

    def get_temp_path(self):
        """Return path to temp directory"""
        return (
            f"/agents/garf/Kris/Projects/OldEmails_20240529/WebFiles/{self.get_name()}"
        )

    def get_enum_instantiation(self):
        """Return java code for enum generation"""
        return f'{self.get_name()}("{self.get_directory()}"),'


@dataclasses.dataclass
class PullInstructions:
    """Data for server pull command"""

    file_name: str
    directory: DirectoryEnum

    def get_command(self):
        """Get the command to pull from the server"""
        path = self.directory.get_directory()
        return f"cp {path}/{self.file_name} {self.directory.get_temp_path()}"


if __name__ == "__main__":
    read_file()
