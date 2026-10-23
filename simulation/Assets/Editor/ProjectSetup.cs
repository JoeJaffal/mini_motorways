using System;
using System.IO;
using System.Linq;
using MotorwaysSim;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build.Reporting;
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
        var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
        var camera=new GameObject("Camera").AddComponent<Camera>();
        camera.orthographic=true;camera.backgroundColor=new Color(.985f,.958f,.85f);
        camera.clearFlags=CameraClearFlags.SolidColor;
        new GameObject("Traffic simulation and viewer").AddComponent<TrafficViewer>();
        Directory.CreateDirectory("Assets/Scenes");
        EditorSceneManager.SaveScene(scene,"Assets/Scenes/TrafficLab.unity");
        EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene("Assets/Scenes/TrafficLab.unity",true)};
        RunChecks();
        AssetDatabase.SaveAssets();
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

    public static void BuildWindows()
    {
        PrepareAndCheck();
        Directory.CreateDirectory("Builds/Windows");
        var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes=new[]{"Assets/Scenes/TrafficLab.unity"},
            locationPathName="Builds/Windows/TrafficLab.exe",target=BuildTarget.StandaloneWindows64,
            options=BuildOptions.None
        });
        if(result.summary.result!=BuildResult.Succeeded)throw new Exception("Windows build failed");
        Debug.Log("TRAFFIC_SIM_BUILD_PASSED");
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
