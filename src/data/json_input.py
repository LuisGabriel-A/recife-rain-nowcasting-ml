"""Decode JSON without silently overwriting duplicate fields or accepting NaN."""

import json


def parse_json(text):
    def object_from_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"Nonfinite JSON value: {value}")

    return json.loads(text, object_pairs_hook=object_from_pairs, parse_constant=reject_constant)
