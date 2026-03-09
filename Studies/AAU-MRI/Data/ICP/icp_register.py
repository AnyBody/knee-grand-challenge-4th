import numpy as np
try:
    import vtk
except Exception:
    vtk = None
import os
import argparse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

def load_csv_points(path):
    # try to detect header
    with open(path, 'r') as f:
        first = f.readline()
    header = any(c.isalpha() for c in first)
    if header:
        data = np.genfromtxt(path, delimiter=',', skip_header=1)
    else:
        data = np.genfromtxt(path, delimiter=',')
    if data.ndim == 1:
        data = data.reshape(1, -1)
    # extract points (last 3 columns if more than 3 present)
    if data.shape[1] >= 3:
        if data.shape[1] > 3:
            pts = data[:, -3:]
        else:
            pts = data[:, :3]
    else:
        raise ValueError('CSV must contain at least 3 columns for x,y,z')

    # try to detect an index column in the first column if present
    if data.shape[1] > 3:
        col0 = data[:, 0]
        # treat as indices if integer-like and unique
        try:
            col0_finite = np.isfinite(col0)
            if col0_finite.all():
                if np.all(np.abs(col0 - np.round(col0)) < 1e-6) and np.unique(col0).size == col0.size:
                    idxs = col0.astype(int)
                else:
                    idxs = np.arange(pts.shape[0], dtype=int)
            else:
                idxs = np.arange(pts.shape[0], dtype=int)
        except Exception:
            idxs = np.arange(pts.shape[0], dtype=int)
    else:
        idxs = np.arange(pts.shape[0], dtype=int)

    return pts, idxs


def build_kdtree(points):
    try:
        from scipy.spatial import cKDTree as KDTree
        return KDTree(points), 'scipy'
    except Exception:
        # fallback to VTK locator wrapper
        pts = vtk.vtkPoints()
        for p in points:
            pts.InsertNextPoint(p[0], p[1], p[2])
        poly = vtk.vtkPolyData()
        poly.SetPoints(pts)
        locator = vtk.vtkPointLocator()
        locator.SetDataSet(poly)
        locator.BuildLocator()
        return locator, 'vtk'


def load_stl_vertices(path):
    reader = vtk.vtkSTLReader()
    reader.SetFileName(path)
    reader.Update()
    poly = reader.GetOutput()
    pts = poly.GetPoints()
    n = pts.GetNumberOfPoints()
    arr = np.zeros((n, 3), dtype=float)
    for i in range(n):
        arr[i, :] = pts.GetPoint(i)
    return arr


def map_points_to_stl_indices(points, stl_points):
    """Map arbitrary points to nearest STL vertex indices."""
    try:
        from scipy.spatial import cKDTree
        tree = cKDTree(stl_points)
        d, idx = tree.query(points)
        return idx
    except Exception:
        # vtk locator fallback
        pts = vtk.vtkPoints()
        for p in stl_points:
            pts.InsertNextPoint(float(p[0]), float(p[1]), float(p[2]))
        poly = vtk.vtkPolyData()
        poly.SetPoints(pts)
        locator = vtk.vtkPointLocator()
        locator.SetDataSet(poly)
        locator.BuildLocator()
        ids = []
        for p in points:
            ids.append(locator.FindClosestPoint(p))
        return np.array(ids, dtype=int)


def query_nn(tree, mode, points):
    if mode == 'scipy':
        dists, idx = tree.query(points)
        return idx
    else:
        idxs = []
        for p in points:
            idxs.append(tree.FindClosestPoint(p))
        return np.array(idxs, dtype=int)


