# UI direction from the product owner — 2026-10-04 to 2026-10-07

Standing direction for the design review. Each item below is also logged, with
its specifics, in `app/static/DESIGN_SYSTEM.md` (Uncanonized table and
Changelog, entries dated 2026-10-04 to 2026-10-07).

## Copy

1. **No on-page explanations or instructions. Labels only.**
   - Labels, buttons, counts and state marks stay.
   - Explanation belongs in modals, hover tooltips and the `?` help.
   - A locked control shows a short label plus the link that fixes it, e.g.
     `NEEDS THE BIBLE · Open it`.
   - Empty areas show a label, e.g. `NO PANELS YET`.
   - Messages after an action are a few words, e.g. "Bible saved". Errors keep
     their reason.
   - No cost lines such as "Costs a model call". The one exception: "Can take up
     to an hour" on the world build.
2. **Plain words, not jargon or internal vocabulary.** For example "scene
   heading", never "slugline".
3. **No production-specific or development text in the app.** Everything must
   work for any screenplay or story.
4. **No provenance clutter.**
   - No file, timestamp or model lines.
   - No "from the script" tags on chosen styles: show the choice and `Change`.
   - The model picker is hidden.

## Flow

5. **The app does the work.** After the read, Production Design fills itself:
   - the Art Direction Bible first, then style anchors and palettes;
   - then thumbnails of every design language and environment, and portraits
     of the characters;
   - proposals are confirmed automatically.

   The upload button, **Process World Visualization**, is the consent.
6. **While it works, one calm screen.** "Visualizing world":
   - a spinner;
   - one step at a time, never a list of steps;
   - a background hue that drifts very slowly.

   The owner called this "a great screen". Treat it as a reference.
7. **Verbs appear when they can act.**
   - The upload button stays hidden until a file is chosen.
   - A proposal offers `Use this` and `Change`, not `Dismiss`.
8. **No errors during onboarding.** A gap that belongs to a later stage is
   future work, not an error. Don't show it until that stage is reached.

## Structure and pictures

9. **Pictures lead.** Every design language, environment and character has a
   thumbnail, rendered small first to keep image costs down.
10. **Card grids in the Style Anchor vocabulary.**
    - Environments are anchor-style cards: picture, name, description, location
      count.
    - Clicking a card opens its detail: locations, editing, larger picture.
11. **Thumbnails open larger** in the lightbox.
12. **Character thumbnails crop from the bottom**, so the head is always in
    frame. Size, aspect and composition are unchanged.
13. **Long material is sectioned, never one long scroll.**
    - The Art Direction Bible shows one section at a time, beside a grouped
      index, and each section is editable on its own.
    - Locations is a workbook with one tab per act.
14. **The human view and the model's context are separate things.** The Bible
    is formatted for people. The model receives only the sections each render
    needs.

## Limits

15. **The foundations hold.**
    - The director approves.
    - Approved work never drifts.
    - A blocked control says why before it is pressed (now as a label and a
      link).
    - Spending is consented to.

    New patterns must not erode these.
