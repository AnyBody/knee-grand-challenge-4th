import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QFileDialog, QWidget, QInputDialog
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QVector4D, QPainter, QPen
from stl import mesh
import pyqtgraph.opengl as gl
import numpy as np

class VertexExtractor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STL Vertex Extractor")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.load_button = QPushButton("Load STL File")
        self.load_button.clicked.connect(self.load_stl)
        self.layout.addWidget(self.load_button)

        self.start_selection_button = QPushButton("Start Selection")
        self.start_selection_button.clicked.connect(self.start_selection)
        self.layout.addWidget(self.start_selection_button)

        self.stop_selection_button = QPushButton("Stop Selection")
        self.stop_selection_button.clicked.connect(self.stop_selection)
        self.layout.addWidget(self.stop_selection_button)

        self.deselect_button = QPushButton("Deselect All")
        self.deselect_button.clicked.connect(self.deselect_all)
        self.layout.addWidget(self.deselect_button)

        self.view = gl.GLViewWidget()
        self.view.setCameraPosition(distance=50)
        self.layout.addWidget(self.view)

        self.stl_mesh = None
        self.scatter_plot = None
        self.selection_active = False
        self.selected_vertices = []  # List to store selected vertices
        self.selected_scatter_plot = None  # Scatter plot for selected vertices

        self.sphere_center = None
        self.sphere_radius = None
        self.sphere_visualization = None

        self.move_x_button = QPushButton("Move Sphere +X")
        self.move_x_button.clicked.connect(lambda: self.move_sphere(axis=0, step=self.move_step))
        self.layout.addWidget(self.move_x_button)

        self.move_y_button = QPushButton("Move Sphere +Y")
        self.move_y_button.clicked.connect(lambda: self.move_sphere(axis=1, step=self.move_step))
        self.layout.addWidget(self.move_y_button)

        self.move_z_button = QPushButton("Move Sphere +Z")
        self.move_z_button.clicked.connect(lambda: self.move_sphere(axis=2, step=self.move_step))
        self.layout.addWidget(self.move_z_button)

        self.move_x_neg_button = QPushButton("Move Sphere -X")
        self.move_x_neg_button.clicked.connect(lambda: self.move_sphere(axis=0, step=-self.move_step))
        self.layout.addWidget(self.move_x_neg_button)

        self.move_y_neg_button = QPushButton("Move Sphere -Y")
        self.move_y_neg_button.clicked.connect(lambda: self.move_sphere(axis=1, step=-self.move_step))
        self.layout.addWidget(self.move_y_neg_button)

        self.move_z_neg_button = QPushButton("Move Sphere -Z")
        self.move_z_neg_button.clicked.connect(lambda: self.move_sphere(axis=2, step=-self.move_step))
        self.layout.addWidget(self.move_z_neg_button)

        self.step_setting_button = QPushButton("Set Move Step")
        self.step_setting_button.clicked.connect(self.set_move_step)
        self.layout.addWidget(self.step_setting_button)

        self.scale_up_button = QPushButton("Increase Sphere Radius")
        self.scale_up_button.clicked.connect(lambda: self.scale_sphere(factor=1.1))
        self.layout.addWidget(self.scale_up_button)

        self.scale_down_button = QPushButton("Decrease Sphere Radius")
        self.scale_down_button.clicked.connect(lambda: self.scale_sphere(factor=0.9))
        self.layout.addWidget(self.scale_down_button)

        self.display_points_button = QPushButton("Display Selected Points")
        self.display_points_button.clicked.connect(self.display_selected_points)
        self.layout.addWidget(self.display_points_button)

        self.move_step = 1  # Default step size

        # Add axis visualization to the 3D view
        self.add_axes()

    def add_axes(self):
        """Visualize the X, Y, and Z axes in the 3D view."""
        axis_length = 10.0

        # X-axis (red)
        x_axis = np.array([[0, 0, 0], [axis_length, 0, 0]])
        x_axis_item = gl.GLLinePlotItem(pos=x_axis, color=(1, 0, 0, 1), width=2, mode='lines')
        self.view.addItem(x_axis_item)

        # Y-axis (green)
        y_axis = np.array([[0, 0, 0], [0, axis_length, 0]])
        y_axis_item = gl.GLLinePlotItem(pos=y_axis, color=(0, 1, 0, 1), width=2, mode='lines')
        self.view.addItem(y_axis_item)

        # Z-axis (blue)
        z_axis = np.array([[0, 0, 0], [0, 0, axis_length]])
        z_axis_item = gl.GLLinePlotItem(pos=z_axis, color=(0, 0, 1, 1), width=2, mode='lines')
        self.view.addItem(z_axis_item)

    def set_move_step(self):
        step, ok = QInputDialog.getDouble(self, "Set Move Step", "Enter step size:", self.move_step, 0.1, 100.0, 2)
        if ok:
            self.move_step = step
            print(f"Move step set to {self.move_step}")

    def load_stl(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open STL File", "", "STL Files (*.stl)")
        if file_path:
            self.stl_mesh = mesh.Mesh.from_file(file_path)
            self.plot_stl()

    def plot_stl(self):
        if self.stl_mesh:
            points = self.stl_mesh.vectors.reshape(-1, 3)
            if self.scatter_plot:
                self.view.removeItem(self.scatter_plot)
            self.scatter_plot = gl.GLScatterPlotItem(pos=points, color=(0, 0, 1, 1), size=2)
            self.view.addItem(self.scatter_plot)

    def start_selection(self):
        if self.stl_mesh is None:
            print("No STL mesh loaded.")
            return

        bounding_box_min = np.min(self.stl_mesh.vectors.reshape(-1, 3), axis=0)
        bounding_box_max = np.max(self.stl_mesh.vectors.reshape(-1, 3), axis=0)
        bounding_box_size = np.linalg.norm(bounding_box_max - bounding_box_min)

        self.sphere_center = (bounding_box_min + bounding_box_max) / 2
        self.sphere_radius = 0.05 * bounding_box_size

        self.visualize_sphere()
        print("Sphere-based selection started. Use buttons to move or scale the sphere.")

    def stop_selection(self):
        self.selection_active = False
        self.view.mousePressEvent = None
        print("Selection stopped.")

    def visualize_sphere(self):
        if self.sphere_visualization:
            self.view.removeItem(self.sphere_visualization)

        # Create a sphere visualization using a scatter plot approximation
        phi, theta = np.mgrid[0:np.pi:20j, 0:2 * np.pi:20j]
        x = self.sphere_radius * np.sin(phi) * np.cos(theta) + self.sphere_center[0]
        y = self.sphere_radius * np.sin(phi) * np.sin(theta) + self.sphere_center[1]
        z = self.sphere_radius * np.cos(phi) + self.sphere_center[2]

        sphere_points = np.vstack((x.flatten(), y.flatten(), z.flatten())).T
        self.sphere_visualization = gl.GLScatterPlotItem(pos=sphere_points, color=(0, 1, 0, 1), size=2)
        self.view.addItem(self.sphere_visualization)

    def move_sphere(self, axis, step):
        if self.sphere_center is None:
            print("Sphere not initialized.")
            return

        self.sphere_center[axis] += step
        self.visualize_sphere()

    def scale_sphere(self, factor):
        if self.sphere_radius is None:
            print("Sphere not initialized.")
            return

        self.sphere_radius *= factor
        self.visualize_sphere()

    def on_mouse_press_sphere(self, event):
        if not self.selection_active:
            return

        if event.button() == Qt.LeftButton:  # Define the center of the sphere
            # Convert 2D screen coordinates to normalized device coordinates (NDC)
            width, height = self.view.width(), self.view.height()
            x_ndc = (event.pos().x() / width) * 2 - 1
            y_ndc = (1 - (event.pos().y() / height)) * 2 - 1
            z_ndc = 0.0  # Assume the sphere is centered at the middle depth

            # Transform NDC coordinates to 3D world space
            view_matrix = self.view.viewMatrix()
            projection_matrix = self.view.projectionMatrix()
            combined_matrix = np.dot(np.array(projection_matrix.copyDataTo()).reshape(4, 4),
                                      np.array(view_matrix.copyDataTo()).reshape(4, 4))
            inverse_combined_matrix = np.linalg.inv(combined_matrix)

            ndc_point = np.array([x_ndc, y_ndc, z_ndc, 1.0])
            world_point = inverse_combined_matrix @ ndc_point
            sphere_center = world_point[:3] / world_point[3]

            # Define the radius of the sphere (adjust as needed)
            sphere_radius = 5.0

            # Perform sphere-based selection
            self.perform_sphere_selection(sphere_center, sphere_radius)

    def perform_sphere_selection(self, center, radius):
        if self.stl_mesh is None:
            print("No STL mesh loaded.")
            return

        # Get all vertices of the mesh
        points = self.stl_mesh.vectors.reshape(-1, 3)

        # Find vertices within the sphere
        distances = np.linalg.norm(points - center, axis=1)
        selected_points = points[distances <= radius]

        if not len(selected_points):
            print("No vertices selected within the sphere.")
            return

        self.selected_vertices = selected_points.tolist()
        self.update_selected_vertices()
        print(f"Selected {len(selected_points)} vertices within the sphere.")

    def update_selected_vertices(self):
        # Remove the previous scatter plot for selected vertices
        if self.selected_scatter_plot:
            self.view.removeItem(self.selected_scatter_plot)

        # Create a new scatter plot for the selected vertices
        if self.selected_vertices:
            selected_points = np.array(self.selected_vertices)
            self.selected_scatter_plot = gl.GLScatterPlotItem(pos=selected_points, color=(1, 0, 0, 1), size=5)
            self.view.addItem(self.selected_scatter_plot)

    def deselect_all(self):
        """Clear all selected vertices and update the visualization."""
        self.selected_vertices = []
        if self.selected_scatter_plot:
            self.view.removeItem(self.selected_scatter_plot)
            self.selected_scatter_plot = None
        print("Deselected all vertices.")

    def display_selected_points(self):
        if not self.selected_vertices:
            print("No points selected.")
            return

        print("Selected Points:")
        for point in self.selected_vertices:
            print(f"{point}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VertexExtractor()
    window.show()
    sys.exit(app.exec_())