import numpy as np
import open3d as o3d
import trimesh
from scipy.spatial import KDTree
import traceback
import vtk

def read_xyz(file_path):
    # Assumes XYZ file has no header and 3 columns: X Y Z
    return np.loadtxt(file_path)

def load_stl_mesh(file_path):
    return trimesh.load(file_path)

def find_closest_vertices(mesh, points):
    """
    For each point in points, find the index of the closest vertex in the mesh.
    Returns a list of vertex indices.
    """
    kdtree = KDTree(mesh.vertices)
    indices = []
    for point in points:
        distance, index = kdtree.query(point)
        print(distance, index)
        indices.append(index)
    return indices

def find_closest_points_on_surface(mesh, points):
    # Use trimesh.proximity.closest_point to get closest points on the mesh surface
    closest_points, _, triangle_id = mesh.nearest.on_surface(points)
    return closest_points

def visualize(mesh_path, points, matched_indices, closest_surface_points=None):
    print(f"[DEBUG] mesh_path: {mesh_path}")
    print(f"[DEBUG] points type: {type(points)}, shape: {getattr(points, 'shape', None)}, dtype: {getattr(points, 'dtype', None)}")
    print(f"[DEBUG] matched_indices (len={len(matched_indices)}): {matched_indices[:10]}")
    mesh_o3d = o3d.io.read_triangle_mesh(mesh_path)
    print(f"[DEBUG] mesh_o3d has {len(mesh_o3d.vertices)} vertices and {len(mesh_o3d.triangles)} triangles")
    mesh_o3d.compute_vertex_normals()

    # Visualize the original XYZ points
    try:
        print(f"[DEBUG] About to create point cloud for original points")
        # Ensure points is a numpy array of shape (N, 3) and dtype float64
        points_arr = np.asarray(points, dtype=np.float64)
        print(f"[DEBUG] points_arr shape: {points_arr.shape}, dtype: {points_arr.dtype}")
        if points_arr.ndim != 2 or points_arr.shape[1] != 3:
            raise ValueError(f"Points array must be of shape (N, 3), got {points_arr.shape}")
        print(f"[DEBUG] Before creating PointCloud object")
        pc = o3d.geometry.PointCloud()
        print(f"[DEBUG] Before assigning points to PointCloud")
        pc.points = o3d.utility.Vector3dVector(points_arr)
        print(f"[DEBUG] PointCloud has {len(pc.points)} points")
        print(f"[DEBUG] First 5 points: {points_arr[:5]}")
        if np.isnan(points_arr).any() or np.isinf(points_arr).any():
            print("[ERROR] points_arr contains NaN or Inf values!")
            return
        print(f"[DEBUG] No NaN or Inf in points_arr")
        if len(pc.points) == 0:
            print("[ERROR] PointCloud is empty, skipping paint_uniform_color.")
        else:
            print(f"[DEBUG] Before painting PointCloud")
            pc.paint_uniform_color([1, 0, 0])  # Red for XYZ points
            print(f"[DEBUG] Created point cloud for original points")
    except Exception as e:
        print(f"[ERROR] Failed to create point cloud for original points: {e}")
        traceback.print_exc()
        return

    # Visualize matched vertices on the mesh (now using unique indices)
    vertices = np.asarray(mesh_o3d.vertices)
    print(f"[DEBUG] vertices shape: {vertices.shape}")
    try:
        matched_points = vertices[matched_indices]
        print(f"[DEBUG] matched_points shape: {matched_points.shape}")
    except Exception as e:
        print(f"[ERROR] Failed to index matched points: {e}")
        return

    try:
        matched_pc = o3d.geometry.PointCloud()
        matched_pc.points = o3d.utility.Vector3dVector(matched_points)
        matched_pc.paint_uniform_color([0, 1, 0])  # Green for unique mesh vertices
        print(f"[DEBUG] Created point cloud for matched points")
    except Exception as e:
        print(f"[ERROR] Failed to create point cloud for matched points: {e}")
        return

    try:
        # Create lines between each original point and its matched mesh vertex
        lines = []
        line_points = []
        for i in range(len(points_arr)):
            line_points.append(points_arr[i])
            line_points.append(matched_points[i])
            lines.append([2*i, 2*i+1])
        line_points = np.array(line_points)
        line_set = o3d.geometry.LineSet()
        line_set.points = o3d.utility.Vector3dVector(line_points)
        line_set.lines = o3d.utility.Vector2iVector(lines)
        line_set.colors = o3d.utility.Vector3dVector([[0,0,1]] * len(lines))  # Blue lines
        print(f"[DEBUG] Created {len(lines)} lines between points and matched mesh vertices")
    except Exception as e:
        print(f"[ERROR] Failed to create lines: {e}")
        traceback.print_exc()
        line_set = None

    try:
        if closest_surface_points is not None:
            surface_pc = o3d.geometry.PointCloud()
            surface_pc.points = o3d.utility.Vector3dVector(closest_surface_points)
            surface_pc.paint_uniform_color([0, 0, 1])  # Blue for closest surface points
            print(f"[DEBUG] Created point cloud for closest surface points")
    except Exception as e:
        print(f"[ERROR] Failed to create point cloud for closest surface points: {e}")
        traceback.print_exc()
        surface_pc = None
    print("[DEBUG] Launching Open3D visualization window...")
    geometries = [mesh_o3d, pc, matched_pc]
    if line_set is not None:
        geometries.append(line_set)
    if closest_surface_points is not None and surface_pc is not None:
        geometries.append(surface_pc)
    o3d.visualization.draw_geometries(geometries)
    print("[DEBUG] Visualization window closed.")

