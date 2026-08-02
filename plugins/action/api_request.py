# Copyright: (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

from ansible.plugins.action import ActionBase
from ansible.utils.vars import merge_hash


class ActionModule(ActionBase):
    supports_raw_params = True
    _supports_check_mode = False
    _supports_async = True
    _PASSTHROUGH_ARGS = frozenset(
        [
            "api_http_method",
            "api_key",
            "api_secret",
            "api_timeout",
            "api_url",
            "api_verify_ssl_cert",
            "command",
            "free_form",
            "params",
            "query_params",
            "validate_certs",
        ]
    )

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        del tmp

        wrap_async = self._task.async_val
        module_args = self._task.args.copy()

        raw_params = module_args.pop("_raw_params", None)
        extra_params = {}
        for key in list(module_args):
            if key not in self._PASSTHROUGH_ARGS:
                extra_params[key] = module_args.pop(key)

        if raw_params:
            module_args["free_form"] = raw_params

        if extra_params:
            params = module_args.get("params") or module_args.get("query_params") or {}
            params.update(extra_params)
            module_args["params"] = params

        results = merge_hash(
            results,
            self._execute_module(
                module_name="ngine_io.cloudstack.api_request",
                module_args=module_args,
                task_vars=task_vars,
                wrap_async=wrap_async,
            ),
        )

        if not wrap_async:
            self._remove_tmp_path(self._connection._shell.tmpdir)

        return results
