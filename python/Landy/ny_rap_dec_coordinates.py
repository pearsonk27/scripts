"""Build the code for the NY RAP dec print"""
import os
import numpy as np
from sklearn.linear_model import LinearRegression

x_coef = 0
y_coef = 0
x_intercept = 0
y_intercept = 0


class PdfCoordinate:
    def __init__(
        self,
        name,
        old_pdf_debugger_x,
        old_pdf_debugger_y,
        old_pcl_x,
        old_pcl_y,
        new_pdf_debugger_x,
        new_pdf_debugger_y,
    ):
        self.name = name
        self.old_pdf_debugger_x = old_pdf_debugger_x
        self.old_pdf_debugger_y = old_pdf_debugger_y
        self.old_pcl_x = old_pcl_x
        self.old_pcl_y = old_pcl_y
        self.new_pdf_debugger_x = new_pdf_debugger_x
        self.new_pdf_debugger_y = new_pdf_debugger_y

    def get_pcl_x(self):
        return round(x_coef * self.new_pdf_debugger_x + x_intercept)

    def get_pcl_y(self):
        return round(y_coef * self.new_pdf_debugger_y + y_intercept)


CODE_FILE_PATH = (
    "Y:\\garf\\Kris\\Projects\\NYMissingSignature_20230626\\NYRAPDecCoordinates.txt"
)
coord_list = []


def add_coord(
    name,
    old_pdf_debugger_x,
    old_pdf_debugger_y,
    old_pcl_x,
    old_pcl_y,
    new_pdf_debugger_x,
    new_pdf_debugger_y,
):
    coord_list.append(
        PdfCoordinate(
            name,
            old_pdf_debugger_x,
            old_pdf_debugger_y,
            old_pcl_x,
            old_pcl_y,
            new_pdf_debugger_x,
            new_pdf_debugger_y,
        )
    )


add_coord("Policy Number", 182, 317, 1650, 4410, 189, 295)
add_coord("Renewal Of", 447, 317, 4300, 4410, 467, 295)
add_coord("Limits of Liability - Each Claim", 149, 101, 1300, 6565, 154, 64)
add_coord("Limits of Liability - Each Claim", 149, 79, 1300, 6770, 154, 43)

if os.path.exists(CODE_FILE_PATH):
    os.remove(CODE_FILE_PATH)

def run_regression(x_array, y_array):
    numpy_x = np.array(x_array).reshape((-1, 1))
    numpy_y = np.array(y_array)

    model = LinearRegression()

    model.fit(numpy_x, numpy_y)

    return model

# x value handling
x_x = []
x_y = []

for coord in coord_list:
    x_x.append(coord.old_pdf_debugger_x)
    x_y.append(coord.old_pcl_x)

x_model = run_regression(x_x, x_y)

x_coef = x_model.coef_[0]
x_intercept = x_model.intercept_

# y value handling
y_x = []
y_y = []

for coord in coord_list:
    y_x.append(coord.old_pdf_debugger_y)
    y_y.append(coord.old_pcl_y)

y_model = run_regression(y_x, y_y)

y_coef = y_model.coef_[0]
y_intercept = y_model.intercept_

with open(CODE_FILE_PATH, "w", encoding="utf8") as code_file:
    for coord in coord_list:
        code_addition = "//" + coord.name + "\n"
        code_addition += f'mv_v("{coord.get_pcl_y()}", fpq);\n'
        code_addition += f'mv_h("{coord.get_pcl_x()}", fpq);\n'
        code_addition += 'fprintf(fpq, "CHANGE ME!!");\n'
        code_file.write("\n")
        code_file.write(code_addition)

convert_x_x = []
convert_x_y = []

for coord in coord_list:
    convert_x_x.append(coord.old_pcl_x)
    convert_x_y.append(coord.get_pcl_x())

convert_x_model = run_regression(convert_x_x, convert_x_y)

convert_y_x = []
convert_y_y = []

for coord in coord_list:
    convert_y_x.append(coord.old_pcl_y)
    convert_y_y.append(coord.get_pcl_y())

convert_y_model = run_regression(convert_y_x, convert_y_y)

print("Conversion factors (old pcl coords to new): ")
print(f'X coeffitient: {convert_x_model.coef_[0]}, X intercept: {convert_x_model.intercept_}')
print(f'Y coeffitient: {convert_y_model.coef_[0]}, Y intercept: {convert_y_model.intercept_}')
