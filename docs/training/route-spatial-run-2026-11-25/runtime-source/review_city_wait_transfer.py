"""Separate Wait-task learning, native restraint and city retention."""
import argparse
import json
from pathlib import Path
from summarize_expansion_comparison import paired


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--parent-review', type=Path, required=True)
    parser.add_argument('--original-review', type=Path, required=True)
    args = parser.parse_args()
    r = args.archive
    assert json.loads((r/'status.json').read_text())['status'] == 'complete'
    city = read_rows(r/'evaluation/city-final/games.jsonl')
    parent = read_rows(args.parent_review/'games.jsonl')
    original = read_rows(args.original_review/'games.jsonl')
    comparisons = {name: paired(city, rows, ('trips', 'paid_units', 'outside_routes'))
                   for name, rows in (('parent', parent), ('original', original))}
    native = json.loads((r/'evaluation/native-final/summary.json').read_text())
    initial_native = json.loads((r/'evaluation/native-initial/summary.json').read_text())
    final_count = json.loads((r/'status.json').read_text())['added_decisions']
    decision = json.loads((r/f'evaluation/decision-{final_count}/summary.json').read_text())
    zeros = sum(row['trips'] == 0 for row in city)
    parent_zeros = sum(row['trips'] == 0 for row in parent)
    report = dict(city_mean=sum(row['trips'] for row in city)/len(city),
                  city_games=len(city), city_zeros=zeros, parent_zeros=parent_zeros,
                  city_comparisons=comparisons,
                  first_decision_target=all(row['mean_correct_probability'] >= .9 for row in decision.values()),
                  repeated_no_build_target=all(native[case]['no_build'] >= 14
                                              for case in ('homes', 'destinations', 'mismatch', 'quiet')),
                  native_service_retained=all(native[case]['all_targets_served'] >= initial_native[case]['all_targets_served']-2
                                              for case in ('match', 'join', 'route', 'quiet')),
                  city_zero_screen=zeros <= parent_zeros+1,
                  clear_paired_city_regression=comparisons['parent']['trips']['ci95'][1] < 0,
                  limits='Consumed development scenarios. A passed retention screen is not proof of equivalence or readiness. No automatic promotion/continuation.')
    (r/'transfer-review.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
