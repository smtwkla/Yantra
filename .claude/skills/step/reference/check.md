# /step — Check

Part of the step skill (`.claude/skills/step/SKILL.md`); read when the skill points here.

`/step check` finds inconsistencies in the step files. **Run
`tooling/step-check.bat` once.** It prints one line per problem, tagged with
the check's number, and changes nothing:

1. the brief's Status and its row in `docs/steps/INDEX.md` are in different stages;
2. a commit names the step but the Status is not Committed or Done, or the
   Status names a hash that is not in the current branch's history;
3. `Done`, but the impl report still has an open important check (`- [ ]`);
4. `Committed`, every important check resolved, but not `Done`;
5. a BR / BS finding of a brief review is not answered in the brief;
6. a step approved and not yet committed has no `Baseline:`, or its commit is
   not in the history;
7. the device-check list's *Done* column and the impl report's ticks disagree;
8. an index row without a folder, a folder without a row, or a step ID used
   twice;
9. a stage's files are missing (an impl report, a code review), or an impl
   report exists before approval;
10. working-tree changes no step claims;
11. a step claim is dead, or is held on a Done or Dropped step.

Then add what the script cannot judge, opening only the files a problem points
to: a Status that contradicts the latest verdict, a gate shown with findings
still open, unclaimed changes and the step they probably belong to (say it is
a guess), a check that is a false alarm and why. Report as a table: step,
problem, proposed fix. Fix nothing until the user says which fixes to make;
then follow the usual rules (never tick a check for someone, never edit a
review file).
