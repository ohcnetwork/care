GitHub Repository
=================

The Github Repo available here_ contains the source code for the care project, Apart from the secrets configured at runtime, the exact copy is deployed in production.

The :code:`develop` branch auto deploys to the Development instance and is regarded as the Beta version of the application.

The :code:`staging` branch auto deploys to the Staging instance and is regarded as the Release Candidate version of the application.

The :code:`production` branch auto deploys to Production instance and is regarded as the Stable version of the application.

All Stable Releases are tagged in Github.

All PR's and issues are monitored by the code reviewers team and merged after a security review.

Any other forks for deployments **MUST** follow the same Github structure so as to remain in sync and to keep getting updates.

.. _here: https://github.com/ohcnetwork/care
