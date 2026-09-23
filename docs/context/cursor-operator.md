# Cursor operator

Fund Expert project subagents live in `.cursor/agents/` and are routed by `.cursor/rules/subagent-routing.mdc` (`alwaysApply: true`). Names use the `fe-` prefix so they do not collide with Cursor's built-in explore agent.

The parent chat stays the coordinator. Subagents do not see the parent transcript, so every prompt must carry the task, the files in scope, and the invariants for that role.

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

After every launch, report the requested slug, the model that actually ran if known, and whether that was a downgrade.

`fe-strategy-review` checks bundle publication, refresh fail-closed behavior, founder attribution, scoring, strategy and sector caps, 5% weights, the news penalty, and fail-soft history writes. `fe-ui-review` checks the local dashboard, founder options, the selection-rule editor, and the build-profile editor. Those reviews replace Stock Expert checks such as branch databases or an Evidence Console.
