from gridmeter.distance_calc_selection import DistanceMatching
import pandas as pd
import random


def generate_group(n_entries, make_random=True, non_random_value=5, id_prefix='t'):
    return pd.DataFrame(
        [
            {
                "id": f"{id_prefix}_{i}",
                "month_1": random.random() if make_random else non_random_value,
                "month_2": random.random() if make_random else non_random_value,
                "month_3": random.random() if make_random else non_random_value,
            }
            for i in range(1, n_entries + 1)
        ]
    ).set_index("id")


def test_distance_match():
    random.seed(1)
    n_treatment = 10
    n_pool = 100
    n_max_duplicate_check_rounds = 10
    n_matches_per_treatment = 4

    comparison_pool = pd.DataFrame(
        [
            {
                "id": f"c_{i}",
                "month_1": random.random(),
                "month_2": random.random(),
                "month_3": random.random(),
            }
            for i in range(1, n_pool + 1)
        ]
    ).set_index("id")
    treatment_group = generate_group(n_treatment, make_random=True)
    comparison_pool = generate_group(n_pool, make_random=True, id_prefix='c')
    comparison_group = DistanceMatching(
        treatment_group=treatment_group,
        comparison_pool=comparison_pool,
    ).get_comparison_group(
        n_matches_per_treatment=n_matches_per_treatment,
        n_max_duplicate_check_rounds=n_max_duplicate_check_rounds,
    )
    assert not comparison_group.empty


def test_distance_match_duplicates():
    random.seed(1)
    n_treatment = 10
    n_pool = 5
    n_max_duplicate_check_rounds = 10
    n_matches_per_treatment = 1

    # this will run out of comparison pool meters and therefore still have duplicates
    treatment_group = generate_group(n_treatment, make_random=True)
    comparison_pool = generate_group(n_pool, make_random=False, id_prefix='c')
    comparison_group = DistanceMatching(
        treatment_group=treatment_group,
        comparison_pool=comparison_pool,
    ).get_comparison_group(
        n_matches_per_treatment=n_matches_per_treatment,
        n_max_duplicate_check_rounds=n_max_duplicate_check_rounds,
    )
    assert comparison_group["duplicated"].any()


def test_distance_match_similar():
    random.seed(1)

    n_treatment = 8
    n_pool = 10
    n_max_duplicate_check_rounds = 10
    n_matches_per_treatment = 1

    # this will run through the 'duplicates' loop several times before finding unique values
    # however since here are more 'max runs allowed' than treatment meters, it will be
    # able to iterate enough times to find unique matches

    treatment_group = generate_group(n_treatment, make_random=True)
    comparison_pool = generate_group(n_pool, make_random=False)
    comparison_group = DistanceMatching(
        treatment_group=treatment_group,
        comparison_pool=comparison_pool,
    ).get_comparison_group(
        n_matches_per_treatment=n_matches_per_treatment,
        n_max_duplicate_check_rounds=n_max_duplicate_check_rounds,
    )
    assert not comparison_group["duplicated"].any()


def test_distance_match_duplicates_from_chunk():
    random.seed(1)

    n_treatment = 8
    n_pool = 10
    n_max_duplicate_check_rounds = 10
    n_matches_per_treatment = 1
    n_treatments_per_chunk = 4

    # this ensures that duplicates will not persist across chunks

    treatment_group = generate_group(n_treatment, make_random=True)
    comparison_pool = generate_group(n_pool, make_random=False, id_prefix='c')
    comparison_group = DistanceMatching(
        treatment_group=treatment_group,
        comparison_pool=comparison_pool,
    ).get_comparison_group(
        n_matches_per_treatment=n_matches_per_treatment,
        n_max_duplicate_check_rounds=n_max_duplicate_check_rounds,
    )
    assert not comparison_group["duplicated"].any()


def test_distance_match_large_treatments():
    random.seed(1)

    n_treatment = 10000
    n_pool = 20000
    n_max_duplicate_check_rounds = 10
    n_matches_per_treatment = 1
    n_treatments_per_chunk = 5000

    treatment_group = generate_group(n_treatment, make_random=True)
    comparison_pool = generate_group(n_pool, make_random=True, id_prefix='c')
    comparison_group = DistanceMatching(
        treatment_group=treatment_group,
        comparison_pool=comparison_pool,
        n_treatments_per_chunk=n_treatments_per_chunk
    ).get_comparison_group(
        n_matches_per_treatment=n_matches_per_treatment,
        n_max_duplicate_check_rounds=n_max_duplicate_check_rounds,
    )
    assert not comparison_group.empty
