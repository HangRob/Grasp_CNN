from os import path, listdir
import setuptools
from torch.utils.cpp_extension import BuildExtension, CUDAExtension


def find_sources(root_dir):
    sources = []
    for file in listdir(root_dir):
        _, ext = path.splitext(file)
        if ext in [".cpp", ".cu"]:
            sources.append(path.join(root_dir, file))

    return sources


def make_extension(name, package):
    return CUDAExtension(
        name="{}.{}._backend".format(package, name),
        sources=find_sources(path.join("src", name)),
        extra_compile_args={
            "cxx": ["-O3"],
            "nvcc": ["--expt-extended-lambda"],
        },
        include_dirs=["include/","/home/test7/hang/grasp_det_seg_cnn/include"],
    )


here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    # Meta-data
    name="GraspDetSeg_CNN_Modified",
    author="Hang Li",
    author_email="ge23zop@mytum.de",
    description="Grasp Detection and Segmentation for Pytorch, code based on GraspDetSeg_CNN (https://github.com/stefan-ainetter/grasp_det_seg_cnn.git).",
    long_description_content_type="text/markdown",
    url="",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],

    # Versioning
    version="0.1.0",

    # Requirements
    python_requires=">=3, <4",

    # Package description
    packages=[
        "grasp_det_seg",
        "grasp_det_seg.algos",
        "grasp_det_seg.config",
        "grasp_det_seg.data_OCID",
        "grasp_det_seg.models",
        "grasp_det_seg.modules",
        "grasp_det_seg.modules.heads",
        "grasp_det_seg.utils",
        "grasp_det_seg.utils.bbx",
        "grasp_det_seg.utils.nms",
        "grasp_det_seg.utils.parallel",
        "grasp_det_seg.utils.roi_sampling",
    ],
    ext_modules=[
        make_extension("nms", "grasp_det_seg.utils"),
        make_extension("bbx", "grasp_det_seg.utils"),
        make_extension("roi_sampling", "grasp_det_seg.utils")
    ],
    cmdclass={"build_ext": BuildExtension},
    include_package_data=True,
)
