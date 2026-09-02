import numpy as np
import vtk
import traceback

def load_stl_mesh(file_path):
    """Load STL mesh using VTK and return the polydata"""
    reader = vtk.vtkSTLReader()
    reader.SetFileName(file_path)
    reader.Update()
    return reader.GetOutput()

def find_closest_vertices(mesh, points):
    """
    For each point in points, find the index of the closest vertex in the mesh using VTK.
    Returns a list of vertex indices.
    """
    # Build a point locator for efficient nearest-neighbor search
    locator = vtk.vtkPointLocator()
    locator.SetDataSet(mesh)
    locator.BuildLocator()
    
    indices = []
    for point in points:
        # Find closest point (vertex) in the mesh
        closest_id = locator.FindClosestPoint(point)
        
        # Calculate distance for debugging
        closest_pt = mesh.GetPoint(closest_id)
        distance = np.linalg.norm(np.array(point) - np.array(closest_pt))
        print(distance, closest_id)
        
        indices.append(closest_id)
    return indices

def find_closest_points_on_surface(mesh, points):
    """
    Find closest points on the mesh surface (not just vertices) using VTK cell locator.
    Returns an array of closest surface points.
    """
    # Build a cell locator for finding closest points on surface
    cell_locator = vtk.vtkCellLocator()
    cell_locator.SetDataSet(mesh)
    cell_locator.BuildLocator()
    
    closest_points = []
    for point in points:
        closest_point = [0.0, 0.0, 0.0]
        cell_id = vtk.mutable(0)
        sub_id = vtk.mutable(0)
        dist2 = vtk.mutable(0.0)
        
        cell_locator.FindClosestPoint(point, closest_point, cell_id, sub_id, dist2)
        closest_points.append(closest_point)
    
    return np.array(closest_points)

def get_points_from_stl(file_path):
    """Load STL mesh and return its points as numpy array"""
    reader = vtk.vtkSTLReader()
    reader.SetFileName(file_path)
    reader.Update()
    polydata = reader.GetOutput()
    
    num_points = polydata.GetNumberOfPoints()
    points = np.zeros((num_points, 3))
    for i in range(num_points):
        points[i] = polydata.GetPoint(i)
    
    return points

