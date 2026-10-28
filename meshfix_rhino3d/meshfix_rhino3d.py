#! python3

import os
import subprocess
import argparse

STEPS = ["shrinkwrap", "fixholes", "remove-isolated-islands"]
MESH_FILETYPES = ["stl", "obj", "ply"]


def start_rhino():

    parser = argparse.ArgumentParser(
        description="Launches Rhino and repairs the given mesh file(s) by applying a chain of mesh fixing steps. The repaired meshes are saved as mesh files, ready to be converted to NURBS with mesh2nurbs-rhino3d."
    )
    parser.add_argument(
        "-i",
        "--input-path",
        required=True,
        type=str,
        help="Path to the input mesh file or folder. If a folder is given, all .stl, .obj and .ply files in that folder will be processed.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=None,
        help="Folder where the repaired meshes are saved, using the same file names as the input meshes. Defaults to a 'fixed' subfolder next to the input. Must differ from the input folder, so that the input meshes are never overwritten.",
    )
    parser.add_argument(
        "--steps",
        required=True,
        type=str,
        nargs="+",
        choices=STEPS,
        help="One or more mesh fixing steps, applied in the given order (e.g. '--steps remove-isolated-islands fixholes shrinkwrap').",
    )
    parser.add_argument(
        "--output-filetype",
        type=str,
        nargs="+",
        choices=MESH_FILETYPES,
        default=None,
        help="One or more filetypes of the repaired mesh file (e.g. '--output-filetype stl obj' saves both). Defaults to the filetype of each input mesh.",
    )
    parser.add_argument(
        "--shrinkwrap-length",
        type=float,
        default=1.0,
        help="Sets the target edge length of the shrinkwrap step in millimeters. Defaults to 1mm and does nothing if 'shrinkwrap' is not in '--steps'.",
    )
    parser.add_argument(
        "--smoothing",
        type=float,
        default=0.0,
        help="Sets the smoothing of the shrinkwrap step. Does nothing if set to 0.0 or if 'shrinkwrap' is not in '--steps'. It is advised to keep this at its default unless the input mesh has a blocky surface, since this lowers the accuracy of the process.",
    )
    parser.add_argument(
        "--rhino-path",
        type=str,
        default="C:\\Program Files\\Rhino 8\\System\\Rhino.exe",
        help="Path to the Rhino executable. Defaults to 'C:\\Program Files\\Rhino 8\\System\\Rhino.exe'.",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="if stated, the Rhino application will remain open after the process is complete.",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="if stated, the Rhino application will not be displayed during the process. This can reduce the processing time.",
    )

    args = parser.parse_args()
    input_path = os.path.abspath(args.input_path)
    if not os.path.exists(input_path):
        parser.error(f"input path does not exist: {input_path}")
    if os.path.isfile(input_path) and os.path.splitext(input_path)[1].lower().lstrip(".") not in MESH_FILETYPES:
        parser.error(f"input file must be one of {MESH_FILETYPES}: {input_path}")
    input_dir = input_path if os.path.isdir(input_path) else os.path.dirname(input_path)
    output_dir = os.path.abspath(args.output_dir) if args.output_dir else os.path.join(input_dir, "fixed")
    if os.path.normcase(output_dir) == os.path.normcase(input_dir):
        parser.error("'--output-dir' must differ from the input folder, otherwise the input meshes would be overwritten.")
    os.makedirs(output_dir, exist_ok=True)

    # Set environment variable for any args
    os.environ["INPUT_PATH"] = input_path
    os.environ["OUTPUT_DIR"] = output_dir
    os.environ["STEPS"] = ",".join(args.steps)
    os.environ["OUTPUT_FILETYPES"] = ",".join(dict.fromkeys(args.output_filetype)) if args.output_filetype else "input"
    os.environ["SHRINKWRAP_LENGTH"] = str(args.shrinkwrap_length)
    os.environ["SMOOTHING"] = str(args.smoothing)
    os.environ["KEEP_OPEN"] = str(args.keep_open)
    os.environ["NO_DISPLAY"] = str(args.no_display)

    # Launch Rhino and run script
    command = f'"{args.rhino_path}" /nosplash /runscript="_-RunPythonScript ({os.path.abspath(__file__)})"'
    subprocess.run(command)


