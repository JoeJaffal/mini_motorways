"""Export selected numeric tuning, never private code/assets, from local reference JSON."""
import argparse
import json
from pathlib import Path


def export(root, target):
    constants = json.loads(next(root.glob('*SimulationConstantsData.json')).read_text())
    def number(v):
        return v['m_rawValue'] / 2**32 if isinstance(v, dict) else v
    def scalar(v):
        return 'double.PositiveInfinity' if v == float('inf') else repr(v)
    def curve(v):
        return 'new double[][]{' + ','.join('new double[]{' + ','.join(scalar(k[f]) for f in ('time', 'value', 'inSlope', 'outSlope')) + '}' for k in v['m_Curve']) + '}'
    fields = {
        'HouseContributionMultiplier': '_houseContributionMultiplier',
        'HouseSpawnDelay': 'DelayBetweenSameGroupHouseSpawns',
        'HouseRetryDelay': 'FailedHouseSpawnCooldown',
    }
    curves = {
        'HouseContribution': '_houseDistanceToContributionCurve',
        'DestinationSupplyScale': 'GroupDestinationCountToHouseValueMultiplier',
        'ArrivalReduction': 'CarArrivalPinReductionMultiplierOverTime',
        'ExtraDemandTimerSpeed': 'OvercrowdTimerSpeedMultiplierByDemand',
    }
    out = ['// Selected numeric configuration from the installed game; no original code or artwork.',
           'namespace MotorwaysSim { public static class OriginalGameplayTuning {']
    for name, key in fields.items():
        out.append(f'public const double {name}={scalar(number(constants[key]))};')
    for name, key in curves.items():
        out.append(f'public static readonly double[][] {name}={curve(constants[key])};')
    out.append('public static UpgradeWeightProfile[] UpgradeWeights(string city){switch(city){')
    for city, kind in [('losangeles','LosAngeles'),('beijing','Beijing'),('tokyo','Tokyo'),('daressalaam','DarEsSalaam'),('london','London')]:
        data = json.loads((root / f'{city}_reference.json').read_text())['trees']['CityDefinition']
        out.append(f'case "{kind}":return new UpgradeWeightProfile[]{{')
        for item in data['upgradeDefinitions']['weeklyChoicePackages']:
            timelines = 'new double[][]{' + ','.join('new double[]{' + ','.join(scalar(number(t[f])) for f in ('week','expectedUpgradeCount','bonusWeightIfNotMet')) + '}' for t in item['expectedUpgradeTimeline']) + '}'
            out.append('new UpgradeWeightProfile{NotOfferedIncrease=' + scalar(number(item['weightIncreaseWhenNotOffered'])) + ',RelativeType=' + str(item['relativeUpgradeType']) + ',RelativeCurve=' + curve(item['relativeUpgradeMultiplierCurve']) + ',Timeline=' + timelines + '},')
        out.append('};')
    out.append('default:return UpgradeWeights("LosAngeles");}}}}')
    target.write_text('\n'.join(out) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--private-json-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(args.private_json_root, args.output)
