#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: Adrien Wehrlé, EO-IO

TODOs:
  - generate documentation
  - implement method for BBA combination
  - implement method for bare ice area and AAR computation

"""

import numpy as np
import rasterio
import glob
from typing import Union, Tuple
import pathlib
import os
from collections import Counter
from multiprocessing import Pool, freeze_support
from functools import partial
import time


class SICEPostProcessing:
    def __init__(
        self,
        dataset_path: str,
        regions: Union[None, list] = ["Greenland"],
        variables: list = ["albedo_bb_planar_sw", "snow_specific_surface_area"],
    ) -> None:

        self.working_directory = str(pathlib.Path().resolve())
        self.dataset_path = dataset_path
        self.variables = variables
        self.files = {}

        self.get_SICE_region_names()

        if not regions:
            self.get_available_regions()
        else:
            self.regions = regions

        self.get_files()

        return None

    def get_SICE_region_names(self) -> list:

        SICE_masks = glob.glob(f"{self.working_directory}/masks/*_1km.tif")

        self.SICE_region_names = [
            mask.split(os.sep)[-1].split("_")[0] for mask in SICE_masks
        ]

        return self.SICE_region_names

    def get_available_regions(self) -> list:

        available_regions = [
            region
            for region in self.SICE_region_names
            if os.path.isdir(f"{self.dataset_path}/{region}")
        ]

        if available_regions:
            self.regions = available_regions
        else:
            print(
                "No region with processed SICE data detected, please provide"
                + "a list of region names"
            )

        return None

    def get_files(self) -> dict:

        for region in self.regions:

            self.files[region] = {
                variable: sorted(
                    glob.glob(f"{self.dataset_path}/{region}/*/{variable}.tif")
                )
                for variable in self.variables
            }

        return self.files

    def prepare_multiprocessing(self, variable: str) -> dict:

        multiprocessing_partitions = {}

        for region in self.regions:

            region_variable_files = np.array(self.files[region][variable])
            region_years = np.array(
                [f.split(os.sep)[-2][:4] for f in region_variable_files]
            )
            available_years = np.array(list(Counter(region_years).keys()))

            # split the list of files per year to get multiprocessing partitions
            partitions = [
                region_variable_files[region_years == year] for year in available_years
            ]
            multiprocessing_partitions[region] = partitions

        return multiprocessing_partitions

    def compute_Lx_product(self, files_to_process: list) -> None:
        def compute_L3_step(
            data_stack_arr: list,
            i: int,
            rolling_window: int = 10,
            deviation_threshold: float = 0.15,
            limit_valid_days: int = 4,
        ) -> Union[np.ndarray, None]:

            if (
                i < rolling_window / 2
                or i > np.shape(data_stack_arr)[-1] - rolling_window / 2
            ):
                return None

            low_boundary = i - int(rolling_window / 2)
            high_boundary = i + int(rolling_window / 2 + 1)
            # TODO: have to stack into an array
            window_data = data_stack_arr[:, :, low_boundary:high_boundary]

            # load albedo raster at the center of rolling_window
            BBA_center = window_data[:, :, int(rolling_window / 2)]

            # # commentmpute median for each pixel time series
            median_window = np.nanmedian(window_data, axis=2)

            # per-pixel deviations within rolling_window
            deviations = np.abs((BBA_center - median_window) / median_window)

            ldata = np.full_like(BBA_center, np.nan)

            ldata[deviations < deviation_threshold] = np.nanmean(window_data, axis=2)[
                deviations < deviation_threshold
            ]

            ldata[deviations >= deviation_threshold] = np.nan

            return ldata

        variable = files_to_process[0].split(os.sep)[-1].split(".")[0]

        # L3 step is a rolling window, therefore accessing several times the same matrix,
        # so let's open the entire data set beforehand for efficiency
        data_stack = [rasterio.open(file).read(1) for file in files_to_process]
        data_stack_arr = np.dstack(data_stack)

        ex_file = files_to_process[0]
        ex_reader = rasterio.open(ex_file)
        ex_data = ex_reader.read(1)
        output_meta = ex_reader.meta.copy()

        region = ex_file.split(os.sep)[-3]
        regional_mask = rasterio.open(
            f"{self.working_directory}/masks/{region}_1km.tif"
        ).read(1)

        output_path = (
            f"{ex_file.rsplit(os.sep, 2)[0]}/L{self.level}_product_t/{variable}"
        )
        print(output_path)

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        L2_product = np.empty_like(ex_data)
        L2_product[:, :] = np.nan

        for i, data in enumerate(data_stack):

            date = files_to_process[i].split(os.sep)[-2]

            data[regional_mask != 220] = np.nan

            if self.level == 3:
                ldata = compute_L3_step(data_stack_arr, i)
                if isinstance(ldata, type(None)):
                    continue
            else:
                ldata = data.copy()

            print(ldata)

            if ("albedo" or "BBA") in variable:
                valid = [(ldata > 0) & (ldata < 1)]
            elif "area" in variable:
                valid = [(ldata > 0) & (ldata < 1)]
            elif "diameter" in variable:
                valid = [(ldata > 0) & (ldata < 1)]

            L2_product[valid] = ldata[valid]

            with rasterio.open(
                f"{output_path}/{date}.tif",
                "w",
                compress="deflate",
                **output_meta,
            ) as dest:
                dest.write(L2_product, 1)

        return None

    def compute_Lx_products_multiprocessing(
        self, level: int = 2, nb_cores: int = 4, Lx_variables: Union[None, str] = None
    ):

        if not Lx_variables:
            Lx_variables = self.variables
        self.level = level

        for variable in Lx_variables:

            multiprocessing_iterators = self.prepare_multiprocessing(variable)

            start_time = time.time()
            start_local_time = time.ctime(start_time)

            for region, annual_iterators in multiprocessing_iterators.items():

                with Pool(nb_cores) as p:
                    p.map(self.compute_Lx_product, annual_iterators)

            end_time = time.time()
            end_local_time = time.ctime(end_time)
            processing_time = (end_time - start_time) / 60
            print("--- Processing time: %s minutes ---" % processing_time)
            print("--- Start time: %s ---" % start_local_time)
            print("--- End time: %s ---" % end_local_time)

        return None

    def compute_BBA_combination(self):
        return None

    def compute_bare_ice_area(self):
        return None