def main():

    # Disable view redraw to improve performance during processing
    if os.environ.get("NO_DISPLAY") == "True":
        import scriptcontext
        scriptcontext.doc.Views.RedrawEnabled = False

    # Retrieve args from environment variables
    input_path = os.environ.get("INPUT_PATH")
    output_dir = os.environ.get("OUTPUT_DIR")
    steps = os.environ.get("STEPS").split(",")
    output_filetypes = os.environ.get("OUTPUT_FILETYPES").split(",")
    shrinkwrap_length = float(os.environ.get("SHRINKWRAP_LENGTH"))
    smoothing = float(os.environ.get("SMOOTHING"))
    keep_open = os.environ.get("KEEP_OPEN") == "True"

    def output_paths_for(file):
        name, ext = os.path.splitext(os.path.basename(file))
        filetypes = [ext.lstrip(".").lower()] if output_filetypes == ["input"] else output_filetypes
        return [os.path.join(output_dir, name + "." + ft) for ft in filetypes]

    if os.path.isfile(input_path):
        # Single file mode
        output_paths = output_paths_for(input_path)
        print(f"Processing single file: {input_path} -> {', '.join(output_paths)}")
        meshfix(input_path, output_paths, steps=steps, shrinkwrap_length=shrinkwrap_length, smoothing=smoothing)

    elif os.path.isdir(input_path):
        # Batch mode
        for file_name in os.listdir(input_path):
            file = os.path.join(input_path, file_name)
            if os.path.isfile(file) and os.path.splitext(file)[1].lower() in [".stl", ".obj", ".ply"]:
                meshfix(file, output_paths_for(file), steps=steps, shrinkwrap_length=shrinkwrap_length, smoothing=smoothing)
    if not keep_open:
        import rhinoscriptsyntax as rs
        rs.Command("_-Exit No")
        subprocess.run(["taskkill", "/F", "/IM", "Rhino.exe"], check=False)


def fix_mesh(
    steps=("shrinkwrap",),
    shrinkwrap_length=1.0,
    smoothing=0.0,
):
    """
    Performs a chain of mesh fixing operations on the mesh in the active Rhino document.
    The steps are applied in the given order, each one operating on the result of the previous step.
    Afterwards, the document contains only the resulting mesh, which is selected.

    Args:
        steps (str or list of str): Mesh fixing step(s) to apply in order.
            Options: 'shrinkwrap', 'fixholes', 'remove-isolated-islands'.
        shrinkwrap_length (float): Resolution for the shrinkwrap step. Only used by the 'shrinkwrap' step.
        smoothing (float): Smoothing iterations for the shrinkwrap step. Only used by the 'shrinkwrap' step.
    """
    if isinstance(steps, str):
        steps = [steps]

    invalid_steps = [step for step in steps if step not in STEPS]
    if invalid_steps:
        raise ValueError(f"Wrong steps given: {invalid_steps}. Choose from {STEPS}")

    step_functions = {
        "shrinkwrap": lambda: shrinkwrap(shrinkwrap_length=shrinkwrap_length, smoothing=smoothing),
        "fixholes": fixholes,
        "remove-isolated-islands": remove_isolated_islands,
    }
    for i, step in enumerate(steps, start=1):
        print(f"Mesh fixing step {i}/{len(steps)}: {step}")
        step_functions[step]()


def shrinkwrap(shrinkwrap_length=1.0, smoothing=0.0):
    """
    Replaces the mesh with a watertight shrink-wrapped version of it.
    """
    import rhinoscriptsyntax as rs

    rs.Command("_-SelAll Enter")
    rs.Command(
        f"_-ShrinkWrap Resolution={shrinkwrap_length} Offset=0 Smooth={smoothing} PolygonOptimize=0 FillHoles=On VertexColors=Off DeleteInput=On Preview=Off DrawWires=On HideInput=Off Enter"
    )
    rs.Command("_SelLast Enter")
    rs.Command("_Invert Enter")
    rs.Command("_Delete Enter")
    rs.Command("_-SelAll Enter")


def fixholes():
    """
    Fills all holes of the mesh.
    """
    import rhinoscriptsyntax as rs

    rs.Command("_-SelAll Enter")
    rs.Command("_-FillMeshHoles Enter")
    rs.Command("_-SelAll Enter")