def icp_point_to_point(A, B, max_iters=50, tol=1e-6):
    # A: fixed (Nx3), B: moving (Mx3)
    src = B.copy()
    prev_error = None
    tree, mode = build_kdtree(A)
    transform_total_R = np.eye(3)
    transform_total_t = np.zeros(3)
    for i in range(max_iters):
        idx = query_nn(tree, mode, src)
        closest = A[idx]
        # compute centroids
        centroid_src = src.mean(axis=0)
        centroid_dst = closest.mean(axis=0)
        # centered
        X = src - centroid_src
        Y = closest - centroid_dst
        # SVD
        H = X.T @ Y
        U, S, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T
        t = centroid_dst - R @ centroid_src
        # apply
        src = (R @ src.T).T + t
        # accumulate
        transform_total_R = R @ transform_total_R
        transform_total_t = R @ transform_total_t + t
        # error
        error = np.mean(np.linalg.norm(src - closest, axis=1))
        if prev_error is not None and abs(prev_error - error) < tol:
            break
        prev_error = error
    return transform_total_R, transform_total_t, src


def estimate_r_t_from_correspondences(A_dst, B_src):
    """Estimate rotation R and translation t that maps points B_src -> A_dst.

    Returns (R, t) such that A_dst ~= R @ B_src + t
    """
    centroid_src = B_src.mean(axis=0)
    centroid_dst = A_dst.mean(axis=0)
    X = B_src - centroid_src
    Y = A_dst - centroid_dst
    H = X.T @ Y
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T
    t = centroid_dst - R @ centroid_src
    return R, t


def compute_offset_and_inverses(R, t, centroid_tibia, femur_centroid, normal_tibia, offset_m):
    """Compute offset vector, updated translation and inverse transforms.

    R, t : ICP rotation and translation mapping tibia->femur (x_f = R x_t + t)
    centroid_tibia : centroid of tibia points in tibia frame
    femur_centroid : centroid of femur points in femur frame
    normal_tibia : plateau normal in tibia frame (unit length)
    offset_m : desired offset magnitude (same units as points)

    Returns: offset_vec (in femur frame), t_offset, inv_R, inv_t, inv_t_offset, tibia_centroid_trans, normal_rot
    """
    # rotate normal into femur frame
    normal_rot = R @ normal_tibia
    normal_rot = normal_rot / np.linalg.norm(normal_rot)

    # transform tibia centroid into femur frame
    tibia_centroid_trans = R @ centroid_tibia + t

    # ensure normal points towards the femur centroid
    dir_to_femur = femur_centroid - tibia_centroid_trans
    if np.dot(normal_rot, dir_to_femur) < 0:
        normal_rot = -normal_rot

    # compute offset vector in femur frame
    offset_vec = normal_rot * offset_m

    # check that applying offset to the tibia centroid increases distance from femur centroid
    dist_before = np.linalg.norm(femur_centroid - tibia_centroid_trans)
    dist_after = np.linalg.norm(femur_centroid - (tibia_centroid_trans + offset_vec))
    if dist_after < dist_before:
        offset_vec = -offset_vec
        dist_after = np.linalg.norm(femur_centroid - (tibia_centroid_trans + offset_vec))

    t_offset = t + offset_vec

    # inverse transforms (femur -> tibia)
    inv_R = R.T
    inv_t = -inv_R @ t
    inv_t_offset = -inv_R @ t_offset

    return offset_vec, t_offset, inv_R, inv_t, inv_t_offset, tibia_centroid_trans, normal_rot


def apply_transform_to_actor(actor, R, t):
    mat = vtk.vtkMatrix4x4()
    # set rotation and translation
    for r in range(3):
        for c in range(3):
            mat.SetElement(r, c, float(R[r, c]))
    mat.SetElement(0, 3, float(t[0]))
    mat.SetElement(1, 3, float(t[1]))
    mat.SetElement(2, 3, float(t[2]))
    transform = vtk.vtkTransform()
    transform.SetMatrix(mat)
    actor.SetUserTransform(transform)


def make_actor_from_stl(path, color=(0.8,0.8,0.8), opacity=1.0):
    reader = vtk.vtkSTLReader()
    reader.SetFileName(path)
    reader.Update()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(reader.GetOutput())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().SetOpacity(opacity)
    return actor


