// Selected numeric configuration from the installed game; no original code or artwork.
namespace MotorwaysSim { public static class OriginalGameplayTuning {
public const double HouseContributionMultiplier=0.875;
public const double HouseSpawnDelay=10.0;
public const double HouseRetryDelay=2.0;
public static readonly double[][] HouseContribution=new double[][]{new double[]{0.0,1.0,double.PositiveInfinity,double.PositiveInfinity},new double[]{7.0,0.9200000166893005,double.PositiveInfinity,double.PositiveInfinity},new double[]{10.0,0.8700000047683716,double.PositiveInfinity,double.PositiveInfinity},new double[]{12.0,0.7799999713897705,double.PositiveInfinity,double.PositiveInfinity},new double[]{14.0,0.6800000071525574,double.PositiveInfinity,double.PositiveInfinity},new double[]{16.0,0.6000000238418579,double.PositiveInfinity,double.PositiveInfinity},new double[]{21.0,0.5,double.PositiveInfinity,double.PositiveInfinity},new double[]{26.0,0.44999998807907104,double.PositiveInfinity,double.PositiveInfinity},new double[]{28.0,0.44999998807907104,double.PositiveInfinity,double.PositiveInfinity}};
public static readonly double[][] DestinationSupplyScale=new double[][]{new double[]{0.0,1.0,0.0,0.0},new double[]{1.0,1.0,0.0,-0.6194806694984436},new double[]{2.0,0.5,-0.132492333650589,-0.132492333650589},new double[]{3.0,0.375,-0.05833333730697632,-0.05833333730697632},new double[]{5.0,0.32499998807907104,-0.0416666679084301,-0.0416666679084301},new double[]{6.0,0.25,-0.04999999329447746,-0.04999999329447746},new double[]{8.0,0.20000000298023224,-0.0010544584365561604,-0.0010544584365561604},new double[]{10.0,0.20000000298023224,-0.0,-0.009999997913837433}};
public static readonly double[][] ArrivalReduction=new double[][]{new double[]{0.0,1.0,0.0,0.0},new double[]{900.0,1.0,0.0,0.0},new double[]{1800.0,0.75,-0.000639798934571445,0.0},new double[]{2400.0,0.5,0.0,0.0}};
public static readonly double[][] ExtraDemandTimerSpeed=new double[][]{new double[]{0.0,1.0,0.0,0.0},new double[]{3.0,1.0,0.0,0.0},new double[]{15.0,4.0,0.03381362184882164,0.03381362184882164}};
public static UpgradeWeightProfile[] UpgradeWeights(string city){switch(city){
case "LosAngeles":return new UpgradeWeightProfile[]{
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.20000000298023224,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.10000000149011612,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.4000000059604645,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{new double[]{3,2,3.0}}},
new UpgradeWeightProfile{NotOfferedIncrease=1.5,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.25,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{new double[]{5,2,5.0}}},
new UpgradeWeightProfile{NotOfferedIncrease=0.05000000074505806,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{new double[]{0.0,1.25,0.0,0.0},new double[]{15.0,0.0,-0.05166666954755783,-0.05166666954755783},new double[]{40.0,-0.5,0.0,0.0}},Timeline=new double[][]{}},
};
case "Beijing":return new UpgradeWeightProfile[]{
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.20000000298023224,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.10000000149011612,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.4000000059604645,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=1.5,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.25,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.05000000074505806,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{new double[]{0.0,1.25,0.0,0.0},new double[]{15.0,0.0,-0.05000000074505806,-0.05000000074505806},new double[]{45.0,-0.5,-0.004713340196758509,-0.004713340196758509}},Timeline=new double[][]{}},
};
case "Tokyo":return new UpgradeWeightProfile[]{
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.20000000298023224,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.10000000149011612,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.4000000059604645,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{new double[]{5,3,5.0},new double[]{7,4,10.0}}},
new UpgradeWeightProfile{NotOfferedIncrease=1.5,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.25,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.05000000074505806,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{new double[]{0.0,2.0,0.0,0.0},new double[]{20.0,0.0,-0.06000000238418579,-0.06000000238418579},new double[]{45.0,-0.5,0.0,0.0}},Timeline=new double[][]{}},
};
case "DarEsSalaam":return new UpgradeWeightProfile[]{
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.20000000298023224,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.10000000149011612,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.4000000059604645,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{new double[]{3,2,3.0}}},
new UpgradeWeightProfile{NotOfferedIncrease=1.5,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.25,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.05000000074505806,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{new double[]{0.0,1.5,0.0,0.0},new double[]{15.0,0.0,-0.06000000238418579,-0.06000000238418579},new double[]{40.0,-0.5,-0.004809655249118805,-0.004809655249118805}},Timeline=new double[][]{}},
};
case "London":return new UpgradeWeightProfile[]{
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.20000000298023224,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.4000000059604645,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{new double[]{3,2,5.0},new double[]{5,3,5.0}}},
new UpgradeWeightProfile{NotOfferedIncrease=1.5,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.25,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.05000000074505806,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{},Timeline=new double[][]{}},
new UpgradeWeightProfile{NotOfferedIncrease=0.0,RelativeType=0,RelativeCurve=new double[][]{new double[]{0.00091552734375,2.00018310546875,-0.00975474901497364,-0.00975474901497364},new double[]{20.0,0.0,-0.09650956094264984,-0.09650956094264984},new double[]{40.0,-0.5,-0.004732307977974415,-0.004732307977974415}},Timeline=new double[][]{}},
};
default:return UpgradeWeights("LosAngeles");}}}}