def remove_isolated_islands():
    """
    Keeps only the largest connected mesh (island) and removes everything else.

    All mesh objects in the document are combined into one mesh, which is split into its connected pieces
    (the same connectivity Rhino's SplitDisjointMesh uses). The piece with the largest surface area is kept;
    all other pieces and objects are deleted.
    """
    import Rhino
    import rhinoscriptsyntax as rs
    import scriptcontext as sc

    mesh_ids = rs.ObjectsByType(rs.filter.mesh) or []
    if not mesh_ids:
        raise RuntimeError("remove-isolated-islands: no mesh found in the document.")

    combined = Rhino.Geometry.Mesh()
    for mesh_id in mesh_ids:
        combined.Append(rs.coercemesh(mesh_id))

    pieces = list(combined.SplitDisjointPieces() or []) or [combined]

    def mesh_area(mesh):
        props = Rhino.Geometry.AreaMassProperties.Compute(mesh)
        return props.Area if props else 0.0

    largest = max(pieces, key=mesh_area)
    largest.Compact()
    largest.Normals.ComputeNormals()
    print(f"remove-isolated-islands: found {len(pieces)} island(s), keeping the largest one.")

    # Put the largest island into the first mesh object and delete everything else
    rs.Command("_-SelAll Enter")
    rs.UnselectObject(mesh_ids[0])
    rs.Command("_Delete Enter")
    sc.doc.Objects.Replace(mesh_ids[0], largest)
    rs.Command("_-SelAll Enter")
    sc.doc.Views.Redraw()


def meshfix(
    input_path: str,
    output_path,
    steps=("shrinkwrap",),
    shrinkwrap_length: float = 1.0,
    smoothing: float = 0.0,
):
    """
    Repairs a single mesh by applying a chain of mesh fixing steps and exports the result as a mesh file.

    Args:
        input_path (str): Path to the input mesh file.
        output_path (str or list of str): Path(s) to the output mesh file(s) ending in '.stl', '.obj' or '.ply'.
            The result is exported once per given path.
        steps (str or list of str, optional): Mesh fixing step(s) to apply in order. Options: 'shrinkwrap',
            'fixholes', 'remove-isolated-islands'. Defaults to 'shrinkwrap'.
        shrinkwrap_length (float, optional): Resolution for the shrinkwrap step. Defaults to 1.0.
        smoothing (float, optional): Smoothing iterations for the shrinkwrap step. Defaults to 0.0.
    """

    import rhinoscriptsyntax as rs

    # Step 1: Import the mesh
    rs.Command("_-New No None Enter")
    rs.Command(f'_-Import "{input_path}" Enter')

    # Step 2: Apply the chain of mesh fixing steps
    keep_last()
    fix_mesh(steps=steps, shrinkwrap_length=shrinkwrap_length, smoothing=smoothing)
    # every mesh fixing step leaves only the resulting mesh selected
    keep_selected()

    # Step 3: Export the repaired mesh to the specified output path(s)
    output_paths = [output_path] if isinstance(output_path, str) else output_path
    for path in output_paths:
        rs.Command("_-SelAll Enter")
        rs.Command(f'_-Export "{path}" _Enter _Enter')


def keep_last():
    """
    Keep only the last created object in the Rhino document, deleting all others.
    """
    import rhinoscriptsyntax as rs

    rs.Command("_SelLast Enter")
    rs.Command("_Invert Enter")
    rs.Command("_Delete Enter")
    rs.Command("_SelLast Enter")


def keep_selected():
    """
    Keep only the currently selected objects in the Rhino document, deleting all others.
    """
    import rhinoscriptsyntax as rs

    rs.Command("_Invert Enter")
    rs.Command("_Delete Enter")
    rs.Command("_-SelAll Enter")


def cli_entry_point():
    """
    Entry point for the script. Determines if Rhino is running and either runs the main function or starts Rhino.
    """
    rhino_is_running = True
    try:
        import rhinoscriptsyntax as rs
    except ImportError:
        rhino_is_running = False
    if rhino_is_running:
        main()
    else:
        start_rhino()


if __name__ == "__main__":
    cli_entry_point()
