# SehatSaathi CI/CD

A hospital appointment and queue system with an automated CI/CD pipeline on GitHub Actions and AWS.  

**Built by Anusha Randhawa.** 

**Live app:** http://3.25.130.111/ (may be shut down after grading to save cost)

<img width="1366" height="609" alt="image" src="https://github.com/user-attachments/assets/6f4a50cb-6337-4bfd-9da9-13018abdacc2" />


## How it works

```
Code change -> Git push -> Tests + security checks -> Build -> S3 -> Deploy to EC2 -> Verify live
```

Every push to `main` starts the pipeline automatically:

1. **Test:** 6 pytest unit tests. A failure stops everything.
2. **Security checks (DevSecOps):** all must pass before the build starts.
   - Semgrep and CodeQL (static code analysis)
   - Bandit (Python code scanning)
   - Gitleaks (secret scanning)
   - pip-audit (vulnerable dependencies)
   - Checkov (workflow configuration)
3. **Build:** the app is zipped as `build-vN.zip`.
4. **Artifact:** the zip is uploaded to a private, versioned S3 bucket, plus a `latest.zip` copy.
5. **Deploy:** the latest build is pulled from S3 onto an EC2 server through AWS Systems Manager (no SSH keys).
6. **Verify:** the pipeline checks that the live site shows the new version.

Dependabot also watches the dependencies and opens update PRs weekly.

Below is a screenshot from a push, as an example.

<img width="913" height="346" alt="image" src="https://github.com/user-attachments/assets/9de03ad2-1d7b-4819-a29c-9517b2835eb8" />


## Try it

| Page | What it shows |
|---|---|
| `/` | Home page with the current version |
| `/db` | Patients table, loaded from `services/patient/seed.sql` |
| `/docs` | API docs (Swagger) |
| `/health` | Health check |
| `/version` | Version as JSON |

To see the pipeline work, edit `services/patient/VERSION` (or add a row to `seed.sql`) and commit. The live site updates in a few minutes.

## Rollback

Run the **Rollback to a previous build** workflow from the Actions tab and enter a build number (for example `10`). It restores that build from S3 and redeploys it.

## Layout

- `services/patient/`: the FastAPI app that gets deployed
- `.github/workflows/pipeline.yml`: the CI/CD pipeline
- `.github/workflows/rollback.yml`: manual rollback
- `tests/`: unit tests
- `services/`, `lambda/`, `db/`, `docker-compose.yml`: the full Milestone 1 system (not deployed by this pipeline)

## AWS setup

Private versioned S3 bucket, one EC2 `t3.micro` in Sydney (ap-southeast-2), and a CI user with permissions limited to that bucket and that server. AWS keys live only in GitHub Secrets.
