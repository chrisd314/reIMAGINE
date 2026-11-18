"""Unit tests for the analyses added after the TA's feedback (toy inputs; no data, network or model needed)."""
import numpy as np
import pytest

from ouaw.corpus import check_calibration_exclusion


# ----------------------------------------------------------------- step 1: calibration is not circular
def test_calibration_exclusion_passes_on_a_clean_pool():
    S = np.array([[0.2, 0.5, 0.1], [0.3, 0.0, 0.89]])
    out = check_calibration_exclusion(["f1", "f2", "f3"], ["c1", "c2"], {"c1": ["x9"]}, S, 0.9)
    assert out["calibration_ids_in_pool"] == 0 and out["pairs_above_threshold"] == 0
    assert out["max_cosine"] == pytest.approx(0.89)
    assert out["closest"][0] == dict(calibration_id="c2", folktale_id="f3", cosine=0.89)


def test_calibration_exclusion_refuses_a_retelling_in_the_pool():
    with pytest.raises(AssertionError, match="calibration versions in the folktale pool"):
        check_calibration_exclusion(["f1", "c2"], ["c1", "c2"])


def test_calibration_exclusion_refuses_a_shingle_near_duplicate():
    with pytest.raises(AssertionError, match="near-duplicates"):
        check_calibration_exclusion(["f1", "f2"], ["c1"], {"c1": ["f2"]})


def test_calibration_exclusion_refuses_a_near_copy_by_cosine():
    S = np.array([[0.2, 0.95]])
    with pytest.raises(AssertionError, match="c1~f2"):
        check_calibration_exclusion(["f1", "f2"], ["c1"], None, S, 0.9)
