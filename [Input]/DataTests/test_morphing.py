import numpy as np
from stl import mesh

def load_stl(filename):
    # Load the STL file
    return mesh.Mesh.from_file(filename)

def save_stl(morphed_mesh, output_filename):
    # Save the morphed mesh to a new STL file
    morphed_mesh.save(output_filename)

def morph_mesh(source_mesh, target_mesh, alpha):
    """
    Morphs the source mesh to the target mesh by interpolating the vertices.

    :param source_mesh: The source mesh (numpy-stl Mesh object)
    :param target_mesh: The target mesh (numpy-stl Mesh object)
    :param alpha: The interpolation factor (0.0 -> source, 1.0 -> target)
    :return: The morphed mesh (numpy-stl Mesh object)
    """
    # Ensure the source and target meshes have the same number of vertices
    if source_mesh.vectors.shape != target_mesh.vectors.shape:
        raise ValueError("The source and target meshes must have the same number of vertices and faces.")
    
    # Perform linear interpolation of the vertices
    morphed_vectors = source_mesh.vectors + alpha * (target_mesh.vectors - source_mesh.vectors)
    
    # Create a new mesh for the morphed result
    morphed_mesh = mesh.Mesh(np.zeros(morphed_vectors.shape[0], dtype=mesh.Mesh.dtype))
    morphed_mesh.vectors = morphed_vectors
    
    return morphed_mesh

def main():
    # Load source and target STL files
    source_filename = 'GCK4_Femur.stl'  # Change to your source STL file path
    target_filename = 'GCK6_preop_femur.stl'  # Change to your target STL file path
    output_filename = 'morphed_mesh.stl'  # Change to your desired output file path

    source_mesh = load_stl(source_filename)
    target_mesh = load_stl(target_filename)

    # Set interpolation parameter (alpha): 0.0 -> source, 1.0 -> target
    alpha = 0.5  # For example, this is halfway between source and target

    # Morph the meshes
    morphed_mesh = morph_mesh(source_mesh, target_mesh, alpha)

    # Save the morphed mesh to a new STL file
    save_stl(morphed_mesh, output_filename)

    print(f"Morphed mesh saved as {output_filename}")

if __name__ == "__main__":
    main()
