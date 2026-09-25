# Third-party components

The MIT license in this repository covers its original installer, launchers,
tests and documentation. It does not relicense downloaded applications, libraries
or translation models. This repository and its source release do not bundle them.

| Component | Upstream / license information |
| --- | --- |
| Crow Translate 4.1.0 | [KDE project](https://apps.kde.org/crowtranslate/), GPL-3.0-or-later; [release source](https://download.kde.org/stable/crow-translate/4.1.0/crow-translate-4.1.0.tar.gz) |
| LibreTranslate 1.9.6 | [Upstream](https://github.com/LibreTranslate/LibreTranslate), AGPL-3.0 |
| Argos Translate LT | [PyPI](https://pypi.org/project/argos-translate-lt/), upstream package license metadata applies |
| Argos en↔zh 1.9 models | [Official index](https://github.com/argosopentech/argospm-index); retain the metadata and documentation included in each model archive |
| MiniSBD | [Upstream](https://github.com/LibreTranslate/MiniSBD) |
| CTranslate2 | [Upstream](https://github.com/OpenNMT/CTranslate2), MIT |
| Python dependencies | Exact versions: `requirements.lock`; installed wheels retain upstream license metadata |

Crow's official AppImage includes additional third-party libraries and their notices.
The installer extracts it without altering those libraries. Distribution of a full
preinstalled binary/model bundle is outside this project's source-release workflow.
Review each component's terms before redistributing a populated download cache.
