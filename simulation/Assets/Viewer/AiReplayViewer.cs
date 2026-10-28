using System;
using System.IO;
using UnityEngine;

namespace MotorwaysSim
{
    public sealed partial class TrafficViewer
    {
        AiReplaySession aiReplay;
        string replayFile="";
        bool replayDiverged;

        bool TryReplayLaunch(string[] args)
        {
            int index=Array.IndexOf(args,"--replay");
            if(index<0)return false;
            try
            {
                if(index+1>=args.Length)throw new ArgumentException("--replay requires a JSON file");
                LoadReplay(args[index+1],Array.IndexOf(args,"--replay-final")>=0||Array.IndexOf(args,"--replay-verify")>=0);
                if(Array.IndexOf(args,"--replay-verify")>=0)
                {
                    Debug.Log("TRAFFIC_AI_REPLAY_PASSED="+World.TripsCompleted+"/"+World.Time+"/"+aiReplay.CompletedCommands);
                    Application.Quit(0);
                }
                int capture=Array.IndexOf(args,"--replay-capture");
                if(capture>=0&&capture+1<args.Length)StartCoroutine(Capture(args[capture+1]));
            }
            catch(Exception error)
            {
                paused=true;status="AI replay error: "+error.Message;Debug.LogError(status);
                if(Application.isBatchMode)Application.Quit(1);
            }
            return true;
        }

        void LoadReplay(string path,bool final)
        {
            if(version!=GameVersion.OriginalReference)throw new InvalidOperationException("AI replay requires Traffic Lab Original");
            var recording=JsonUtility.FromJson<AiReplayRecording>(File.ReadAllText(path));
            var session=new AiReplaySession(recording);
            // Only replace the displayed game after successful parsing/validation.
            aiReplay=session;World=session.World;seed=recording.seed;
            chosenMap=World.Scenario;variation=MapVariation.SameMap;
            replayFile=Path.GetFullPath(path);replayDiverged=false;
            paused=true;accumulator=0;inspect=true;selected=null;selectedCar=-1;
            motorwayStart=null;drag=null;pan=Vector2.zero;zoom=1;
            if(final)while(!aiReplay.Complete)aiReplay.AdvanceTick();
            status="AI replay / "+recording.source+" / seed "+seed+" / recorded score "+recording.score;
        }

        void ReplayTick()
        {
            if(aiReplay==null||aiReplay.Complete||replayDiverged)return;
            try
            {
                aiReplay.AdvanceTick();
                if(aiReplay.Complete){paused=true;status="AI replay finished and verified / "+World.TripsCompleted+" trips";}
            }
            catch(Exception error){replayDiverged=true;paused=true;status="AI replay diverged: "+error.Message;Debug.LogError(status);}
        }

        void ToggleReplayPlayback()
        {
            try
            {
                if(aiReplay.Complete){LoadReplay(replayFile,false);paused=false;}
                else paused=!paused;
            }
            catch(Exception error){paused=true;replayDiverged=true;status=error.Message;}
        }

        void UpdateReplay()
        {
            if(paused||aiReplay.Complete||replayDiverged)return;
            accumulator+=Math.Min(Time.unscaledDeltaTime,.25f)*speed;
            int ticks=0;
            while(accumulator>=World.Rules.TickSeconds&&ticks++<200&&!aiReplay.Complete&&!replayDiverged)
            {ReplayTick();accumulator-=(float)World.Rules.TickSeconds;}
        }

        void ReplayPanel(float x,float y,float width)
        {
            Say(x,y,width,"AI GAME REPLAY",title);y+=38;
            Say(x,y,width,"Seed "+seed+" / recorded score "+aiReplay.Recording.score,small);y+=28;
            Say(x,y,width,World.TripsCompleted+" trips / "+World.Time.ToString("0.0")+"s",title);y+=37;
            Say(x,y,width,"Commands "+aiReplay.CompletedCommands+" / "+aiReplay.Recording.actions.Length,small);y+=28;
            string replaySource=aiReplay.Recording.source??"";
            string sourceLabel=replaySource.StartsWith("hybrid")?"Source: planner-aided AI / normal materials":
                replaySource.StartsWith("heuristic")?"Source: heuristic diagnostic / not learned":
                replaySource=="training"?"Source: training best / normal materials":"Source: checkpoint demonstration / normal materials";
            Say(x,y,width,sourceLabel,small);y+=34;
            if(GUI.Button(new Rect(x,y,80,30),aiReplay.Complete?"Replay":paused?"Play":"Pause",button))ToggleReplayPlayback();
            if(GUI.Button(new Rect(x+87,y,80,30),"Step",button)){paused=true;ReplayTick();}
            if(GUI.Button(new Rect(x+174,y,80,30),speed+"x",button))speed=speed==1?4:speed==4?16:1;y+=39;
            if(GUI.Button(new Rect(x,y,width,28),"Restart this replay",button))
            {try{LoadReplay(replayFile,false);}catch(Exception error){status=error.Message;paused=true;}}y+=34;
            if(GUI.Button(new Rect(x,y,width,28),"Show final map / reload best",button))
            {try{LoadReplay(replayFile,true);}catch(Exception error){status=error.Message;paused=true;replayDiverged=true;}}y+=38;
            grid=GUI.Toggle(new Rect(x,y,20,24),grid,"");Say(x+22,y,85,"Grid",small,24);
            routes=GUI.Toggle(new Rect(x+120,y,20,24),routes,"");Say(x+142,y,110,"Lane routes",small,24);y+=32;
            Say(x,y,width,"Read-only replay: inspect, zoom or pan.\nSpace: play / pause / restart.\n\nReload best shows newer recordings while training continues.",text,110);y+=120;
            if(selected.HasValue)
            {
                var c=selected.Value;var b=World.BuildingAt(c);
                Say(x,y,width,b==null?"Tile "+c+" / "+World.Tile(c)+" / "+World.Degree(c)+" links":
                    (b.IsHouse?"House ":"Destination ")+b.Id+" / color "+b.Color+" / demand "+b.Demand,text,65);y+=72;
                var car=World.Cars.Find(v=>v.Id==selectedCar);
                if(car!=null){Say(x,y,width,"Car "+car.Id+" / "+car.Stage+" / wait "+car.Waiting.ToString("0.0")+"s",text,55);y+=60;}
            }
            Say(x,y,width,replayDiverged?"REPLAY DIVERGED - stopped":aiReplay.Complete?"Replay complete / final outcome verified":"Paused or playing exact recorded commands",small,60);y+=66;
            if(GUI.Button(new Rect(x,y,width,28),"Exit replay / start manual city",button))
            {aiReplay=null;paused=true;Reset(false);}
        }
    }
}
