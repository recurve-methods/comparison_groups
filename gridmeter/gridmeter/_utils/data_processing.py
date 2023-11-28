from gridmeter._utils.loadshape_settings import Data_Settings
from gridmeter._utils import const as _const
import pandas as pd
import numpy as np


class Data:
    def __init__(self, settings: Data_Settings | None = None):
        if settings is None:
            settings = Data_Settings()

        self.settings = settings

        self.excluded_ids = pd.DataFrame(columns=["id", "reason"])

    def _find_groupby_columns(self) -> list:
        """
        Create the list of columns to be grouped by based on the time_period selected in Settings.

        Time_period : hour => group by (id, hour)
        Time_period : month => group by (id, month)
        Time_period : hourly_day_of_week => group by (id, day_of_week, hour)
        Time_period : weekday_weekend => group by (id, weekday_weekend)
        Time_period : season_day_of_week => group by (id, season, day_of_week)
        Time_period : season_hourly_weekday_weekend => group by (id, season, weekday_weekend, hour)

        """
        cols = ["id"]

        for period in _const.unique_time_periods:
            if period in self.settings.TIME_PERIOD:
                cols.append(period)

        return cols

    def _add_index_columns_from_datetime(self, df: pd.DataFrame) -> pd.DataFrame:
        # Add hour column
        if "hour" in self.settings.TIME_PERIOD:
            df["hour"] = df.index.hour

        # Add month column
        if "month" in self.settings.TIME_PERIOD:
            df["month"] = df.index.month

        # Add day_of_week column
        if "day_of_week" in self.settings.TIME_PERIOD:
            df["day_of_week"] = df.index.dayofweek

        # Add day_of_year column
        if "day_of_year" in self.settings.TIME_PERIOD:
            df["day_of_year"] = df.index.dayofyear

        # Add weekday_weekend column
        if "weekday_weekend" in self.settings.TIME_PERIOD:
            df["weekday_weekend"] = df.index.dayofweek

            # Setting the ordering to weekday, weekend
            df["weekday_weekend"] = (
                df["weekday_weekend"]
                .map(self.settings.WEEKDAY_WEEKEND._NUM_DICT)
                .map(self.settings.WEEKDAY_WEEKEND._ORDER)
            )

        # Add season column
        if "season" in self.settings.TIME_PERIOD:
            df["season"] = df.index.month.map(self.settings.SEASON._NUM_DICT).map(
                self.settings.SEASON._ORDER
            )

        return df

    def _validate_format_loadshape(self, df: pd.DataFrame) -> pd.DataFrame:
        # Check columns missing in loadshape_df
        expected_columns = ["id", "time", "loadshape"]
        missing_columns = [c for c in expected_columns if c not in df.columns]

        if missing_columns:
            raise ValueError(f"Missing columns in loadshape_df: {missing_columns}")

        # Check if all values are present in the columns as required
        # Else update the values via interpolation if missing, also ignore duplicates if present

        # loadshape df has the "time" column, whereas timeseries df has the "datetime" column
        subset_columns = expected_columns[:-1]

        # TODO: What to do with duplicates?
        df = df.drop_duplicates(subset=subset_columns, keep="first")

        # Check that the minimum time counts per id is consisitent
        unique_time_counts = df["time"].nunique()
        unique_time_counts_per_id = df.groupby("id")["time"].nunique()

        if self.settings.INTERPOLATE_MISSING:
            if self.settings.TIME_PERIOD is None:
                # for loadshape type dataframe
                # if I input a loadshape, I don't want to have to tell it the time_period I used
                # The time column should directly be pivoted, and the error checking should ensure that the number of values is consistent per meter

                invalid_ids = unique_time_counts_per_id[
                    unique_time_counts_per_id
                    < unique_time_counts * self.settings.MIN_DATA_PCT_REQUIRED
                ].index.tolist()
                invalid_ids_df = pd.DataFrame(
                    {
                        "id": invalid_ids,
                        "reason": "Unique time counts per id don't have the minimum time counts required",
                    }
                )
                self.excluded_ids = self.excluded_ids.append(
                    invalid_ids_df, ignore_index=True
                )

            else:
                # Check that the number of missing values is less than the threshold
                for id, group in df.groupby("id"):
                    if (
                        group.count().min()
                        < self.settings.MIN_DATA_PCT_REQUIRED
                        * _const.time_period_row_counts[self.settings.TIME_PERIOD]
                    ):
                        # throw out meters with missing values and record them, do not throw error

                        self.excluded_ids = self.excluded_ids.append(
                            {
                                "id": id,
                                "reason": "missing minimum number of values in loadshape_df",
                            },
                            ignore_index=True,
                        )

            # Fill NaN values with interpolation
            df = (
                df.groupby("id")
                .apply(lambda x: x.interpolate(method="linear", limit_direction="both"))
                .reset_index(drop=True)
            )

            # TODO : Interpolation should only occur on within seasons, not across seasons

        else:
            if self.settings.TIME_PERIOD is None:
                # for loadshape type dataframe
                invalid_ids = unique_time_counts_per_id[
                    unique_time_counts_per_id < unique_time_counts
                ].index.tolist()
                invalid_ids_df = pd.DataFrame(
                    {
                        "id": invalid_ids,
                        "reason": "Unique time counts per id don't have the minimum time counts required",
                    }
                )
                self.excluded_ids = self.excluded_ids.append(
                    invalid_ids_df, ignore_index=True
                )

            else:
                # throw out id with null values and record them, do not throw error

                # get a list of any rows with missing values
                excluded_ids = df[df.isnull().any(axis=1)]["id"].values
                if excluded_ids.size > 0:
                    excluded_ids = pd.DataFrame({"id": excluded_ids})
                    excluded_ids["reason"] = "null values in features_df"
                    self.excluded_ids = pd.concat([self.excluded_ids, excluded_ids])

        # pivot the loadshape_df to have the time as columns
        df = df.pivot(index="id", columns=["time"], values="loadshape")

        # Convert multi level index to single level
        df = (
            df.rename_axis(None, axis=1)
            .reset_index()
            .set_index("id")
            .drop(columns="index", axis=1, errors="ignore")
        )

        return df

    def _validate_format_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # Check columns missing in features_df
        if "id" not in df.columns:
            raise ValueError(f"Missing columns in features_df: 'id'")

        # get a list of any rows with missing values
        excluded_ids = df[df.isnull().any(axis=1)]["id"].values
        if excluded_ids.size > 0:
            excluded_ids = pd.DataFrame({"id": excluded_ids})
            excluded_ids["reason"] = "null values in features_df"
            self.excluded_ids = pd.concat([self.excluded_ids, excluded_ids])

        # remove any rows with missing values
        df = df.dropna()

        # TODO: What to do with duplicates?
        df = df.drop_duplicates(keep="first")

        # drop any ids that are in excluded_ids from loadshape (or init)
        df = df[~df["id"].isin(self.excluded_ids["id"])]
        df = (
            df.reset_index()
            .set_index("id")
            .drop(columns="index", axis=1, errors="ignore")
        )

        return df

    def _convert_timeseries_to_loadshape(
        self, time_series_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Arguments:
            Time series dataframe with columns = [id, datetime, observed, observed_error, modeled, modeled_error

        Returns :
            Loadshape dataframe with columns = [id, time, loadshape]
        """

        # Check columns missing in time_series_df
        df_type = self.settings.LOADSHAPE_TYPE
        expected_columns = ["id", "datetime"]
        if df_type == "error":
            expected_columns.extend(["observed", "modeled"])
        else:
            expected_columns.append(df_type)

        missing_columns = [
            c for c in expected_columns if c not in time_series_df.columns
        ]
        if missing_columns:
            raise ValueError(f"Missing columns in time_series_df: {missing_columns}")

        # Check that the datetime column is actually of type datetime
        if time_series_df["datetime"].dtypes != "datetime64[ns]":
            raise ValueError("The 'datetime' column must be of datetime type")

        if df_type == "error":
            pass  # TODO: calculate error

        # Remove duplicates
        subset_columns = expected_columns[:-1]

        # TODO: What to do with duplicates?
        base_df = time_series_df.drop_duplicates(subset=subset_columns, keep="first")

        # Create a base df for adding all required columns
        base_df = base_df.set_index("datetime")

        # Check that the time column is having a minimum granularity lower than requested time period, otherwise we cannot aggregate
        base_df["time_diff"] = base_df.index.diff()
        min_time_diff_per_id = base_df.groupby("id")["time_diff"].min().dt.total_seconds() / 60

        # Get the ids that have a higher minimum granularity than defined
        invalid_ids = min_time_diff_per_id[min_time_diff_per_id > _const.min_granularity_per_time_period[self.settings.TIME_PERIOD]].index.tolist()

        # If there are any invalid ids, add them to the excluded_ids dataframe
        if invalid_ids:
            invalid_ids_df = pd.DataFrame({'id': invalid_ids, 'reason': "Minimum time interval is more than the specified TimePeriod"})
            self.excluded_ids = self.excluded_ids.append(invalid_ids_df, ignore_index=True)


        base_df = self._add_index_columns_from_datetime(base_df)

        # Aggregate the input time_series based on time_period

        group_by_columns = self._find_groupby_columns()

        grouped_df = base_df.groupby(group_by_columns)[self.settings.LOADSHAPE_TYPE]

        agg_df = grouped_df.agg(loadshape=self.settings.AGG_TYPE).reset_index()

        # Sort the values so that the ordering is maintained correctly
        agg_df = agg_df.sort_values(by=group_by_columns)

        # Create the count of the index per ID
        agg_df["time"] = agg_df.groupby("id").cumcount() + 1

        # Validate that all the values are correct
        loadshape_df = self._validate_format_loadshape(agg_df)

        return loadshape_df

    def set_data(
        self, loadshape_df=None, time_series_df=None, features_df=None
    ) -> None:
        """

        Args:
            Loadshape_df: columns = [id, time, loadshape]

            Time_series_df: columns = [id, datetime, observed, observed_error, modeled, modeled_error]

            Features_df: columns = [id, {feature_1}, {feature_2}, ...]

        Output:
            loadshape: index = id, columns = time, values = loadshape

            features: index = id, columns = [{feature_1}, {feature_2}, ...]


        """
        if loadshape_df is None and time_series_df is None and features_df is None:
            raise ValueError(
                "A loadshape, time series, or features dataframe must be provided."
            )

        elif loadshape_df is not None and time_series_df is not None:
            raise ValueError(
                "Both loadshape dataframe and time series dataframe are provided. Please provide only one."
            )

        if loadshape_df is not None:
            loadshape_df = self._validate_format_loadshape(loadshape_df)

        elif time_series_df is not None:
            loadshape_df = self._convert_timeseries_to_loadshape(time_series_df)

        if features_df is not None:
            features_df = self._validate_format_features(features_df)

        if loadshape_df is not None:
            # drop any ids that are in the excluded_ids list
            loadshape_df = loadshape_df[
                ~loadshape_df.index.isin(self.excluded_ids["id"])
            ]

        self.features = features_df
        self.loadshape = loadshape_df


if __name__ == "__main__":
    # Create a testing dataframe having an id, datetime of 15 min intervals, observed and modeled values
    num_intervals = 4 * 24 * 365  # 4 intervals/hour * 24 hours/day * 365 days

    # Create a DataFrame with 'id', 'datetime', 'observed', and 'modeled' columns
    df = pd.DataFrame(
        {
            "id": np.repeat(
                ["id1", "id2", "id3"], num_intervals
            ),  # only 3 ids for easier comparison
            "datetime": pd.date_range(
                start="2023-01-01", periods=num_intervals, freq="15T"
            ).tolist()
            * 3,
            "observed": np.random.rand(num_intervals * 3),  # randomized
            "modeled": np.random.rand(num_intervals * 3),  # randomized
        }
    )

    # # Create a boolean mask for Mondays and Wednesdays , will give ValueError at 80% threshold
    # day_mask = df['datetime'].dt.dayofweek.isin([0,2])

    # # Set 'observed' and 'modeled' values to NaN for all Mondays and Wednesdays
    # df.loc[day_mask, ['observed', 'modeled']] = np.nan

    # Convert 'datetime' column to datetime type
    df["datetime"] = pd.to_datetime(df["datetime"])

    data = Data(None)
    data.set_data(time_series_df=df)
    print(data.loadshape)