"""Convert PDFDebugger coordinates to PCL Coordinates using a dataset"""
import os
import dataclasses
import math
import numpy as np
from sklearn.linear_model import LinearRegression
import click
import pandas as pd
import matplotlib.pyplot as plt


@dataclasses.dataclass
class Coordinates:
    """Standard x-y coordinate"""

    x_coord: int
    y_coord: int


@dataclasses.dataclass
class PdfCoordinates:
    """Coordinate combination for regression analysis"""

    name: str
    pdf_debugger_coordinates: Coordinates
    pcl_coordinates: Coordinates


class CoordinatePredictor:
    """Class that stores the intercepts and coefficients to produce the predicted"""

    def __init__(self, x_coef, y_coef, x_intercept, y_intercept):
        self.x_coef = x_coef
        self.y_coef = y_coef
        self.x_intercept = x_intercept
        self.y_intercept = y_intercept

    def get_predicted_pcl_x(self, pdf_coordinates):
        """Returns predicted x coordinate given the model outputs and PDFDebugger x coordinate"""
        return round(
            self.x_coef * pdf_coordinates.pdf_debugger_coordinates.x_coord
            + self.x_intercept
        )

    def get_predicted_pcl_y(self, pdf_coordinates):
        """Returns predicted y coordinate given the model outputs and PDFDebugger y coordinate"""
        return round(
            self.y_coef * pdf_coordinates.pdf_debugger_coordinates.y_coord
            + self.y_intercept
        )


def add_coord(coord_list, name, pdf_debugger_x, pdf_debugger_y, pcl_x, pcl_y):
    """Add a PDFCoordinate to the given coordinate list"""
    coord_list.append(
        PdfCoordinates(
            name,
            Coordinates(pdf_debugger_x, pdf_debugger_y),
            Coordinates(pcl_x, pcl_y),
        )
    )


def run_regression(x_array, y_array):
    """Train model with x and y arrays from the list of coordinates"""
    numpy_x = np.array(x_array).reshape((-1, 1))
    numpy_y = np.array(y_array)
    model = LinearRegression()
    model.fit(numpy_x, numpy_y)
    return model


@click.command()
@click.option(
    "--input-file-path",
    prompt="Input JSON file path:",
    help="Input JSON file path to train the model. Data points without pcl coordinates will be outputted with them. Script output will be placed in same directory as the data.",
)
@click.option(
    "--file-handle-param",
    help="Parameter name in the coordinate set code.",
    prompt="Parameter name in the coordinate set code.",
)
def convert_pcl_coordinates(input_file_path, file_handle_param):
    """
    Use completed coordinates to train a model that will be used to predict the incomplete
    coordinates.
    """
    ## Pull in JSON data from the input file
    coords_json = pd.read_json(input_file_path)
    ## Build coordinate list
    coord_list = []
    for index in coords_json.index:
        add_coord(
            coord_list,
            coords_json["name"][index],
            coords_json["pdf_debugger_x"][index],
            coords_json["pdf_debugger_y"][index],
            coords_json["pcl_x"][index],
            coords_json["pcl_y"][index],
        )
    ## Get x and y arrays
    # x value handling
    x_x = []
    x_y = []
    for coord in coord_list:
        if not math.isnan(coord.pcl_coordinates.x_coord):
            x_x.append(coord.pdf_debugger_coordinates.x_coord)
            x_y.append(coord.pcl_coordinates.x_coord)
    # y value handling
    y_x = []
    y_y = []
    for coord in coord_list:
        if not math.isnan(coord.pcl_coordinates.y_coord):
            y_x.append(coord.pdf_debugger_coordinates.y_coord)
            y_y.append(coord.pcl_coordinates.y_coord)
    ## Run regressions to get coefficients and intercepts
    x_model = run_regression(x_x, x_y)
    y_model = run_regression(y_x, y_y)
    coordinate_predictor = CoordinatePredictor(
        x_model.coef_[0],
        y_model.coef_[0],
        x_model.intercept_,
        y_model.intercept_,
    )
    ## Build output file
    build_output_file(
        input_file_path, file_handle_param, coord_list, coordinate_predictor
    )
    ## Show plot
    show_plot(
        input_file_path, x_x, x_y, y_x, y_y, x_model, y_model, coordinate_predictor
    )


def build_output_file(
    input_file_path, file_handle_param, coord_list, coordinate_predictor
):
    """Build the C Script coordinate adjustment and print statements for the pcl2pdf utility"""
    output_file_path = os.path.splitext(input_file_path)[0] + ".c"
    if os.path.exists(output_file_path):
        os.remove(output_file_path)
    with open(output_file_path, "w", encoding="utf8") as code_file:
        for coord in coord_list:
            if math.isnan(coord.pcl_coordinates.x_coord) or math.isnan(
                coord.pcl_coordinates.x_coord
            ):
                code_addition = "//" + coord.name + "\n"
                predicted_y = coordinate_predictor.get_predicted_pcl_y(coord)
                code_addition += f'mv_v("{predicted_y}", {file_handle_param});\n'
                predicted_x = coordinate_predictor.get_predicted_pcl_x(coord)
                code_addition += f'mv_h("{predicted_x}", {file_handle_param});\n'
                code_addition += f'fprintf({file_handle_param}, "CHANGE ME!!");\n'
                code_file.write("\n")
                code_file.write(code_addition)


def show_plot(
    input_file_path, x_x, x_y, y_x, y_y, x_model, y_model, coordinate_predictor
):
    """Show a plot of how well the model fits the training data (if the model is bad you might've inputted bad data)"""
    y_plot_file_path = os.path.splitext(input_file_path)[0] + "_y.png"
    plt.scatter(y_x, y_y, color="red")
    plt.plot(
        y_x,
        y_model.predict(np.array(y_x).reshape((-1, 1))),
        color="blue",
        linewidth=3,
    )
    plt.xlabel("PDFDebugger")
    plt.ylabel("PCL2PDF")
    plt.title("PDF Debugger to PCL Y Coordinates Converison")
    # This isn't working, the attempt is to display the model outputs
    plt.text(
        60,
        0.025,
        rf"$\beta_0={coordinate_predictor.y_intercept},\ \beta_1={coordinate_predictor.y_coef}$",
    )
    plt.savefig(y_plot_file_path)
    plt.clf()

    x_plot_file_path = os.path.splitext(input_file_path)[0] + "_x.png"
    plt.scatter(x_x, x_y, color="red")
    plt.plot(
        x_x,
        x_model.predict(np.array(x_x).reshape((-1, 1))),
        color="blue",
        linewidth=3,
    )
    plt.xlabel("PDFDebugger")
    plt.ylabel("PCL2PDF")
    plt.title("PDF Debugger to PCL X Coordinates Converison")
    plt.text(
        60,
        0.025,
        rf"$\beta_0={coordinate_predictor.x_intercept},\ \beta_1={coordinate_predictor.x_coef}$",
    )
    plt.savefig(x_plot_file_path)


if __name__ == "__main__":
    convert_pcl_coordinates()
