# Copyright 2022 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from contextlib import AbstractContextManager
import os
import pickle
import sys

from colcon_core.python_project.hook_caller import _call_hook
from colcon_core.python_project.hook_caller import _list_hooks
from colcon_core.python_project.spec import load_and_cache_spec
from colcon_core.subprocess import run


class _SubprocessTransport(AbstractContextManager):

    def __enter__(self):
        self.child_in, self.parent_out = os.pipe()
        self.parent_in, self.child_out = os.pipe()

        try:
            import msvcrt
        except ImportError:
            os.set_inheritable(self.child_in, True)
            self.pass_in = self.child_in
            os.set_inheritable(self.child_out, True)
            self.pass_out = self.child_out
        else:
            self.pass_in = msvcrt.get_osfhandle(self.child_in)
            os.set_handle_inheritable(self.pass_in, True)
            self.pass_out = msvcrt.get_osfhandle(self.child_out)
            os.set_handle_inheritable(self.pass_out, True)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.close(self.parent_out)
        os.close(self.parent_in)
        os.close(self.child_out)
        os.close(self.child_in)


class AsyncHookCaller:
    """Calls PEP 517 style hooks asynchronously in a new process."""

    def __init__(
        self, backend_name, *, project_path=None, env=None,
        stdout_callback=None, stderr_callback=None,
    ):
        """
        Initialize a new AsyncHookCaller.

        :param backend_name: The name of the PEP 517 build backend.
        :param project_path: Path to the project's root directory.
        :param env: Environment variables to use when invoking hooks.
        :param stdout_callback: Callback for stdout from the hook invocation.
        :param stderr_callback: Callback for stderr from the hook invocation.
        """
        self._backend_name = backend_name
        self._project_path = str(project_path) if project_path else None
        self._env = dict(env if env is not None else os.environ)
        self._stdout_callback = stdout_callback
        self._stderr_callback = stderr_callback

    @property
    def backend_name(self):
        """Get the name of the backend to call hooks on."""
        return self._backend_name

    @property
    def env(self):
        """Get the environment variables to use when invoking hooks."""
        return self._env

    async def list_hooks(self):
        """
        Call into the backend to list implemented hooks.

        This function lists all callable methods on the backend, which may
        include more than just the hook names.

        :returns: List of hook names.
        """
        args = [
            sys.executable, _list_hooks.__file__,
            self._backend_name]
        process = await run(
            args, None, self._stderr_callback,
            cwd=self._project_path, env=self.env,
            capture_output=True)
        process.check_returncode()
        hook_names = [
            line.strip().decode() for line in process.stdout.splitlines()]
        return [
            hook for hook in hook_names if hook and not hook.startswith('_')]

    async def call_hook(self, hook_name, **kwargs):
        """
        Call the given hook with given arguments.

        :param hook_name: Name of the hook to call.
        """
        with _SubprocessTransport() as transport:
            args = [
                sys.executable, _call_hook.__file__,
                self._backend_name, hook_name,
                str(transport.pass_in), str(transport.pass_out)]
            with os.fdopen(os.dup(transport.parent_out), 'wb') as f:
                pickle.dump(kwargs, f)
            have_callbacks = self._stdout_callback or self._stderr_callback
            process = await run(
                args, self._stdout_callback, self._stderr_callback,
                cwd=self._project_path, env=self.env, close_fds=False,
                capture_output=not have_callbacks)
            process.check_returncode()
            with os.fdopen(os.dup(transport.parent_in), 'rb') as f:
                res = pickle.load(f)
            return res


def get_hook_caller(desc, **kwargs):
    """
    Create a new AsyncHookCaller instance for a package descriptor.

    :param desc: The package descriptor
    """
    spec = load_and_cache_spec(desc)
    backend_path = spec['build-system'].get('backend-path')
    if backend_path:
        # TODO: This isn't *technically* the beginning of sys.path
        #       as PEP 517 calls for, but it's pretty darn close.
        kwargs['env'] = {
            **kwargs.get('env', os.environ),
            'PYTHONDONTWRITEBYTECODE': '1',
        }
        pythonpath = kwargs['env'].get('PYTHONPATH', '')
        kwargs['env']['PYTHONPATH'] = os.pathsep.join(
            backend_path + ([pythonpath] if pythonpath else []))
    return AsyncHookCaller(
        spec['build-system']['build-backend'],
        project_path=desc.path, **kwargs)