def main():
    # use default filenames in the current working directory (no dialogs)
    # parse command-line arguments (defaults use cwd filenames)
    parser = argparse.ArgumentParser(description='ICP register femur/tibia using STL vertex indices or CSVs')
    parser.add_argument('--femur-csv', type=str, default=str(Path.cwd() / 'femur_articulation.csv'), help='Femur points CSV (optional)')
    parser.add_argument('--tibia-csv', type=str, default=str(Path.cwd() / 'tibia_articulation.csv'), help='Tibia points CSV (optional)')
    parser.add_argument('--femur-stl', type=str, default=str(Path.cwd() / 'femurR.stl'), help='Femur STL path')
    parser.add_argument('--tibia-stl', type=str, default=str(Path.cwd() / 'tibiaR.stl'), help='Tibia STL path')
    parser.add_argument('--out-dir', type=str, default='.', help='Output directory (default: ./)')
    parser.add_argument('--results-name', type=str, default='tf_reg.any', help='Results filename (default tf_reg.txt)')
    parser.add_argument('--close-after-save', action='store_true', help='Close the viewer immediately after saving screenshot and results')
    args = parser.parse_args()

    femur_stl = args.femur_stl
    tibia_stl = args.tibia_stl
    femur_csv = args.femur_csv if args.femur_csv else os.path.join(args.out_dir, 'femur_articulation.csv')
    tibia_csv = args.tibia_csv if args.tibia_csv else os.path.join(args.out_dir, 'tibia_articulation.csv')
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    save_path = os.path.join(out_dir, args.results_name)

    # require STLs
    missing_stls = [p for p in (femur_stl, tibia_stl) if not os.path.exists(p)]
    if missing_stls:
        print('Missing required STL files:', missing_stls)
        return

    # load STL vertices
    fem_stl_pts = load_stl_vertices(femur_stl)
    tib_stl_pts = load_stl_vertices(tibia_stl)

    # if CSVs exist or provided, map CSV indices/coords to STL indices; CSVs are optional
    if os.path.exists(femur_csv) and os.path.exists(tibia_csv):
        A_csv, idxA_csv = load_csv_points(femur_csv)
        B_csv, idxB_csv = load_csv_points(tibia_csv)
        # if CSV provides direct STL indices (in-range and not just trivial sequence), use them
        use_direct_A = False
        use_direct_B = False
        if idxA_csv is not None and idxA_csv.size > 0:
            if np.all((idxA_csv >= 0) & (idxA_csv < fem_stl_pts.shape[0])):
                if not np.array_equal(idxA_csv, np.arange(A_csv.shape[0], dtype=int)):
                    use_direct_A = True
        if idxB_csv is not None and idxB_csv.size > 0:
            if np.all((idxB_csv >= 0) & (idxB_csv < tib_stl_pts.shape[0])):
                if not np.array_equal(idxB_csv, np.arange(B_csv.shape[0], dtype=int)):
                    use_direct_B = True

        if use_direct_A and use_direct_B:
            stl_idxA = idxA_csv.astype(int)
            stl_idxB = idxB_csv.astype(int)
            A = fem_stl_pts[stl_idxA]
            B = tib_stl_pts[stl_idxB]
            idxA = stl_idxA
            idxB = stl_idxB
            print(f'Using direct STL indices from CSV: femur {len(idxA)} indices, tibia {len(idxB)} indices')
        else:
            # map CSV points to nearest STL vertex indices
            stl_idxA = map_points_to_stl_indices(A_csv, fem_stl_pts)
            stl_idxB = map_points_to_stl_indices(B_csv, tib_stl_pts)
            A = fem_stl_pts[stl_idxA]
            B = tib_stl_pts[stl_idxB]
            idxA = stl_idxA
            idxB = stl_idxB
            print(f'Mapped CSV points to STL vertices: femur {len(idxA)} -> unique STL ids {np.unique(idxA).size}, tibia {len(idxB)} -> unique STL ids {np.unique(idxB).size}')
    else:
        # no CSVs: use all STL vertices and indices
        A = fem_stl_pts
        B = tib_stl_pts
        idxA = np.arange(A.shape[0], dtype=int)
        idxB = np.arange(B.shape[0], dtype=int)
        print('No CSVs found; using STL vertices for ICP.')
    print(f'Loaded femur points: {A.shape}, tibia points: {B.shape}')
    R, t, B_trans = icp_point_to_point(A, B, max_iters=50, tol=1e-6)
    print('ICP done. Rotation:\n', R)
    print('Translation:', t)

    # compute tibial plateau normal via PCA (smallest eigenvector)
    centroid_tibia = B.mean(axis=0)
    femur_centroid = A.mean(axis=0)
    cov = np.cov((B - centroid_tibia).T)
    w, v = np.linalg.eigh(cov)
    normal_tibia = v[:, np.argmin(w)]
    normal_tibia = normal_tibia / np.linalg.norm(normal_tibia)
    print('Tibia plateau normal (tibia coords):', normal_tibia)

    # compute offset vector and inverse transforms using helper (keeps logic testable)
    offset_m = 5.0  # mm
    offset_vec, t_offset, inv_R, inv_t, inv_t_offset, tibia_centroid_trans, normal_rot = compute_offset_and_inverses(
        R, t, centroid_tibia, femur_centroid, normal_tibia, offset_m)
    print('Applied plateau-normal offset (mm):', offset_vec)
    print(f'Distance to femur before: {np.linalg.norm(femur_centroid - tibia_centroid_trans):.6f}, after: {np.linalg.norm(femur_centroid - (tibia_centroid_trans + offset_vec)):.6f}')
    print('Translation after offset:', t_offset)

    # visualization
    ren = vtk.vtkRenderer()
    ren.SetBackground(0.1, 0.1, 0.1)
    win = vtk.vtkRenderWindow()
    win.AddRenderer(ren)
    renWinInteractor = vtk.vtkRenderWindowInteractor()
    renWinInteractor.SetRenderWindow(win)

    fem_actor = make_actor_from_stl(femur_stl, color=(0.8,0.8,0.8), opacity=1.0)
    # make temporary surfaces almost fully transparent
    tib_actor = make_actor_from_stl(tibia_stl, color=(0.2,0.6,1.0), opacity=0.05)
    # transformed tibia without offset (very transparent)
    tib_trans_no_offset = make_actor_from_stl(tibia_stl, color=(0.2,1.0,0.2), opacity=0.05)
    # transformed tibia with offset (nearly opaque result)
    tib_trans_offset = make_actor_from_stl(tibia_stl, color=(1.0,0.3,0.3), opacity=0.95)

    ren.AddActor(fem_actor)    
    ren.AddActor(tib_actor)
    ren.AddActor(tib_trans_no_offset)
    ren.AddActor(tib_trans_offset)

    # apply transforms: no-offset uses (R,t), offset uses (R,t_offset)
    apply_transform_to_actor(tib_trans_no_offset, R, t)
    apply_transform_to_actor(tib_trans_offset, R, t_offset)

    # use default results filename (already set above)
    print('Results will be written to', save_path)

    # Draw an arrow/line indicating the offset from the no-offset tibia centroid
    start_pt = (R @ centroid_tibia) + t
    end_pt = start_pt + offset_vec
    # draw a thicker tube for the offset and add an arrow for visibility
    line = vtk.vtkLineSource()
    line.SetPoint1(start_pt[0], start_pt[1], start_pt[2])
    line.SetPoint2(end_pt[0], end_pt[1], end_pt[2])
    tubef = vtk.vtkTubeFilter()
    tubef.SetInputConnection(line.GetOutputPort())
    tubef.SetRadius(0.8)  # mm
    tubef.SetNumberOfSides(24)
    tubef.Update()
    line_mapper = vtk.vtkPolyDataMapper()
    line_mapper.SetInputConnection(tubef.GetOutputPort())
    line_actor = vtk.vtkActor()
    line_actor.SetMapper(line_mapper)
    line_actor.GetProperty().SetColor(1.0, 1.0, 0.0)
    ren.AddActor(line_actor)

    # add an arrow glyph oriented along the offset vector for clarity
    vec = np.array(end_pt) - np.array(start_pt)
    length = np.linalg.norm(vec)
    if length > 1e-6:
        dir_vec = vec / length
        arrow = vtk.vtkArrowSource()
        # orient arrow (default points +X) to dir_vec
        transform_arrow = vtk.vtkTransform()
        transform_arrow.PostMultiply()
        transform_arrow.Translate(start_pt[0], start_pt[1], start_pt[2])
        # compute rotation
        default = np.array([1.0, 0.0, 0.0])
        axis = np.cross(default, dir_vec)
        axis_norm = np.linalg.norm(axis)
        if axis_norm > 1e-6:
            axis = axis / axis_norm
            angle = np.degrees(np.arccos(np.clip(np.dot(default, dir_vec), -1.0, 1.0)))
            transform_arrow.RotateWXYZ(angle, axis[0], axis[1], axis[2])
        transform_arrow.Scale(length, length * 0.1, length * 0.1)
        tfilt = vtk.vtkTransformPolyDataFilter()
        tfilt.SetTransform(transform_arrow)
        tfilt.SetInputConnection(arrow.GetOutputPort())
        tfilt.Update()
        amap = vtk.vtkPolyDataMapper()
        amap.SetInputConnection(tfilt.GetOutputPort())
        aactor = vtk.vtkActor()
        aactor.SetMapper(amap)
        aactor.GetProperty().SetColor(1.0, 1.0, 0.0)
        ren.AddActor(aactor)

    # small spheres at start and end for emphasis
    def make_sphere_at(p, r=1.0, color=(1,1,0)):
        src = vtk.vtkSphereSource()
        src.SetCenter(p[0], p[1], p[2])
        src.SetRadius(r)
        src.SetThetaResolution(24)
        src.SetPhiResolution(24)
        src.Update()
        m = vtk.vtkPolyDataMapper()
        m.SetInputConnection(src.GetOutputPort())
        a = vtk.vtkActor()
        a.SetMapper(m)
        a.GetProperty().SetColor(*color)
        return a

    ren.AddActor(make_sphere_at(start_pt, r=1.2, color=(0,1,0)))
    ren.AddActor(make_sphere_at(end_pt, r=1.2, color=(1,0,0)))

    # compute penetration volume between femur and final transformed tibia
    def read_polydata(path):
        r = vtk.vtkSTLReader()
        r.SetFileName(path)
        r.Update()
        poly = r.GetOutput()
        return poly

    try:
        fem_poly = read_polydata(femur_stl)
        tib_poly = read_polydata(tibia_stl)
        # apply transform (R, t_offset) to tibia polydata
        mat = vtk.vtkMatrix4x4()
        for rr in range(3):
            for cc in range(3):
                mat.SetElement(rr, cc, float(R[rr, cc]))
        mat.SetElement(0, 3, float(t_offset[0]))
        mat.SetElement(1, 3, float(t_offset[1]))
        mat.SetElement(2, 3, float(t_offset[2]))
        tr = vtk.vtkTransform()
        tr.SetMatrix(mat)
        tf = vtk.vtkTransformPolyDataFilter()
        tf.SetTransform(tr)
        tf.SetInputData(tib_poly)
        tf.Update()
        tib_tr = tf.GetOutput()

        # ensure triangulated
        tri1 = vtk.vtkTriangleFilter()
        tri1.SetInputData(fem_poly)
        tri1.Update()
        tri2 = vtk.vtkTriangleFilter()
        tri2.SetInputData(tib_tr)
        tri2.Update()

        boolean = vtk.vtkBooleanOperationPolyDataFilter()
        boolean.SetOperationToIntersection()
        boolean.SetInputData(0, tri1.GetOutput())
        boolean.SetInputData(1, tri2.GetOutput())
        boolean.Update()
        inter = boolean.GetOutput()
        if inter.GetNumberOfPoints() == 0 or inter.GetNumberOfCells() == 0:
            print('No intersection detected; penetration volume = 0')
            penetration_vol = 0.0
        else:
            mp = vtk.vtkMassProperties()
            mp.SetInputData(inter)
            mp.Update()
            penetration_vol = mp.GetVolume()
            print(f'Penetration volume (units^3): {penetration_vol:.6f}')
    except Exception as e:
        print('Could not compute penetration volume (boolean intersection failed):', e)
        penetration_vol = None

    # if user selected a path, write an extended results file with indices and transforms
    if save_path:
        try:
            # also compute inverse transforms (Femur CS -> Tibia CS)
            try:
                inv_R = R.T
                inv_t = -inv_R @ t
                inv_t_offset = -inv_R @ t_offset
            except Exception:
                inv_R = None
                inv_t = None
                inv_t_offset = None
            with open(save_path, 'w') as f:
                # write index arrays in AnyInt style (commented out)
                if 'idxA' in locals():
                    fem_items = ', '.join(str(int(x)) for x in idxA)
                    f.write(f'// AnyInt femur_index_array = {{{fem_items}}};\n')
                else:
                    f.write('// AnyInt femur_index_array = {};\n')
                if 'idxB' in locals():
                    tib_items = ', '.join(str(int(x)) for x in idxB)
                    f.write(f'// AnyInt tibia_index_array = {{{tib_items}}};\n')
                else:
                    f.write('// AnyInt tibia_index_array = {};\n')

                # initial transform (rotation + translation) (commented out)
                f.write('// \n// Initial transform (no-offset)\n')
                f.write('// AnyFloat initial_Rot = {')
                rows = []
                for rrow in range(3):
                    rows.append('{' + ', '.join(f'{float(R[rrow, c]):.10f}' for c in range(3)) + '}')
                f.write('// ' + ', '.join(rows) + '};\n')
                f.write('// AnyFloat initial_trans = {' + ', '.join(f'{float(x):.10f}' for x in t) + '};\n')

                # inverse (femur -> tibia) of the initial transform (commented out)
                if inv_R is not None:
                    f.write('// AnyFloat initial_Rot_inv = {')
                    rowsi = []
                    for rrow in range(3):
                        rowsi.append('{' + ', '.join(f'{float(inv_R[rrow, c]):.10f}' for c in range(3)) + '}')
                    f.write('// ' + ', '.join(rowsi) + '};\n')
                    f.write('// AnyFloat initial_trans_inv = {' + ', '.join(f'{float(x):.10f}' for x in inv_t) + '};\n')
                else:
                    f.write('// AnyFloat initial_Rot_inv = { {0,0,0},{0,0,0},{0,0,0} };\n')
                    f.write('// AnyFloat initial_trans_inv = {0,0,0};\n')

                f.write('// \n// Computed axis (plateau normal, rotated into femur frame)\n')
                f.write('// AnyFloat plateau_axis = {' + ', '.join(f'{float(x):.10f}' for x in normal_rot) + '};\n')

                f.write('// \n// Displacement vector (mm)\n')
                f.write('// AnyFloat displacement = {' + ', '.join(f'{float(x):.10f}' for x in offset_vec) + '};\n')

                # final transform (rotation + translation) (commented out)
                f.write('// \n// Final transform (with offset)\n')
                f.write('// AnyFloat final_Rot = {')
                rowsf = []
                for rrow in range(3):
                    rowsf.append('{' + ', '.join(f'{float(R[rrow, c]):.10f}' for c in range(3)) + '}')
                f.write('// ' + ', '.join(rowsf) + '};\n')
                f.write('// AnyFloat final_trans = {' + ', '.join(f'{float(x):.10f}' for x in t_offset) + '};\n')

                # inverse (femur -> tibia) of the final transform
                if inv_R is not None:
                    f.write('\n// Inverse transforms (Femur -> Tibia)\n')
                    f.write('AnyFloat final_Rot_inv = {')
                    rowsfi = []
                    for rrow in range(3):
                        rowsfi.append('{' + ', '.join(f'{float(inv_R[rrow, c]):.10f}' for c in range(3)) + '}')
                    f.write(', '.join(rowsfi) + '};\n')
                    f.write('AnyFloat final_trans_inv = {' + ', '.join(f'{float(x):.10f}' for x in inv_t_offset) + '};\n')
                else:
                    f.write('AnyFloat final_Rot_inv = { {0,0,0},{0,0,0},{0,0,0} };\n')
                    f.write('AnyFloat final_trans_inv = {0,0,0};\n')

                #f.write('\n// Penetration volume (units^3, None if not computed)\n')
                #f.write(str(penetration_vol) + '\n')

            print(f'Wrote extended results to {save_path}')
        except Exception as e:
            print('Failed to write results file:', e)

    # camera reset
    # configure camera: place it along a direction orthogonal to the computed axis
    ren.ResetCamera()
    try:
        cam = ren.GetActiveCamera()
        focal = tibia_centroid_trans
        up = normal_rot
        # choose an arbitrary vector not parallel to up
        arb = np.array([1.0, 0.0, 0.0])
        if abs(np.dot(arb, up)) > 0.9:
            arb = np.array([0.0, 1.0, 0.0])
        right = np.cross(up, arb)
        right = right / np.linalg.norm(right)
        front = np.cross(right, up)
        front = front / np.linalg.norm(front)
        # distance: 1.5 meters -> 1500 mm (inputs are mm)
        cam_dist = 1500.0
        cam_pos = focal + front * cam_dist

        # rotate camera position 90 degrees around the central axis (up)
        theta = np.deg2rad(90.0)
        k = up / np.linalg.norm(up)
        v = cam_pos - focal
        v_rot = v * np.cos(theta) + np.cross(k, v) * np.sin(theta) + k * (np.dot(k, v)) * (1 - np.cos(theta))
        cam_pos = focal + v_rot

        cam.SetPosition(float(cam_pos[0]), float(cam_pos[1]), float(cam_pos[2]))
        cam.SetFocalPoint(float(focal[0]), float(focal[1]), float(focal[2]))
        # 180-degree vertical flip: invert view-up
        cam.SetViewUp(float(-up[0]), float(-up[1]), float(-up[2]))
        # expand clipping range
        cam.SetClippingRange(0.1, cam_dist * 4.0)
        ren.ResetCameraClippingRange()
    except Exception as e:
        print('Could not set custom camera:', e)

    win.SetSize(1200, 800)
    win.SetWindowName('ICP registration: femur fixed, tibia transformed')
    renWinInteractor.Initialize()
    win.Render()

    # save a screenshot (PNG) next to the results file if provided
    try:
        if save_path:
            base = os.path.splitext(save_path)[0]
            screenshot_path = base + '_screenshot.png'
            w2if = vtk.vtkWindowToImageFilter()
            w2if.SetInput(win)
            w2if.Update()
            writer = vtk.vtkPNGWriter()
            writer.SetFileName(screenshot_path)
            writer.SetInputConnection(w2if.GetOutputPort())
            writer.Write()
            print(f'Saved screenshot to {screenshot_path}')
            if args.close_after_save:
                print('Closing viewer after save as requested (--close-after-save).')
                return
    except Exception as e:
        print('Failed to save screenshot:', e)

    renWinInteractor.Start()


if __name__ == '__main__':
    main()
