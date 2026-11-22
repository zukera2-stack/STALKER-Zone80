import unittest

from ownership import assign_parts, point_owner


def feature(source_id, kind, coordinates):
    return {"properties": {"source_id": source_id},
            "geometry": {"type": kind, "coordinates": coordinates}}


class OwnershipTests(unittest.TestCase):
    def test_internal_and_outer_boundaries(self):
        self.assertEqual(point_owner(400000, 5700000), "W")
        self.assertEqual(point_owner(400255.999, 5700256), "W")
        self.assertEqual(point_owner(400256, 5700256), "E")
        self.assertEqual(point_owner(400512, 5700256), "E")
        self.assertIsNone(point_owner(400512.001, 5700256))
        self.assertIsNone(point_owner(400256, 5700256.001))
        self.assertIsNone(point_owner(float("nan"), 5700000))

    def test_overlap_buffer_and_stable_id(self):
        points = [feature("west", "Point", [400250, 5700004]),
                  feature("east", "Point", [400262, 5700004]),
                  feature("seam", "Point", [400256, 5700004])]
        actual = [f["properties"] for tile in ("W", "E")
                  for f in assign_parts(points, tile)]
        self.assertCountEqual(actual, [
            {"source_id": "west", "part_id": "west:W"},
            {"source_id": "east", "part_id": "east:E"},
            {"source_id": "seam", "part_id": "seam:E"}])

    def test_empty_and_degenerate(self):
        features = [feature("empty", "Point", []),
                    feature("collapsed", "LineString", [[1, 1], [1, 1]]),
                    feature("flat", "Polygon", [[[0, 0], [1, 1], [2, 2], [0, 0]]]),
                    {"properties": {"source_id": "null"}, "geometry": None}]
        self.assertEqual(assign_parts(features, "W"), [])

    def test_duplicate_source_rejected(self):
        point = feature("site", "Point", [400001, 5700001])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            assign_parts([point, point], "W")


if __name__ == "__main__":
    unittest.main()
