# MeshFix-Rhino3D

A python package for repairing and cleaning up 3D meshes through Rhino3D software.

MeshFix-Rhino3D takes a mesh (`.stl`, `.obj`, `.ply`) and returns a repaired **mesh**: it fills holes, removes loose fragments and inner shells, and creates watertight meshes. It does not create NURBS or CAD files.

To convert the repaired mesh into a NURBS model (IGES or STEP), use **[Mesh2NURBS-Rhino3D](https://github.com/BoneHub/mesh2nurbs-rhino3d)**. The two packages are designed to be used one after the other:

| Package | Input | Output | Role |
| --- | --- | --- | --- |
| **MeshFix-Rhino3D** | mesh | mesh | Repair and clean up the mesh |
| [Mesh2NURBS-Rhino3D](https://github.com/BoneHub/mesh2nurbs-rhino3d) | mesh | NURBS (IGES/STEP) | Convert a clean mesh to NURBS |

## Requirements

1.  Rhino 8 needs to be installed and able to be executed from `C:\Program Files\Rhino 8\System\Rhino.exe`
2.  [Miniconda](https://www.anaconda.com/docs/getting-started/miniconda/install/overview)

## Installation

Create a conda environment:

```bash
conda create -n meshfix-rhino3d python==3.10
```

Activate the environment:

```bash
conda activate meshfix-rhino3d
```

Install the package:

```bash
pip install git+https://github.com/BoneHub/MeshFix-Rhino3D.git
```

If you also use Mesh2NURBS-Rhino3D, you can install both packages in the same environment.

## Usage

### Command-line

**Note**: Activate the conda environment before running the command-line tool.

The package installs the `meshfix-rhino3d` command. It launches Rhino, repairs one mesh file or all supported meshes in a folder, and saves the repaired meshes in an output folder. The input meshes are never overwritten.

#### Arguments

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `-i, --input-path` | path | required | Input mesh file or folder. If a folder is provided, all `.stl`, `.obj`, and `.ply` files in that folder are processed. |
| `-o, --output-dir` | path | `fixed` subfolder next to the input | Folder where the repaired meshes are saved, with the same file names as the input meshes. Must differ from the input folder. |
| `--steps` | one or more of `shrinkwrap`, `fixholes`, `remove-isolated-islands` | required | Chain of mesh fixing steps, applied in the given order. See [Steps](#steps). |
| `--output-filetype` | one or more of `stl`, `obj`, `ply` | filetype of the input mesh | Output mesh file type(s). Give several to save all of them, e.g. `--output-filetype stl obj`. |
| `--shrinkwrap-length` | float | `1.0` | Target shrinkwrap edge length in millimeters. Used only when `shrinkwrap` is in `--steps`. |
| `--smoothing` | float | `0.0` | Smoothing value used by the `shrinkwrap` step. Ignored if `shrinkwrap` is not in `--steps`. |
| `--rhino-path` | path | `C:\Program Files\Rhino 8\System\Rhino.exe` | Path to the Rhino executable. |
| `--keep-open` | flag | `False` | Leave Rhino open after processing finishes. |
| `--no-display` | flag | `False` | Avoids displaying objects in Rhino to reduce processing time. |

#### Steps

`--steps` accepts one or more steps separated by spaces. All steps run inside Rhino3D in the given order, and each step works on the result of the previous one. The same step can be listed more than once.

| Step | What it does in Rhino3D |
| --- | --- |
| `shrinkwrap` | Replaces the mesh with a watertight shrink-wrapped mesh (`ShrinkWrap`). Uses `--shrinkwrap-length` and `--smoothing`. |
| `fixholes` | Fills all holes in the mesh (`FillMeshHoles`). |
| `remove-isolated-islands` | Keeps only the largest connected mesh and deletes everything else. All meshes in the file are combined, split into connected parts, and the part with the largest surface area is kept. Useful for removing loose fragments and inner shells. |

#### Examples

Remove loose fragments, fill the holes, then shrink-wrap the result (saved to `C:\path\to\fixed\mesh.stl`):

```bash
meshfix-rhino3d -i "C:\path\to\mesh.stl" --steps remove-isolated-islands fixholes shrinkwrap
```

Shrink-wrap with a coarser resolution and some smoothing:

```bash
meshfix-rhino3d -i "C:\path\to\mesh.stl" --steps shrinkwrap --shrinkwrap-length 1.5 --smoothing 2
```

Repair every supported mesh in a folder and save the results as OBJ in a custom folder:

```bash
meshfix-rhino3d -i "C:\path\to\folder" --steps fixholes --output-filetype obj -o "C:\path\to\repaired"
```

### From mesh to NURBS

Repair the meshes with MeshFix-Rhino3D, then convert the repaired meshes with [Mesh2NURBS-Rhino3D](https://github.com/BoneHub/mesh2nurbs-rhino3d):

```bash
meshfix-rhino3d -i "C:\path\to\folder" --steps remove-isolated-islands shrinkwrap
mesh2nurbs-rhino3d -i "C:\path\to\folder\fixed"
```
