"""Loaded by Harbor 0.25.0, not by this package: `skip_install`, which Harbor has in 0.27.0.

The agents are Harbor's own. Only the installation is replaced by a check that the pinned version is there.
"""

from typing import Any

from harbor.agents.installed.opencode import OpenCode
from harbor.agents.installed.pi import Pi


class _Prebuilt:
    async def install(self, environment: Any) -> None:
        command = self.get_version_command()  # type: ignore[attr-defined]
        result = await environment.exec(command=command)
        found = None
        if result.return_code == 0 and result.stdout:
            found = self.parse_version(result.stdout)  # type: ignore[attr-defined]
        if found != self._version:  # type: ignore[has-type]
            raise RuntimeError(f"the image has harness version {found}, not {self._version}")  # type: ignore[has-type]
        self._version = found


class PrebuiltPi(_Prebuilt, Pi):
    pass


class PrebuiltOpenCode(_Prebuilt, OpenCode):
    pass
