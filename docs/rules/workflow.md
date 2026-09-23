# Workflow

The parent chat coordinates. Project subagents each do one job. Dispatch the matching agent even for a small task. Do not nest subagents. Each launch gets a self-contained prompt.

The parent owns issues, branches, commits, and pull requests. `fe-implement` commits only when the user already asked in that turn. Bugbot and security-review run only on request.

## Roster

| Agent | When | Model |
| --- | --- | --- |
| `fe-explore` | Before a change, when file layout or data flow is unknown | `composer-2.5-fast`, readonly |
| `fe-implement` | One scoped change after the parent already has a plan | `inherit` |
| `fe-strategy-review` | Right after persistence, ranking, selection, import, or bundle work | `claude-opus-5-thinking-high` |
| `fe-ui-review` | Right after local web UI or web presentation changes | `claude-4-sonnet` |

## Cascade

If the requested slug is missing or rejected, follow that agent's cascade and stop after `inherit`. Do not invent another model.

| Agent | Cascade |
| --- | --- |
| `fe-explore` | `composer-2.5-fast` → `inherit` |
| `fe-implement` | `inherit` |
| `fe-strategy-review` | `claude-opus-5-thinking-high` → `inherit` |
| `fe-ui-review` | `claude-4-sonnet` → `inherit` |

After every launch, report the requested slug, the model that actually ran if known, and whether that was a downgrade. A review that ran on the fallback still counts unless the user says otherwise.

Reviews report Critical, Important, or Nit, and approve only with no Critical or Important findings.
