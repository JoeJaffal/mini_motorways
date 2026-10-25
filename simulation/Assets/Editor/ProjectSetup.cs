using System;
using System.IO;
using System.Linq;
using MotorwaysSim;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build.Reporting;
using UnityEditor.Build;
using UnityEngine;

public static class ProjectSetup
{
    [MenuItem("Traffic Lab/Prepare scene and run checks")]
    public static void PrepareAndCheck()
    {
        PlayerSettings.companyName="Traffic Lab";
        PlayerSettings.productName="Motorways Simulation Lab";
        PlayerSettings.defaultScreenWidth=1440;
        PlayerSettings.defaultScreenHeight=960;
        PlayerSettings.runInBackground=true;
        PlayerSettings.resizableWindow=true;
        PlayerSettings.fullScreenMode=FullScreenMode.Windowed;
        CreateScene(GameVersion.Custom,"Assets/Scenes/TrafficLabCustom.unity");
        CreateScene(GameVersion.OriginalReference,"Assets/Scenes/TrafficLab.unity");
        RunChecks();
        AssetDatabase.SaveAssets();
    }

    static void CreateScene(GameVersion version,string path)
    {
        var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
        var camera=new GameObject("Camera").AddComponent<Camera>();
        camera.orthographic=true;camera.backgroundColor=new Color(.985f,.958f,.85f);
        camera.clearFlags=CameraClearFlags.SolidColor;
        new GameObject("Traffic simulation and viewer").AddComponent<TrafficViewer>().AppVersion=version;
        Directory.CreateDirectory("Assets/Scenes");
        EditorSceneManager.SaveScene(scene,path);
    }

    static void Require(bool pass,string message)
    {if(!pass)throw new Exception("Simulation check failed: "+message);}

    [MenuItem("Traffic Lab/Run simulation checks")]
    public static void RunChecks()
    {
        Directory.CreateDirectory("Reports");
        File.WriteAllText("Reports/simulation-checks.txt",SimulationChecks.Run());
        Debug.Log("TRAFFIC_SIM_CHECKS_PASSED");
    }

    [MenuItem("Traffic Lab/Build both Windows apps")]
    public static void BuildWindows()
    {
        PrepareAndCheck();
        BuildApp(GameVersion.OriginalReference);
        BuildApp(GameVersion.Custom);
        Debug.Log("TRAFFIC_SIM_BUILD_PASSED: two separate apps");
    }

    [MenuItem("Traffic Lab/Build Original Windows app")]
    public static void BuildOriginalWindows(){PrepareAndCheck();BuildApp(GameVersion.OriginalReference);}

    [MenuItem("Traffic Lab/Build Custom Windows app")]
    public static void BuildCustomWindows(){PrepareAndCheck();BuildApp(GameVersion.Custom);}

    static void BuildApp(GameVersion version)
    {
        bool custom=version==GameVersion.Custom;
        string name=custom?"TrafficLabCustom":"TrafficLabOriginal";
        string scene=custom?"Assets/Scenes/TrafficLabCustom.unity":"Assets/Scenes/TrafficLab.unity";
        string product=PlayerSettings.productName;
        string identifier=PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Standalone);
        try
        {
            PlayerSettings.productName=custom?"Traffic Lab Custom":"Traffic Lab Original";
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Standalone,custom?"com.trafficlab.custom":"com.trafficlab.original");
            Directory.CreateDirectory("Builds/Windows/"+name);
            var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions {
                scenes=new[]{scene},
                locationPathName="Builds/Windows/"+name+"/"+name+".exe",target=BuildTarget.StandaloneWindows64,
                options=BuildOptions.None
            });
            if(result.summary.result!=BuildResult.Succeeded)throw new Exception(name+" Windows build failed");
        }
        finally
        {
            PlayerSettings.productName=product;
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Standalone,identifier);
        }
    }

    // Useful before connecting an RL policy: evaluate deterministic episodes without rendering.
    public static void EvaluateHeadless()
    {
        Directory.CreateDirectory("Reports");
        using(var output=new StreamWriter("Reports/baseline-evaluation.csv"))
        {
            output.WriteLine("seed,seconds,trips,demand,construction_spent,terminated,truncated");
            for(int seed=0;seed<10;seed++)
            {
                var world=new TrafficWorld(seed,true);world.Step(12000);
                output.WriteLine(FormattableString.Invariant($"{seed},{world.Time:0.00},{world.TripsCompleted},{world.DemandTotal},{world.ConstructionSpent},{world.Failed},{!world.Failed}"));
            }
        }
    }
}
