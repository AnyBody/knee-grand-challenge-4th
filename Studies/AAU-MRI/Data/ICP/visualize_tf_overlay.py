import argparse
import re
import vtk
import numpy as np


def parse_anyfloat_matrix(lines, key):
    pat = re.compile(rf"^{re.escape(key)}\s*=\s*(.*)\s*;", re.MULTILINE)
    txt = '\n'.join(lines)
    m = pat.search(txt)
    if not m:
        return None
    body = m.group(1).strip()
    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", body)
    vals = [float(x) for x in nums]
    if len(vals) == 9:
        return np.array(vals).reshape((3,3))
    elif len(vals) == 3:
        return np.array(vals)
    else:
        return None


def read_tf_file(path):
    with open(path, 'r') as f:
        lines = [l.rstrip('\n') for l in f]
    R = parse_anyfloat_matrix(lines, 'AnyFloat final_Rot')
    t = parse_anyfloat_matrix(lines, 'AnyFloat final_trans')
    Rinv = parse_anyfloat_matrix(lines, 'AnyFloat final_Rot_inv')
    tinv = parse_anyfloat_matrix(lines, 'AnyFloat final_trans_inv')
    if R is None or t is None:
        raise RuntimeError('Could not find final_Rot/final_trans in TF file')
    return R, t, Rinv, tinv


def make_actor(path, color=(0.8,0.8,0.8), opacity=1.0):
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


def set_actor_transform(actor, R, t):
    mat = vtk.vtkMatrix4x4()
    for r in range(3):
        for c in range(3):
            mat.SetElement(r, c, float(R[r, c]))
    mat.SetElement(0, 3, float(t[0]))
    mat.SetElement(1, 3, float(t[1]))
    mat.SetElement(2, 3, float(t[2]))
    tr = vtk.vtkTransform()
    tr.SetMatrix(mat)
    actor.SetUserTransform(tr)


def render_and_save(win, out_path):
    win.Render()
    w2if = vtk.vtkWindowToImageFilter()
    w2if.SetInput(win)
    w2if.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(out_path)
    writer.SetInputConnection(w2if.GetOutputPort())
    writer.Write()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--femur', required=True)
    parser.add_argument('--shank', required=True)
    parser.add_argument('--tf', required=True)
    parser.add_argument('--out', default='visualize_tf_overlay.png')
    parser.add_argument('--interactive', action='store_true', help='Open interactive 3D window instead of saving PNG')
    args = parser.parse_args()

    R, t, Rinv, tinv = read_tf_file(args.tf)
    if Rinv is None or tinv is None:
        Rinv = R.T
        tinv = -Rinv @ t

    ren = vtk.vtkRenderer()
    ren.SetBackground(0.1, 0.1, 0.1)
    win = vtk.vtkRenderWindow()
    win.AddRenderer(ren)
    win.SetSize(1200, 900)

    # femur fixed (gray)
    fem_fixed = make_actor(args.femur, color=(0.8,0.8,0.8), opacity=1.0)
    ren.AddActor(fem_fixed)

    # shank transformed by forward (red, semi)
    shank_fwd = make_actor(args.shank, color=(1.0,0.2,0.2), opacity=0.8)
    set_actor_transform(shank_fwd, R, t)
    ren.AddActor(shank_fwd)

    # femur transformed by inverse (green, semi)
    fem_inv = make_actor(args.femur, color=(0.2,1.0,0.2), opacity=0.6)
    set_actor_transform(fem_inv, Rinv, tinv)
    ren.AddActor(fem_inv)

    # also add original shank fixed (blue, translucent) for reference
    shank_fixed = make_actor(args.shank, color=(0.2,0.6,1.0), opacity=0.25)
    ren.AddActor(shank_fixed)

    ren.ResetCamera()
    if args.interactive:
        inter = vtk.vtkRenderWindowInteractor()
        inter.SetRenderWindow(win)
        win.Render()
        inter.Initialize()
        print('Starting interactive viewer (close window to continue)')
        inter.Start()
    else:
        out_path = args.out
        render_and_save(win, out_path)
        print('Saved overlay visualization to', out_path)

if __name__ == '__main__':
    main()
