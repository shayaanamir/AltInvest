import ml.config as config


def test_split_fractions_sum_to_one():
    assert abs(sum(config.SPLIT_FRACTIONS.values()) - 1.0) < 1e-9
