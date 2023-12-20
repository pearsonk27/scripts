"""CLI to search input file for tokens and print lines to output file."""
import os
import click


@click.command()
@click.option(
    "--tokens",
    prompt="Tokens to search for?",
    help="Tokens to search for (comma separated).",
)
@click.option(
    "--input_file", prompt="Input file?", help="Full file path to file to be searched."
)
@click.option(
    "--output_file",
    prompt="Output file?",
    help="Full file path for found lines to be exported to.",
)
@click.option(
    "--remove_tokens",
    help="If this option is used lines without tokens will be exported.",
    default=False,
    is_flag=True,
    show_default=True,
)
def strip_file(tokens, input_file, output_file, remove_tokens):
    """Search input file for tokens and print lines to output file."""
    if not os.path.exists(input_file):
        raise ValueError("input file does not exist")
    if os.path.exists(output_file):
        os.remove(output_file)

    with open(input_file, "r", encoding="utf8") as search_file, open(
        output_file, "w", encoding="utf8"
    ) as output:
        for line in search_file.readlines():
            if any(token in line for token in tokens.split(",")):
                if not remove_tokens:
                    output.write(line)
            else:
                if remove_tokens:
                    output.write(line)


if __name__ == "__main__":
    strip_file()
