"""Benchmark for nisl.apply_mask()

This file is indented to be placed in the nisl source directory, under
a subdirectory of nisl/. Adjust sys.path if this is not the case.

This script makes use of the adhd dataset. If it is not already on you
disk, it will be downloaded the first time this script is run. It can
take a long time.

Usage:
- first run once as 'python apply_mask.py init'
This computes two files: one containing a mask, another one the data,
uncompressed.

- then run 'python apply_mask.py gz' or 'python apply_mask.py nogz'
To run the corresponding benchmark. The first one uses an compressed
nifti file as input, the second an uncompressed nifti file. Except for
compression, the input data are identical. No output is generated: only
execution time is used.

The script is already instrumented: the apply_mask() function is wrapped
into a profile() function that is defined by profiling tools, like the
memory_profiler on the line_profiler.
Basic timing can be performed with: 'time python apply_mask.py gz'
More sophisticated timing is obtained with the line profiler:
'time kernprof.py -lv apply_mask.py gz'

To remove any cache effect, the system buffer can be deleted on linux
with this command (as root):
    sync ; echo 3 > /proc/sys/vm/drop_caches

This can have a very strong influence, in particular for uncompressed
input file.
"""

import sys
import os.path as osp

import numpy as np

import nibabel
import nisl.masking
import nisl.datasets

import utils

# profile() is defined by most profilers, these lines allows running
# the script without any profiler.
try:
    profile
except NameError:
    def profile(func):
        return func


def get_filenames(kind="gz"):
    if kind == "gz":
        adhd = nisl.datasets.fetch_adhd(n_subjects=1)
        filename = adhd["func"][0]
    elif kind == "nogz":
        filename = "0010042_rest_tshift_RPI_voreg_mni.nii"
    else:
        raise ValueError("A kind must be provided")
    # mask file is generated by write_mask.py
    return filename, "adhd_0_mask.nii"


def create_mask():
    import gzip

    print ("Computing and writing mask file...")
    filename, mask_filename = get_filenames(kind="gz")
    print("Loading data...")
    fmri = nibabel.load(filename)
    data = fmri.get_data()

    print("Computing mask on all images...")
    mask = nisl.masking.compute_epi_mask(data, opening=False).astype(np.int8)
    nibabel.save(nibabel.nifti1.Nifti1Image(mask, fmri.get_affine()),
                 mask_filename)
    print("Mask saved.")
    del mask_filename

    print("Computing uncompressed dataset...")
    filename_nogz, _ = get_filenames(kind="nogz")
    if not osp.exists(filename_nogz):
        infile = gzip.open(filename)  # no support for "with" in 2.6
        data = infile.read()
        infile.close()
        with open(filename_nogz, 'wb') as outfile:
            outfile.write(data)


def benchmark(kind="gz"):
    data_filename, mask_filename = get_filenames(kind=kind)
    smooth = 2

    if utils.cache_tools_available and False:
        print("Invalidating cache of input file...")
        utils.dontneed(data_filename)
        utils.dontneed(mask_filename)
        print("Masking data...")
        masked = utils.timeit(profile(nisl.masking.apply_mask)
                              )(data_filename, mask_filename,
                                smooth=smooth)
        del masked

    print("Masking data...")
    masked = utils.timeit(profile(nisl.masking.apply_mask)
                          )(data_filename, mask_filename,
                            smooth=smooth)
    del masked


if __name__ == "__main__":
    # Use "gz" or "nogz" as first argument. Default is "gz"
    kind = "nogz"
    if len(sys.argv) == 2:
        kind = sys.argv[1]

    if kind == "init":
        create_mask()
    else:
        benchmark(kind=kind)
