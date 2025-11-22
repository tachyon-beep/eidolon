"""
Data processing utilities
"""

import json
from typing import List, Dict, Any


class DataProcessor:
    """Process and transform data structures"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.cache = {}

    def process_records(self, records: List[Dict]) -> List[Dict]:
        """Process a list of records"""
        processed = []

        for record in records:
            # SECURITY: Potential injection if record contains malicious data
            processed_record = {}

            for key, value in record.items():
                # Missing validation
                processed_record[key] = self._transform_value(value)

            processed.append(processed_record)

        return processed

    def _transform_value(self, value: Any) -> Any:
        """Transform a single value"""
        if isinstance(value, str):
            return value.strip().lower()
        elif isinstance(value, (int, float)):
            return value * 2
        elif isinstance(value, list):
            return [self._transform_value(v) for v in value]
        else:
            return value

    def load_from_file(self, filename: str) -> List[Dict]:
        # BUG: No error handling for file operations
        # BUG: No validation of file format
        with open(filename, 'r') as f:
            data = json.load(f)
        return data

    def save_to_file(self, data: List[Dict], filename: str):
        # Missing error handling
        with open(filename, 'w') as f:
            json.dump(data, f)

    # CODE SMELL: Method too complex
    def aggregate_data(self, records: List[Dict], group_by: str, agg_field: str, agg_type: str):
        groups = {}

        for record in records:
            key = record.get(group_by)
            if key is None:
                continue

            if key not in groups:
                groups[key] = []

            groups[key].append(record.get(agg_field, 0))

        results = {}
        for key, values in groups.items():
            if agg_type == 'sum':
                results[key] = sum(values)
            elif agg_type == 'avg':
                results[key] = sum(values) / len(values) if values else 0
            elif agg_type == 'min':
                results[key] = min(values) if values else None
            elif agg_type == 'max':
                results[key] = max(values) if values else None
            elif agg_type == 'count':
                results[key] = len(values)
            else:
                raise ValueError(f"Unknown aggregation type: {agg_type}")

        return results


# Missing class docstring
class DataValidator:
    def __init__(self, schema):
        self.schema = schema

    def validate(self, data):
        # Oversimplified validation
        errors = []

        for field, rules in self.schema.items():
            if field not in data:
                if rules.get('required'):
                    errors.append(f"Missing required field: {field}")
                continue

            value = data[field]

            if 'type' in rules:
                if rules['type'] == 'string' and not isinstance(value, str):
                    errors.append(f"{field} must be a string")
                elif rules['type'] == 'number' and not isinstance(value, (int, float)):
                    errors.append(f"{field} must be a number")

            if 'min' in rules and value < rules['min']:
                errors.append(f"{field} must be >= {rules['min']}")

            if 'max' in rules and value > rules['max']:
                errors.append(f"{field} must be <= {rules['max']}")

        return len(errors) == 0, errors