def visualize_vtk(mesh_path, points, matched_indices, closest_surface_points=None):
    # Load mesh
    reader = vtk.vtkSTLReader()
    reader.SetFileName(mesh_path)
    reader.Update()
    mesh = reader.GetOutput()

    # Create mesh actor
    mesh_mapper = vtk.vtkPolyDataMapper()
    mesh_mapper.SetInputData(mesh)
    mesh_actor = vtk.vtkActor()
    mesh_actor.SetMapper(mesh_mapper)
    mesh_actor.GetProperty().SetColor(0.7, 0.7, 0.7)
    mesh_actor.GetProperty().SetOpacity(0.3)

    # Original points (red) - using vertices only
    points_vtk = vtk.vtkPoints()
    for pt in points:
        points_vtk.InsertNextPoint(pt)
    
    vertices = vtk.vtkCellArray()
    for i in range(len(points)):
        vertices.InsertNextCell(1)
        vertices.InsertCellPoint(i)
    
    pc_poly = vtk.vtkPolyData()
    pc_poly.SetPoints(points_vtk)
    pc_poly.SetVerts(vertices)
    
    pc_mapper = vtk.vtkPolyDataMapper()
    pc_mapper.SetInputData(pc_poly)
    pc_actor = vtk.vtkActor()
    pc_actor.SetMapper(pc_mapper)
    pc_actor.GetProperty().SetColor(1, 0, 0)
    pc_actor.GetProperty().SetPointSize(8)

    # Matched mesh vertices (green) - using vertices only
    matched_points_vtk = vtk.vtkPoints()
    for idx in matched_indices:
        matched_points_vtk.InsertNextPoint(mesh.GetPoint(idx))
    
    matched_vertices = vtk.vtkCellArray()
    for i in range(len(matched_indices)):
        matched_vertices.InsertNextCell(1)
        matched_vertices.InsertCellPoint(i)
    
    matched_poly = vtk.vtkPolyData()
    matched_poly.SetPoints(matched_points_vtk)
    matched_poly.SetVerts(matched_vertices)
    
    matched_mapper = vtk.vtkPolyDataMapper()
    matched_mapper.SetInputData(matched_poly)
    matched_actor = vtk.vtkActor()
    matched_actor.SetMapper(matched_mapper)
    matched_actor.GetProperty().SetColor(0, 1, 0)
    matched_actor.GetProperty().SetPointSize(8)

    # Closest surface points (blue) - using vertices only
    surface_actor = None
    if closest_surface_points is not None:
        surface_points_vtk = vtk.vtkPoints()
        for pt in closest_surface_points:
            surface_points_vtk.InsertNextPoint(pt)
        
        surface_vertices = vtk.vtkCellArray()
        for i in range(len(closest_surface_points)):
            surface_vertices.InsertNextCell(1)
            surface_vertices.InsertCellPoint(i)
        
        surface_poly = vtk.vtkPolyData()
        surface_poly.SetPoints(surface_points_vtk)
        surface_poly.SetVerts(surface_vertices)
        
        surface_mapper = vtk.vtkPolyDataMapper()
        surface_mapper.SetInputData(surface_poly)
        surface_actor = vtk.vtkActor()
        surface_actor.SetMapper(surface_mapper)
        surface_actor.GetProperty().SetColor(0, 0, 1)
        surface_actor.GetProperty().SetPointSize(8)

    # Renderer
    renderer = vtk.vtkRenderer()
    renderer.AddActor(mesh_actor)
    renderer.AddActor(pc_actor)
    renderer.AddActor(matched_actor)

    if surface_actor:
        renderer.AddActor(surface_actor)
    renderer.SetBackground(1, 1, 1)

    # Render window
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window.SetSize(1000, 800)

    # Interactor
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)
    render_window.Render()
    interactor.Start()

# === Main Usage ===
# Input STL files
#points_stl_path = 'FemoralHead.stl'
#points_stl_path = 'FemoralComponentCylFitPoints.stl'
#points_stl_path = 'FemoralComponentPatellaJointPoints.stl'
points_stl_path = 'femur_anyknee_1.stl'
#points_stl_path = 'Patella_PatellarLigamentPoints.stl'

mesh_stl_path = 'femur.stl'  # The mesh to find points on

# Read files
points = get_points_from_stl(points_stl_path)
print(f"Loaded {len(points)} points from {points_stl_path}. Sample: {points[:3]}")
mesh = load_stl_mesh(mesh_stl_path)
num_vertices = mesh.GetNumberOfPoints()
print(f"Loaded mesh with {num_vertices} vertices from {mesh_stl_path}.")

print(points)
# Find closest vertices
closest_indices = find_closest_vertices(mesh, points)

# Find closest points on mesh surface
closest_surface_points = find_closest_points_on_surface(mesh, points)

# Process to get unique indices
unique_indices = sorted(set(closest_indices))
print(f"Number of unique indices: {len(unique_indices)}. Sample: {unique_indices[:10]}")

# Save unique indices as AnyScript array in a .any file named after the points STL file
any_filename = points_stl_path.rsplit('.', 1)[0] + '.any'
with open(any_filename, 'w') as f:
    f.write('AnyInt indices = {')
    f.write(', '.join(str(idx) for idx in unique_indices))
    f.write('};\n')
print(f"Unique indices saved as AnyScript array to {any_filename}")

# Show coordinates of first 3 matched mesh vertices
if len(closest_indices) > 0:
    matched_coords = [mesh.GetPoint(idx) for idx in closest_indices[:3]]
    print(f"Coordinates of first 3 matched mesh vertices: {matched_coords}")

# Visualize
visualize_vtk(mesh_stl_path, points, closest_indices, closest_surface_points)

input("Press Enter to exit...")

# Optional: Print out the indices
print("Closest vertex indices on STL mesh:", closest_indices)
