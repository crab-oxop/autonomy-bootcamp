"""
TODO(bootcamper): write the tests for ``src/waypoint_utils.py`` in here.

The example below covers files that parse fine: with and without ``home``,
and files with comments and blank lines in them. The rest is yours:

- Bad data: a file whose top level isn't a mapping, waypoints missing
  ``lat``, ``lon``, or ``alt``, values that aren't numbers, YAML that
  doesn't parse, and a file that isn't there.
- Out of range: latitudes past +/-90 and longitudes past +/-180 get
  rejected.
- Nothing to work with: an empty file, an empty ``waypoints`` list, and
  ``sort_clockwise_sweep`` given a list of 0 or 1 waypoints.
- ``east_north_coordinate_offset_m``: offsets you worked out yourself,
  compared with ``pytest.approx``. Never use ``==`` on meters.
- Ordering: with no ``home``, ``sort_clockwise_sweep`` goes clockwise
  starting from north.
- With a ``home``: the order starts in home's direction instead, and goes
  back to starting at north if home is right on top of the centroid.
- Two waypoints in the same direction: the closer one comes first.
- Parsing gives you frozen ``Coordinate`` objects that can't be changed.

Graded by ``warg run utils grade-tests``: pass on the real code, 90% branch
coverage, and fail on every broken copy in ``grader/mutants/``.
"""

from dataclasses import FrozenInstanceError

import pytest

from src.types import Coordinate
from src.waypoint_utils import (
    east_north_coordinate_offset_m,
    parse_waypoints_file,
    sort_clockwise_sweep,
)

M_PER_DEG = 111195.08
# The helper and the test below are given to you.


def write_to_tmp_waypoints_file(tmp_path, text):
    """Write ``text`` to a YAML file and hand back its path.

    ``tmp_path`` is a pytest fixture: a fresh empty directory per test.
    """
    path = tmp_path / "waypoints.yaml"
    path.write_text(text)
    return path


# One test, three files. ``parametrize`` runs the test body once per
# ``(text, expected)`` pair, and ``ids`` names each run so a failure tells you
# which file broke.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            """
            home: {lat: 1, lon: 2, alt: 3}
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
        (
            """
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
              - {lat: 7, lon: 8, alt: 9}
            """,
            (None, [Coordinate(4, 5, 6), Coordinate(7, 8, 9)]),
        ),
        (
            """
            # a lap

            home: {lat: 1, lon: 2, alt: 3}

            waypoints:
              # first leg
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
        (
            "",
            (None, []),
            
        ),
    ],
    ids=["home-and-waypoints", "no-home", "comments-and-blank-lines", "empty-file"],
)
def test_parse_waypoints_file_success(tmp_path, text, expected):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    assert parse_waypoints_file(path) == expected

@pytest.mark.parametrize(
    ("text"),
    [
        # 1) top level is a list, not a mapping
        """
        - {lat: 1, lon: 2, alt: 3}
        """,
        """
        waypoints:
          - {lon: 5, alt: 6}
        """,
        """
        waypoints:
          - {lat: 100, lon: 2, alt: 9}
        """,
        """
        waypoints:
          - {lat: 5, lon: 6}
        """,
        """
        waypoints:
          - {lat: 5, lon: 6, alt: "not a number"}
        """,
        


        # 2) YOUR TURN
    ],
    ids=["top-level-not-a-mapping", "missing-lat", "lat-too-high", "missing-alt", "alt-not-a-number"],
)
def test_parse_waypoints_file_bad_data(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    with pytest.raises(ValueError):
        parse_waypoints_file(path)

def test_sort_clockwise_no_home():
    north = Coordinate(43.001, -80.0, 10.0)
    east = Coordinate(43.0, -79.999, 10.0)
    south = Coordinate(42.999, -80.0, 10.0)
    west = Coordinate(43.0, -80.001, 10.0)
    result = sort_clockwise_sweep([west, south, east, north])
    assert result == [north, east, south, west]

def test_sort_clockwise_home_east():
    north = Coordinate(43.001, -80.0, 10.0)
    east = Coordinate(43.0, -79.999, 10.0)
    south = Coordinate(42.999, -80.0, 10.0)
    west = Coordinate(43.0, -80.001, 10.0)
    home = Coordinate(43.0, -79.99, 0.0)
    result = sort_clockwise_sweep([north, south, west, east], home)
    assert result == [east, south, west, north]

def test_sort_same_direction_closer_first():
    near = Coordinate(43.001, -80.0, 10.0)
    far = Coordinate(43.003, -80.0, 10.0)
    south = Coordinate(42.995, -80.0, 10.0)
    result = sort_clockwise_sweep([far, south, near])
    assert result == [near, far, south]

def test_sort_empty():
    assert sort_clockwise_sweep([]) == []

def test_sort_single():
    point = Coordinate(43.0, -80.0, 10.0)
    assert sort_clockwise_sweep([point]) == [point]

def test_offset_north():
    east, north = east_north_coordinate_offset_m(0.0, 0.0, 1.0, 0.0)
    assert east == pytest.approx(0.0, abs=1e-6)
    assert north == pytest.approx(M_PER_DEG, rel=1e-6)

def test_offset_east_at_latitude_60():
    east, north = east_north_coordinate_offset_m(60.0, 0.0, 60.0, 1.0)
    assert east == pytest.approx(M_PER_DEG * 0.5, rel=1e-6)
    assert north == pytest.approx(0, abs=1e-6)

def test_coordinate_is_frozen(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "home: {lat: 1, lon: 2, alt: 3}")
    home, _ = parse_waypoints_file(path)
    with pytest.raises(FrozenInstanceError):
        home.lat = 5.0

def test_missing_file_raises(tmp_path):
    with pytest.raises(OSError):
        parse_waypoints_file(tmp_path / "does_not_exist.yaml")
