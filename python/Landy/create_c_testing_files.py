"""CLI to create test files for Landy C Project."""
import os
import click


@click.command()
@click.option(
    "--testing_directory",
    prompt="Testing Directory?",
    help="Directory to place the testing files in.",
)
@click.option(
    "--test_name", prompt="Test Name?", help="Test name used for files."
)
def build_test_files(testing_directory, test_name):
    """Create test files for Landy C Project."""
    if not os.path.exists(testing_directory):
        os.mkdir(testing_directory)
    c_file_path = os.path.join(testing_directory, test_name + ".c")
    with open(c_file_path, 'w', encoding="utf8") as c_file:
        c_file.write(f"""#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <locale.h>
#include "/opt/conetic5/cbase/include/cbase/dtypes.h"
#include "/opt/conetic5/cbase/include/cbase/dirio.h"
#include "/usr2/inter/src/include/utility.h"

int main(int argc, char *argv[])
{{
      printf("Running {test_name}...\\n");
}}""")

    mk_file_path = os.path.join(testing_directory, test_name + ".mk")
    with open(mk_file_path, 'w', encoding="utf8") as mk_file:
        mk_file.write(f"""
CC=/usr/bin/gcc
CHOME=/opt/conetic5/cbase
INC=-I$(CHOME)/include
CFLAGS=-O -I$(CHOME)/include 
LFLAGS=-L$(CHOME)/lib -lscreen -lcbase -llic -lm
TFLAGS=/lib/libtermcap.so.2
LLFLAGS=-L/usr3/inter/src/lib -lhp -lutility

objects = {test_name}.o

{test_name}: $(objects)
	$(CC) $(objects) $(LFLAGS) $(LLFLAGS) $(TFLAGS) -o {test_name}
	cssbuild {test_name}
	touch $@

.o:
	$(CC) $(CFLAGS) $<

clean:
	rm *.o
""")
    sh_file_path = os.path.join(testing_directory, test_name + ".sh")
    with open(sh_file_path, 'w', encoding="utf8") as sh_file:
        sh_file.write(f"""#! /bin/sh

make -f {test_name}.mk
chmod 777 {test_name}
./{test_name}
""")


if __name__ == "__main__":
    build_test_files()
