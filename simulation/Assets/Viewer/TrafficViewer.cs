using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;

namespace MotorwaysSim
{
    public sealed class TrafficViewer : MonoBehaviour
    {
        public TrafficWorld World {get;private set;}
        bool paused,grid,routes,inspect=true;
        float speed=1,accumulator,zoom=1,tile;
        Vector2 pan,scroll;
        Rect viewport,map;
        Cell? selected,drag;
        int selectedCar=-1,seed=42;
        GameVersion version=GameVersion.OriginalReference;
        MapVariation variation=MapVariation.SameMap;
        ScenarioKind chosenMap=ScenarioKind.LosAngeles;
        BuildTool tool;
        Texture2D circle,rounded;
        GUIStyle text,small,title,button;
        string status="Draw roads from a house driveway to a matching shop entrance.";
        readonly Color land=new Color(.985f,.958f,.85f),road=new Color(1,.998f,.97f),ink=new Color(.25f,.32f,.32f);
        readonly Color[] palette={new Color(.91f,.31f,.38f),new Color(.34f,.64f,.81f),new Color(.35f,.69f,.55f),new Color(.94f,.72f,.29f),new Color(.75f,.43f,.67f)};
        Color ColorFor(int c)=>palette[Math.Abs(c)%palette.Length];
        void Awake()
        {
            Application.targetFrameRate=60;
            if(Array.IndexOf(Environment.GetCommandLineArgs(),"--custom")>=0)version=GameVersion.Custom;
            World=new TrafficWorld(seed,false,Rules.ForVersion(version));
            circle=Shape(true);rounded=Shape(false);
            var args=Environment.GetCommandLineArgs();
            if(Array.IndexOf(args,"--lab")>=0)World.Reset(42,true);
            int capture=Array.IndexOf(args,"--capture");
            if(capture>=0&&capture+1<args.Length)
            {World.BuildReferenceNetwork();World.Step(1000);World.BuildReferenceNetwork();World.Step(600);paused=true;StartCoroutine(Capture(args[capture+1]));}
        }
        IEnumerator Capture(string path)
        {
            for(int i=0;i<12;i++)yield return new WaitForEndOfFrame();
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path)));
            var image=ScreenCapture.CaptureScreenshotAsTexture();File.WriteAllBytes(path,image.EncodeToPNG());Destroy(image);Application.Quit();
        }
        void Update()
        {
            if(paused||World.Failed||World.ScenarioRejected)return;accumulator+=Math.Min(Time.unscaledDeltaTime,.25f)*speed;
            int ticks=0;while(accumulator>=World.Rules.TickSeconds&&ticks++<200){World.Step();accumulator-=(float)World.Rules.TickSeconds;}
        }
        Texture2D Shape(bool disc)
        {
            var t=new Texture2D(64,64,TextureFormat.RGBA32,false);var pixels=new Color[4096];
            for(int y=0;y<64;y++)for(int x=0;x<64;x++)
            {float dx=Mathf.Abs(x+.5f-32),dy=Mathf.Abs(y+.5f-32);float d=disc?Mathf.Sqrt(dx*dx+dy*dy)-31:new Vector2(Mathf.Max(0,dx-23),Mathf.Max(0,dy-23)).magnitude-8;pixels[y*64+x]=new Color(1,1,1,Mathf.Clamp01(.5f-d));}
            t.SetPixels(pixels);t.Apply();return t;
        }
        void Styles()
        {
            var font=Font.CreateDynamicFontFromOSFont(new[]{"Segoe UI","Arial"},16);
            text=new GUIStyle(GUI.skin.label){font=font,fontSize=14,wordWrap=true,normal={textColor=ink}};
            small=new GUIStyle(text){fontSize=12,normal={textColor=new Color(.48f,.53f,.49f)}};
            title=new GUIStyle(text){fontSize=23,fontStyle=FontStyle.Bold};
            button=new GUIStyle(GUI.skin.button){font=font,fontSize=13,normal={background=rounded,textColor=ink},hover={background=rounded,textColor=ink},active={background=rounded,textColor=ink},border=new RectOffset(10,10,10,10)};
        }
        void Box(Rect r,Color c,bool soft=false){GUI.color=c;GUI.DrawTexture(r,soft?rounded:Texture2D.whiteTexture);GUI.color=Color.white;}
        void Disc(Vector2 p,float r,Color c){GUI.color=c;GUI.DrawTexture(new Rect(p.x-r,p.y-r,r*2,r*2),circle);GUI.color=Color.white;}
        void Line(Vector2 a,Vector2 b,float width,Color color)
        {var old=GUI.matrix;var d=b-a;GUIUtility.RotateAroundPivot(Mathf.Atan2(d.y,d.x)*Mathf.Rad2Deg,a);Box(new Rect(a.x,a.y-width/2,d.magnitude,width),color);GUI.matrix=old;Disc(a,width/2,color);Disc(b,width/2,color);}
        Vector2 At(Cell c)=>At(new Point(c));
        Vector2 At(Point p)=>new Vector2(map.x+(float)p.X*tile,map.y+(float)p.Y*tile);
        void Say(float x,float y,float w,string s,GUIStyle style=null,float h=34)=>GUI.Label(new Rect(x,y,w,h),s,style??text);
        void OnGUI()
        {
            if(World==null)return;if(text==null)Styles();
            viewport=new Rect(20,77,Mathf.Max(100,Screen.width-350),Mathf.Max(100,Screen.height-135));
            tile=Mathf.Min(viewport.width/50,viewport.height/30)*zoom;
            map=new Rect((viewport.width-50*tile)/2+pan.x,(viewport.height-30*tile)/2+pan.y,50*tile,30*tile);
            Box(new Rect(0,0,Screen.width,Screen.height),land);
            Say(24,18,390,"MOTORWAYS / TRAFFIC LAB",title);Say(430,26,Screen.width-760,World.Scenario+"  /  original rules under validation",small);
            InputMap();GUI.BeginGroup(viewport);DrawMap();GUI.EndGroup();
            Panel(Screen.width-310,12,286);
            Say(24,Screen.height-48,Screen.width-360,status,small,44);
        }
        void DrawMap()
        {
            for(int y=0;y<30;y++)for(int x=0;x<50;x++)
            {
                var c=new Cell(x,y);var p=At(c);
                if(World.Water[x,y]||World.Blocked[x,y])Box(new Rect(p.x-tile/2,p.y-tile/2,tile+1,tile+1),World.Water[x,y]?new Color(.57f,.81f,.74f):new Color(.87f,.89f,.69f));
                else if(World.Tile(c)==Infrastructure.None&&World.BuildingAt(c)==null&&(x*17+y*23)%53==3)
                {Disc(p,tile*.27f,new Color(.9f,.91f,.62f));Disc(p,tile*.09f,new Color(.64f,.74f,.37f));}
            }
            if(grid)
            {for(int x=0;x<=50;x++)Box(new Rect(map.x+x*tile,map.y,1,map.height),new Color(.6f,.65f,.5f,.18f));for(int y=0;y<=30;y++)Box(new Rect(map.x,map.y+y*tile,map.width,1),new Color(.6f,.65f,.5f,.18f));}
            for(int layer=0;layer<2;layer++)for(int y=0;y<30;y++)for(int x=0;x<50;x++)
            {
                var c=new Cell(x,y);if(World.Tile(c)==Infrastructure.None||World.RoundaboutAt(c)!=null)continue;
                var color=layer==0?new Color(.84f,.82f,.69f):road;float width=tile*(layer==0?.5f:.39f);
                if(World.PendingRemoval[x,y]&&layer==1)color=new Color(.82f,.84f,.81f);
                Disc(At(c),width/2,color);
                int mask=World.Connections[x,y];
                for(int d=0;d<8;d++)if((mask&(1<<d))!=0)Line(At(c),At(c+TrafficWorld.Directions[d]),width,color);
            }
            foreach(var r in World.Roundabouts)
            {
                var center=At(r.Center);Disc(center,tile*1.2f,new Color(.84f,.82f,.69f));Disc(center,tile*1.13f,road);Disc(center,tile*.77f,new Color(.82f,.85f,.53f));
                foreach(var c in r.Ring)for(int d=0;d<8;d++)if((World.Connections[c.X,c.Y]&(1<<d))!=0)
                {var n=c+TrafficWorld.Directions[d];if(!r.Ring.Contains(n)&&n!=r.Center)Line(At(c),At(n),tile*.39f,road);}
            }
            for(int y=0;y<30;y++)for(int x=0;x<50;x++)
            {
                var c=new Cell(x,y);var p=At(c);
                if(World.Tile(c)==Infrastructure.Bridge)
                {
                    bool horizontal=(World.Connections[x,y]&17)!=0;
                    Vector2 along=horizontal?Vector2.right:Vector2.up,side=horizontal?Vector2.up:Vector2.right;
                    for(int sign=-1;sign<=1;sign+=2)Line(p-along*tile*.48f+side*tile*.26f*sign,p+along*tile*.48f+side*tile*.26f*sign,tile*.04f,new Color(.68f,.69f,.56f));
                }
                if(World.Signals.TryGetValue(c,out var signal))
                {var q=p+new Vector2(.28f,-.28f)*tile;Box(new Rect(q.x-3,q.y-7,6,14),ink,true);Disc(q+Vector2.up*3,2,signal.Amber?Color.yellow:(signal.ActivePair&17)!=0?ColorFor(2):ColorFor(0));Disc(q+Vector2.down*3,2,signal.Amber?Color.yellow:(signal.ActivePair&68)!=0?ColorFor(2):ColorFor(0));}
                if(World.PendingRemoval[x,y])Disc(p,3,new Color(.95f,.57f,.22f));
            }
            foreach(var b in World.Buildings)Building(b);
            foreach(var car in World.Cars)
            {
                if(car.Stage==TripStage.Home)continue;
                if(routes||selectedCar==car.Id)foreach(var lane in car.Lanes)for(int i=1;i<lane.Samples.Length;i++)Line(At(lane.Samples[i-1]),At(lane.Samples[i]),1,new Color(.3f,.46f,.65f,.25f));
                if(car.Stage==TripStage.Outbound&&car.RouteIndex==0&&car.DistanceAlongLane<.02)continue;
                var p=At(car.Position);var h=car.Heading;var old=GUI.matrix;GUIUtility.RotateAroundPivot((float)(Math.Atan2(h.Y,h.X)*180/Math.PI),p);
                float w=tile*(float)World.Rules.CarLength,v=tile*.17f;var color=ColorFor(car.Color);
                Box(new Rect(p.x-w/2+1,p.y-v/2+2,w,v),new Color(.73f,.72f,.61f),true);Box(new Rect(p.x-w/2,p.y-v/2,w,v),color*.8f,true);Box(new Rect(p.x-w/2+1,p.y-v/2,w*.88f,v*.8f),color,true);Box(new Rect(p.x+w*.12f,p.y-v*.32f,w*.18f,v*.6f),Color.Lerp(color,Color.white,.65f),true);GUI.matrix=old;
                if(car.Waiting>1)Disc(p+Vector2.up*7,2,new Color(.96f,.64f,.21f));
            }
            if(selected.HasValue){var p=At(selected.Value);float s=tile*.47f;Line(p+new Vector2(-s,-s),p+new Vector2(s,-s),2,ink);Line(p+new Vector2(-s,s),p+new Vector2(s,s),2,ink);}
        }
        void Building(Building b)
        {
            var p=At(b.Cell);var color=ColorFor(b.Color);
            var d=TrafficWorld.Directions[b.DrivewayDirection];Line(At(b.Access),At(b.Access+d),tile*.31f,road);
            if(b.IsHouse)
            {
                float s=tile*.52f;Box(new Rect(p.x-s/2+3,p.y-s/2+4,s,s),new Color(.81f,.79f,.66f),true);Box(new Rect(p.x-s/2-2,p.y-s/2-2,s+4,s+4),road,true);Box(new Rect(p.x-s/2,p.y-s/2,s,s),color*.78f,true);Box(new Rect(p.x-s/2+1,p.y-s/2+1,s-3,s-4),color,true);
                int home=World.Cars.Count(c=>c.HomeId==b.Id&&c.Stage==TripStage.Home);for(int i=0;i<home;i++)Box(new Rect(p.x-s/2+i*tile*.25f,p.y+s/2+3,tile*.2f,tile*.12f),color,true);
            }
            else
            {
                var corner=At(new Point(b.Cell.X,b.Cell.Y));Box(new Rect(corner.x+3,corner.y+4,2*tile,3*tile),new Color(.83f,.81f,.69f),true);Box(new Rect(corner.x,corner.y,2*tile,3*tile),road,true);
                Box(new Rect(corner.x+tile*.14f,corner.y+tile*.14f,tile*1.68f,tile*1.6f),color*.78f,true);Box(new Rect(corner.x+tile*.2f,corner.y+tile*.2f,tile*1.51f,tile*1.42f),color,true);
                for(int i=0;i<b.Parking.Length;i++){var q=At(World.ParkingPoint(b,i));Box(new Rect(q.x-tile*.1f,q.y-tile*.24f,tile*.2f,tile*.48f),new Color(.85f,.85f,.76f),true);}
                for(int i=0;i<Math.Min(10,b.Demand);i++)Disc(new Vector2(corner.x+tile*.25f+(i%5)*tile*.33f,corner.y-tile*.18f-(i/5)*tile*.27f),tile*.10f,color);
                if(b.OvercrowdedFor>0)Box(new Rect(corner.x,corner.y+3*tile+2,2*tile*(float)(b.OvercrowdedFor/World.Rules.OvercrowdingSeconds),3),ColorFor(0));
            }
        }
        void Panel(float x,float y,float width)
        {
            Box(new Rect(x-12,0,width+35,Screen.height),new Color(.995f,.99f,.95f));
            scroll=GUI.BeginScrollView(new Rect(x,0,width+12,Screen.height),scroll,new Rect(0,0,width-8,1470));x=0;width-=12;y=15;
            Say(x,y,width,"TRAFFIC LAB",title);y+=38;
            if(GUI.Button(new Rect(x,y,124,28),"Original target",button)){version=GameVersion.OriginalReference;SwitchVersion();}
            if(GUI.Button(new Rect(x+131,y,124,28),"Your version",button)){version=GameVersion.Custom;SwitchVersion();}y+=35;
            Say(x,y,width,version==GameVersion.Custom?"YOUR RULES / unlimited construction":"ORIGINAL TARGET / fidelity incomplete",small);y+=29;
            if(GUI.Button(new Rect(x,y,width,28),"Map: "+chosenMap,button)){chosenMap=CityCatalog.Maps[(Array.IndexOf(CityCatalog.Maps,chosenMap)+1)%CityCatalog.Maps.Length];Reset(false);}y+=34;
            if(GUI.Button(new Rect(x,y,width,28),variation==MapVariation.SameMap?"Runs: same map, varied events":"Runs: different maps + varied events",button)){variation=variation==MapVariation.SameMap?MapVariation.DifferentMaps:MapVariation.SameMap;Reset(false);}y+=34;
            if(GUI.Button(new Rect(x,y,width,28),"New run / seed "+seed,button)){seed++;Reset(false);}y+=36;
            Say(x,y,width,$"Week {World.Week} / Day {World.Day%7+1} / {World.Hour:00}:00",small);y+=29;
            Say(x,y,width,World.Rules.UnlimitedConstruction?$"{World.TripsCompleted} trips    |    {World.ConstructionSpent} spent":$"{World.TripsCompleted} trips    |    {World.RoadTilesAvailable} roads",title,35);y+=39;
            Say(x,y,width,$"{World.Time:0.0}s  /  {World.ActiveCars} active cars  /  {World.DemandTotal} pins",small);y+=30;
            if(GUI.Button(new Rect(x,y,80,30),paused?"Play":"Pause",button))paused=!paused;
            if(GUI.Button(new Rect(x+87,y,80,30),"Step",button)){paused=true;World.Step();}
            if(GUI.Button(new Rect(x+174,y,80,30),speed+"x",button))speed=speed==1?4:speed==4?16:1;y+=39;
            if(GUI.Button(new Rect(x,y,124,28),"Reset city",button))Reset(false);
            if(GUI.Button(new Rect(x+131,y,124,28),"Reference lab",button))Reset(true);y+=35;
            if(GUI.Button(new Rect(x,y,width,28),"Build reference roads (debug)",button)){World.BuildReferenceNetwork();status="Debug roads added. Their cost is counted; this is not an agent action.";}y+=39;
            Say(x,y,width,World.Rules.UnlimitedConstruction?"UNLIMITED CONSTRUCTION":"MATERIALS / roads: "+World.Inventory[0]+" / bridges: "+World.Inventory[1],small);y+=24;
            if(!World.Rules.UnlimitedConstruction&&World.UpgradeChoices.Count>0)
            {
                string[] upgrades={"Road tiles","Bridge","Motorway (not ported)","Traffic lights","Roundabout","Tunnel (not ported)"};
                for(int i=0;i<World.UpgradeChoices.Count;i++){var offer=World.UpgradeChoices[i];if(GUI.Button(new Rect(x,y,width,28),offer.Amount+" "+upgrades[offer.Type]+" + "+offer.Roads+" roads",button)){World.ChooseUpgrade(i);break;}y+=33;}
            }

            string[] tools=World.Rules.UnlimitedConstruction?new[]{"Road  /  2 per tile","Bridge  /  10 per water tile","Roundabout  /  8","Traffic light  /  5","Remove  /  no refund"}:new[]{"Road / "+World.Inventory[0]+" available","Bridge / "+World.Inventory[1]+" available","Roundabout / "+World.Inventory[4]+" available","Traffic light / "+World.Inventory[3]+" available","Remove / materials return after clearing"};
            for(int i=0;i<5;i++){GUI.backgroundColor=!inspect&&(int)tool==i?new Color(.70f,.84f,.73f):Color.white;if(GUI.Button(new Rect(x,y,width,28),tools[i],button)){tool=(BuildTool)i;inspect=false;}y+=33;}
            GUI.backgroundColor=inspect?new Color(.70f,.84f,.73f):Color.white;if(GUI.Button(new Rect(x,y,width,28),"Inspect / select car or building",button))inspect=true;GUI.backgroundColor=Color.white;y+=36;
            grid=GUI.Toggle(new Rect(x,y,110,24),grid," Grid");routes=GUI.Toggle(new Rect(x+120,y,135,24),routes," Lane routes");y+=30;
            Say(x,y,width,"INSPECTOR",small);y+=24;string info="Click a car, house, shop or road.\n\nShop dots = outstanding demand.\nOrange car dot = waiting.\nOrange road dot = queued demolition.\n\nMouse wheel: zoom\nMiddle-drag: pan\nSpace: pause / play";
            if(selected.HasValue)
            {
                var c=selected.Value;var b=World.BuildingAt(c);
                info=b==null?$"Tile {c}: {World.Tile(c)}\nLinks: {World.Degree(c)}":b.IsHouse?$"House {b.Id} / color {b.Color}\n2 reusable cars\nAt home: {World.Cars.Count(v=>v.HomeId==b.Id&&v.Stage==TripStage.Home)}":$"Shop {b.Id} / color {b.Color}\nDemand: {b.Demand} / dispatched: {b.Reserved}\nParked: {b.Parking.Count(v=>v>=0)}\nOverload: {b.OvercrowdedFor:0.0}s\nOriginal demand interval: {b.OriginalDemandInterval:0.0}s\nCapacity interval: {b.FeasibleDemandInterval:0.0}s";
                var car=World.Cars.FirstOrDefault(v=>v.Id==selectedCar);
                if(car!=null)info=$"Car {car.Id} / {car.Stage}\nHome {car.HomeId} / shop {car.ShopId}\nSpeed: {car.Speed:0.00} tiles/s\nWaiting: {car.Waiting:0.0}s\n{car.Obstacle}";
            }
            Say(x,y,width,info,text,220);y+=230;
            Say(x,y,width,World.ScenarioRejected?World.RejectionReason:World.Failed?"EPISODE ENDED: shop overcrowding":"Original parity is not certified. Geometry, spawning and original upgrade behavior still need work.",small,90);y+=95;
            Say(x,y,width,version==GameVersion.Custom?"Goal: keep the city running first. Less waiting and lower cost are secondary. No learning algorithm or color penalty added.":"Missing original systems include motorways, destination upgrades, full maps/expansion and exact upgrade-choice weighting.",small,75);GUI.EndScrollView();
        }
        void SwitchVersion(){World=new TrafficWorld(seed,false,Rules.ForVersion(version));Reset(false);}
        void Reset(bool connected){World.Reset(seed,connected?ScenarioKind.ReferenceLab:chosenMap,connected?MapVariation.SameMap:variation);accumulator=0;selected=null;selectedCar=-1;pan=Vector2.zero;zoom=1;status=World.LastAction;}
        void InputMap()
        {
            var e=Event.current;if(e.type==EventType.KeyDown&&e.keyCode==KeyCode.Space){paused=!paused;e.Use();}
            if(e.type==EventType.MouseUp){drag=null;return;}if(!viewport.Contains(e.mousePosition))return;
            if(e.type==EventType.ScrollWheel){zoom=Mathf.Clamp(zoom-e.delta.y*.12f,1,4);e.Use();return;}
            if(e.type==EventType.MouseDrag&&e.button==2){pan+=e.delta;e.Use();return;}
            if(e.type!=EventType.MouseDown&&e.type!=EventType.MouseDrag)return;
            var p=e.mousePosition-viewport.position-map.position;var c=new Cell(Mathf.FloorToInt(p.x/tile),Mathf.FloorToInt(p.y/tile));if(!World.InBounds(c))return;
            if(inspect&&e.button==0)
            {
                selected=c;selectedCar=-1;var point=new Point(p.x/tile,p.y/tile);
                var car=World.Cars.Where(v=>v.Stage!=TripStage.Home).OrderBy(v=>Point.Distance(v.Position,point)).FirstOrDefault();if(car!=null&&Point.Distance(car.Position,point)<.45)selectedCar=car.Id;e.Use();return;
            }
            var active=e.button==1?BuildTool.Remove:tool;
            if(active==BuildTool.Road||active==BuildTool.Bridge){if(drag.HasValue)World.DrawRoad(drag.Value,c);else if(World.BuildingAt(c)==null)World.Build(active,c);}
            else if(e.type==EventType.MouseDown||active==BuildTool.Remove)World.Build(active,c);
            drag=c;status=World.LastAction;e.Use();
        }
    }
}
