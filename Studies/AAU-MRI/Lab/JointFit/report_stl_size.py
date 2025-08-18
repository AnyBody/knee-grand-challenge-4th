import sys
import os
import glob
from stl import mesh

def report_stl_size(file_path):
    try:
        model = mesh.Mesh.from_file(file_path)
        num_faces = len(model.vectors)

        unique_vertices = set()
        for face in model.vectors:
            for vertex in face:
                unique_vertices.add(tuple(vertex))
        num_vertices = len(unique_vertices)

        return {
            "file": file_path,
            "faces": num_faces,
            "vertices": num_vertices
        }
    except Exception as e:
        return {
            "file": file_path,
            "error": str(e)
        }

def process_folder(folder_path, output_file="results.txt"):
    stl_files = glob.glob(os.path.join(folder_path, "*.stl"))
    results = []

    for stl_file in stl_files:
        result = report_stl_size(stl_file)
        results.append(result)

    with open(output_file, "w") as f:
        for r in results:
            if "error" in r:
                f.write(f"{r['file']}: Error - {r['error']}\n")
            else:
                f.write(f"{r['file']}: Faces = {r['faces']}, Unique Vertices = {r['vertices']}\n")

    print(f"Processed {len(results)} files. Results written to {output_file}")

if __name__ == '__main__':
    #if len(sys.argv) !=2 :
    #    print("Usage:")
    #    print("  python analyze_stl.py <path_to_stl_file>")
    #    print("  OR")
    #    print("  python analyze_stl.py <folder_with_stl_files>")
    #    sys.exit(1)

    path = sys.argv[1]
    output = sys.argv[2]

    if os.path.isfile(path) and path.lower().endswith('.stl'):
        result = report_stl_size(path)
        if "error" in result:
            print(f"Error processing {path}: {result['error']}")
        else:
            print(f"STL File: {result['file']}")
            print(f"Number of Faces (Triangles): {result['faces']}")
            print(f"Number of Unique Vertices: {result['vertices']}")
    elif os.path.isdir(path):
        process_folder(folder_path=path, output_file=output)
    else:
        print(f"Invalid input: {path}")