def mirror_points_xy(points):
    mirrored = np.copy(points)
    mirrored[:, 2] *= -1
    return mirrored

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

    # Original points (red)
    points_vtk = vtk.vtkPoints()
    for pt in points:
        points_vtk.InsertNextPoint(pt)
    pc_poly = vtk.vtkPolyData()
    pc_poly.SetPoints(points_vtk)
    pc_glyph = vtk.vtkVertexGlyphFilter()
    pc_glyph.SetInputData(pc_poly)
    pc_glyph.Update()
    pc_mapper = vtk.vtkPolyDataMapper()
    pc_mapper.SetInputData(pc_glyph.GetOutput())
    pc_actor = vtk.vtkActor()
    pc_actor.SetMapper(pc_mapper)
    pc_actor.GetProperty().SetColor(1, 0, 0)
    pc_actor.GetProperty().SetPointSize(6)

    # Matched mesh vertices (green)
    matched_points_vtk = vtk.vtkPoints()
    for idx in matched_indices:
        matched_points_vtk.InsertNextPoint(mesh.GetPoint(idx))
    matched_poly = vtk.vtkPolyData()
    matched_poly.SetPoints(matched_points_vtk)
    matched_glyph = vtk.vtkVertexGlyphFilter()
    matched_glyph.SetInputData(matched_poly)
    matched_glyph.Update()
    matched_mapper = vtk.vtkPolyDataMapper()
    matched_mapper.SetInputData(matched_glyph.GetOutput())
    matched_actor = vtk.vtkActor()
    matched_actor.SetMapper(matched_mapper)
    matched_actor.GetProperty().SetColor(0, 1, 0)
    matched_actor.GetProperty().SetPointSize(6)

    # Closest surface points (blue)
    surface_actor = None
    if closest_surface_points is not None:
        surface_points_vtk = vtk.vtkPoints()
        for pt in closest_surface_points:
            surface_points_vtk.InsertNextPoint(pt)
        surface_poly = vtk.vtkPolyData()
        surface_poly.SetPoints(surface_points_vtk)
        surface_glyph = vtk.vtkVertexGlyphFilter()
        surface_glyph.SetInputData(surface_poly)
        surface_glyph.Update()
        surface_mapper = vtk.vtkPolyDataMapper()
        surface_mapper.SetInputData(surface_glyph.GetOutput())
        surface_actor = vtk.vtkActor()
        surface_actor.SetMapper(surface_mapper)
        surface_actor.GetProperty().SetColor(0, 0, 1)
        surface_actor.GetProperty().SetPointSize(6)

    # Lines between original and matched points (cyan)
    lines = vtk.vtkCellArray()
    line_points = vtk.vtkPoints()
    for i, idx in enumerate(matched_indices):
        p1 = points[i]
        p2 = mesh.GetPoint(idx)
        id1 = line_points.InsertNextPoint(p1)
        id2 = line_points.InsertNextPoint(p2)
        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, id1)
        line.GetPointIds().SetId(1, id2)
        lines.InsertNextCell(line)
    line_poly = vtk.vtkPolyData()
    line_poly.SetPoints(line_points)
    line_poly.SetLines(lines)
    line_mapper = vtk.vtkPolyDataMapper()
    line_mapper.SetInputData(line_poly)
    line_actor = vtk.vtkActor()
    line_actor.SetMapper(line_mapper)
    line_actor.GetProperty().SetColor(0, 1, 1)
    line_actor.GetProperty().SetLineWidth(1)

    # Renderer
    renderer = vtk.vtkRenderer()
    renderer.AddActor(mesh_actor)
    renderer.AddActor(pc_actor)
    renderer.AddActor(matched_actor)
    renderer.AddActor(line_actor)
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
#xyz_path = 'FemoralHead.xyz'  # Replace with your XYZ file path
#xyz_path = 'FemoralComponentCylFitPoints.xyz'
#xyz_path = 'femur_R_medial_condyle.stl'
xyz_path = 'femur_R_lateral_condyle.stl'
#femur_R_medial_condyle.stl femur_L.stl
#xyz_path = 'Patella_PatellarLigamentPoints.xyz'
#FemoralComponentCylFitPoints.xyz FemoralComponentPatellaJointPoints.xyz FemoralHead.xyz Patella_PatellarLigamentPoints.xyz 
stl_path = 'femur_R.stl'    # Replace with your STL file path

