# Team development and review

Create a feature branch from the latest main, commit and push there, and open a PR targeting main. Do not push directly to main.

```powershell
 git fetch origin
 git switch -c descriptive-feature-name origin/main
```

Main protection requires one approving review, approval after the latest push, and resolved review conversations. New commits dismiss stale approvals. Administrators are subject to the rules, and force pushes and deletion are disabled. No required CI status check is currently configured.

| Author | Human reviewer |
| --- | --- |
| Hayden (`haydenteh5526`) | Roy (`Roy-Cheong`) |
| Roy (`Roy-Cheong`) | Sebastian (`shyishengtan009-cmd`) |
| Sebastian (`shyishengtan009-cmd`) | Hayden (`haydenteh5526`) |

Branch protection enforces an eligible approval count, not a particular person's identity. The named cycle is team guidance. Teammates need repository write access for their approvals to satisfy the rule. The author/last pusher cannot provide the required approval themselves.

For processing changes, reproduce the snapshot run and tests, and check retention, exclusions and provenance. For charts, compare values with prepared data and check units, labels and interpretation. For narrative, verify claims against evidence. Everyone must understand the complete project.

Describe purpose, changes and validation in the PR. Record significant project decisions and verification. Do not commit student IDs, credentials, environments or raw download caches.
