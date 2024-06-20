from __future__ import annotations
from typing import Optional

import numpy as np
import pandas as pd

from gridmeter._utils.base_comparison_group import Comparison_Group_Algorithm

from gridmeter.individual_meter_matching.settings import Settings
from gridmeter.individual_meter_matching.distance_calc_selection import (
    DistanceMatching,
    DistanceMatchingLegacy,
)


class Individual_Meter_Matching(Comparison_Group_Algorithm):
    def __init__(self, settings: Optional[Settings] = None):
        if settings is None:
            settings = Settings()
        
        self.settings = settings

    def _create_clusters_df(self, df_raw):
        clusters = df_raw
        clusters["cluster"] = 0

        clusters = clusters.reset_index()

        # add weight column as count of id
        clusters["weight"] = clusters.groupby("id")["id"].transform("count")

        # replace duplicates after the first with 0
        clusters.loc[clusters.duplicated(subset="id", keep="first"), "weight"] = 0

        # sort by id and weight
        # clusters = clusters.sort_values(by=["id", "weight"], ascending=[True, False])

        # add duplicated column
        clusters["duplicated"] = clusters.duplicated(subset="id", keep=False)

        clusters = clusters.set_index("id")

        # reorder columns
        cols = ["treatment", "distance", "duplicated", "cluster", "weight"]
        clusters = clusters[cols]

        return clusters
    

    def _create_treatment_weights_df(self, ids):
        coeffs = np.ones(len(ids))

        treatment_weights = pd.DataFrame(coeffs, index=ids, columns=["pct_cluster_0"])
        treatment_weights.index.name = "id"

        return treatment_weights
    

    def get_comparison_group(self, treatment_data, comparison_pool_data, weights=None):
        if self.settings.SELECTION_METHOD == "legacy":
            distance_matching = DistanceMatchingLegacy(self.settings)
        else:
            distance_matching = DistanceMatching(self.settings)

        self.treatment_data = treatment_data
        self.comparison_pool_data = comparison_pool_data

        self.treatment_ids = treatment_data.ids
        self.treatment_loadshape = treatment_data.loadshape
        self.comparison_pool_loadshape = comparison_pool_data.loadshape
        self.ls_weights = self._validate_ls_weights(weights)

        # Get clusters
        df_raw = distance_matching.get_comparison_group(
            self.treatment_loadshape, 
            self.comparison_pool_loadshape, 
            weights=self.ls_weights
        )

        clusters = self._create_clusters_df(df_raw)

        # Create treatment_weights
        treatment_weights = self._create_treatment_weights_df(self.treatment_ids)

        # Assign dfs to self
        self.clusters = clusters
        self.treatment_weights = treatment_weights

        return clusters, treatment_weights
    

    def add_treatment_meters(self, treatment_data):
        # need some code to make life easier when adding treatment meters. Need to recalculate duplicate weights and unc_multiplier
        pass