# Read files
points_stl = load_stl_mesh(xyz_path)
points = np.array(points_stl.vertices)#read_xyz(xyz_path)
#points = mirror_points_xy(points)
print(f"Loaded and mirrored {len(points)} points from {xyz_path}. Sample: {points[:3]}")
mesh = load_stl_mesh(stl_path)
print(f"Loaded mesh with {len(mesh.vertices)} vertices from {stl_path}.")

# Find closest vertices
closest_indices = find_closest_vertices(mesh, points)

# Find closest points on mesh surface
closest_surface_points = find_closest_points_on_surface(mesh, points)

# Process to get unique indices
unique_indices = sorted(set(closest_indices))
print(f"Number of unique indices: {len(unique_indices)}. Sample: {unique_indices[:10]}")

# Save unique indices as AnyScript array in a .any file named after the XYZ file
any_filename = xyz_path.rsplit('.', 1)[0] + '.any'
with open(any_filename, 'w') as f:
    f.write('AnyInt indices = {')
    f.write(', '.join(str(idx) for idx in unique_indices))
    f.write('};\n')
print(f"Unique indices saved as AnyScript array to {any_filename}")

# Show coordinates of first 3 matched mesh vertices
if len(closest_indices) > 0:
    matched_coords = mesh.vertices[closest_indices[:3]]
    print(f"Coordinates of first 3 matched mesh vertices: {matched_coords}")

# Visualize
visualize_vtk(stl_path, points, closest_indices, closest_surface_points)

input("Press Enter to exit...")

# Optional: Print out the indices
print("Closest vertex indices on STL mesh:", closest_indices)
