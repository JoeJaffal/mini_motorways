using System;
using System.IO;
using UnityEngine;
namespace MotorwaysSim
{
    public sealed partial class TrafficViewer
    {
        CustomScenarioSession customScenario;
        string customScenarioFile="",seedText="42",customScenarioInput="";
        bool customScenarioError;
        bool TryCustomScenarioLaunch(string[] args)
        {
            int index=Array.IndexOf(args,"--scenario-file");if(index<0)return false;
            try
            {
                if(index+1>=args.Length)throw new ArgumentException("--scenario-file requires a JSON path");
                LoadCustomScenarioFile(args[index+1]);
                if(Array.IndexOf(args,"--scenario-final")>=0||Array.IndexOf(args,"--scenario-verify")>=0)
                    while(!customScenario.Complete)customScenario.AdvanceTick();
                if(Array.IndexOf(args,"--scenario-verify")>=0)
                {Debug.Log("TRAFFIC_CUSTOM_SCENARIO_PASSED="+World.TripsCompleted+"/"+World.Time+"/"+customScenario.CompletedEvents);Application.Quit(0);}
            }
            catch(Exception error){paused=true;customScenarioError=true;status=error.Message;Debug.LogError(status);if(Application.isBatchMode)Application.Quit(1);}
            return true;
        }
        void LoadCustomScenarioFile(string path)
        {
            if(version!=GameVersion.OriginalReference)throw new InvalidOperationException("Custom scenarios require Original");
            var definition=JsonUtility.FromJson<CustomScenarioDefinition>(File.ReadAllText(path));
            var session=new CustomScenarioSession(definition);
            customScenario=session;World=session.World;seed=definition.seed;seedText=seed.ToString();chosenMap=World.Scenario;
            customScenarioFile=Path.GetFullPath(path);customScenarioError=false;paused=true;accumulator=0;
            selected=null;selectedCar=-1;drag=null;motorwayStart=null;pan=Vector2.zero;zoom=1;
            status="Custom scenario: "+definition.id;
        }
        void UpdateCustomScenario()
        {
            if(paused||customScenario.Complete||customScenarioError)return;
            accumulator+=Math.Min(Time.unscaledDeltaTime,.25f)*speed;
            try
            {
                int ticks=0;while(accumulator>=World.Rules.TickSeconds&&ticks++<200&&!customScenario.Complete)
                {customScenario.AdvanceTick();accumulator-=(float)World.Rules.TickSeconds;}
                if(customScenario.Complete)paused=true;
            }
            catch(Exception error){customScenarioError=true;paused=true;status="Scenario stopped: "+error.Message;Debug.LogError(status);}
        }
        void CustomScenarioPanel(float x,float y,float width)
        {
            Say(x,y,width,"CUSTOM SCENARIO",title);y+=38;
            Say(x,y,width,customScenario.Definition.id,small,50);y+=54;
            Say(x,y,width,"Simulation: "+World.TripsCompleted+" trips",title);y+=38;
            Say(x,y,width,"Recorded reference: "+customScenario.Definition.referenceScore+" trips",small);y+=30;
            Say(x,y,width,World.Time.ToString("0.00")+"s / "+customScenario.CompletedEvents+" of "+customScenario.Definition.events.Length+" events",small,45);y+=48;
            Say(x,y,width,"Reconstructed events; not a recovered original seed.",small,65);y+=68;
            if(GUI.Button(new Rect(x,y,80,30),paused?"Play":"Pause",button))paused=!paused;
            if(GUI.Button(new Rect(x+87,y,80,30),"Step",button))
            {paused=true;try{customScenario.AdvanceTick();}catch(Exception error){customScenarioError=true;status=error.Message;}}
            if(GUI.Button(new Rect(x+174,y,80,30),speed+"x",button))speed=speed==1?4:speed==4?16:1;y+=38;
            if(GUI.Button(new Rect(x,y,width,28),"Restart scenario",button))
            {try{LoadCustomScenarioFile(customScenarioFile);}catch(Exception error){customScenarioError=true;status=error.Message;}}y+=35;
            grid=GUI.Toggle(new Rect(x,y,20,24),grid,"");Say(x+22,y,width-22,"Grid",small);y+=32;
            routes=GUI.Toggle(new Rect(x,y,20,24),routes,"");Say(x+22,y,width-22,"Lane routes",small);y+=35;
            Say(x,y,width,customScenario.Definition.uncertainties??"",small,160);y+=165;
            Say(x,y,width,customScenarioError?status:customScenario.Complete?World.Failed?"Run ended: destination overcrowding":"Recorded timeline ended":status,small,140);
        }
    }
}
