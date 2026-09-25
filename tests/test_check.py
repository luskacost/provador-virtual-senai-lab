from provador import check, paths


def test_paths_point_inside_project():
    assert (paths.ROOT / "pyproject.toml").exists()
    assert paths.POSE_MODEL.parent == paths.MODELS


def test_required_packages_listed():
    for dist in ["mediapipe", "opencv-python", "moderngl", "glfw", "pygltflib", "trimesh", "numpy", "psutil"]:
        assert dist in check.REQUIRED.values()


def test_python_version_supported():
    assert check.check_python()
