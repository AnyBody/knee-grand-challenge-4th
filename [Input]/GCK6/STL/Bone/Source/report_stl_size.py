import sys
from stl import mesh

def report_stl_size(file_path):
    try:
        model = mesh.Mesh.from_file(file_path)
        num_faces = len(model.vectors)
        # Each face is a triangle with 3 vertices
        # We'll collect all vertices and count unique ones
        unique_vertices = set()
        for face in model.vectors:
            for vertex in face:
                unique_vertices.add(tuple(vertex))
        num_vertices = len(unique_vertices)

        print(f"STL File: {file_path}")
        print(f"Number of Faces (Triangles): {num_faces}")
        print(f"Number of Unique Vertices: {num_vertices}")
    except Exception as e:
        print(f"Error loading STL file: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python report_stl_size.py <path_to_stl_file>")
        sys.exit(1)

    file_name = sys.argv[1]
    report_stl_size(file_name)