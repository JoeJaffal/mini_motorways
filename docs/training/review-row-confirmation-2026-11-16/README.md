# User-confirmed review rows — 16 November 2026

User explicitly identifies the rows left Not reviewed: **20,28,47,48,49,51,52,53,54,55,56,57,58**. Interpret as Excel row numbers in Tracker, whose first decision is row8, not decision IDs or detail-tab row numbers. All other decision rows8..58 are Reviewed. [Updated workbook](Maskable_PPO_Decisions_Reviewed.xlsx):38Reviewed/13Not reviewed. This verbal correction is authoritative despite the previously attached file having no changed cell contents.

Unreviewed mapping:

| Excel row | ID | Topic |
| --- | --- | --- |
|20|D13|Roundabout action|
|28|D21|Goal hierarchy|
|47|D40|Compute allocation|
|48|D41|Episode boundaries|
|49|D42|Pilot and checks|
|51|D44|Delegated decisions|
|52|D45|Competitive milestone|
|53|D46|Integration protocol|
|54|D47|Final-test discipline|
|55|D48|Save and resume|
|56|D49|Preflight and stop gates|
|57|D50|Hardware measurement|
|58|D51|Initial scope boundary|

Only review cells and the summary's recalculated cached result change. Choice/reason/work fields and full detail text are not silently edited. **Reviewed does not mean implemented or automatically approve superseded numeric settings.** More recent explicit chat corrections still prevail: hierarchy required but undefined; curriculum deferred; lambda unsettled with hierarchy; Ryzen/Linux Alienware replacing tentative Intel/Windows details; manual Linux-command workflow. The reviewed workbook still contains historical choice text in those areas. The current decision JSON retains these corrections and open design states, records user review separately and does not promote open choices to Done. D52hierarchy requirement is a later discussion record outside the51-row workbook and retains its existing status.

Sources: user message and unchanged attachment archived under ../user-workbook-review-2026-11-16/. [review_mapping.json](review_mapping.json) preserves exact51-row mapping. Current decision snapshot: current_decisions.json, mirrored to ../hierarchy-design-2026-11-16/current_decisions.json. No source attachment overwritten. Prior workbook snapshots remain historical.

Checks: [QA.json](QA.json), [verify.py](verify.py). All51statuscells match explicit row list; only20newlyreviewed cells plus summarycache changed; source detail-sheet values/formulas unchanged; summary formula/freeze panes preserved; ZIPintegrity/outputarchiveidentity pass. Opening and ending main views visually inspected; unchanged detail view checked on attachment. Native Excel UI not launched. ArtifactNodeexit1after completed export without explanatory error; independent filechecks pass. No model/simulator change,implementation or training.

Authoring source:update.mjs uses bundled artifact tool to import the user attachment and edit only E8:E58. For another authoring task use operation marker edit/1/xlsx and execute a scratch copy with bundled dependencies; source path and destinations must be revised for future snapshots. Local scratch and preview files remain under tmp/decision-workbook-2026-11-16 and outputs/maskable-ppo-reviewed-2026-11-16; archive contains records,workbook,checks and manifest.
