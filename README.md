# Catholic Church Incident Research

This SQLite archive documents selected incidents affecting Catholic churches, parish property and people at worship worldwide. It also documents attacks on Catholic clergy and laypeople wherever they occur. A religious motive is recorded only when supported by evidence. Each case links to published evidence. Counts describe the cases researched and depend on the project's coverage.

## Explore the cases

Download [the database](Catholic_Church_Incident_Research.sqlite) and open it in DB Browser for SQLite. Under **Browse Data**, select **case_search** to see one row per incident with its latest assessment. Filter by date, country, event type, cause, conduct or negligence. The **sources** table holds the citations for each incident.

## Update the research

Enable foreign keys in your SQLite editor. Add an incident once, link each source by incident ID, then append a dated assessment when evidence changes. Accidental origin and negligence can coexist. Record who made a negligence finding and what evidence supports it. The **project_guide** table includes entry and publication instructions.

## Publish to the Atlas

Start edits from the current database on `main`. Let SQLite assign the next incident ID and keep that ID when correcting an existing case. Set its review status to `reviewed` when its dates and sources are ready for publication. The optional `public_headlines` table holds the display title for a case.

A database commit triggers **Publish reviewed Atlas cases** in GitHub Actions. A successful run replaces the generated pages on the `atlas-web` branch together. The public site reads that branch. The original case addresses are preserved in `web/links.json`, and new cases use their incident IDs. Withdrawn cases drop out of the counts and keep an explanatory page at the old address.

[Open the live Atlas](https://incidentatlas.net/) · [Publishing history](https://github.com/fodderzero/catholic-church-incident-research/actions/workflows/publish-atlas.yml)
